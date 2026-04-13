import os
from typing import Optional, BinaryIO
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from app.models.document import Document
from app.models.job import Job, JobStatus
from app.storage.local import storage
from app.core.config import settings
from app.workers.document_processor import process_document


def validate_file(file: UploadFile) -> None:
    """Validate file extension and size."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )


def create_document_and_job(
    db: Session,
    file: UploadFile,
    owner_id: Optional[int] = None,
) -> tuple[Document, Job]:
    """Save file to storage, create Document + Job records, dispatch Celery task."""
    validate_file(file)

    file_path = storage.save(file.file, file.filename, subfolder="documents")
    file_size = os.path.getsize(file_path)
    ext = os.path.splitext(file.filename)[1].lower()
    mime = file.content_type or "application/octet-stream"

    document = Document(
        filename=os.path.basename(file_path),
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        file_type=ext.lstrip("."),
        mime_type=mime,
        owner_id=owner_id,
    )
    db.add(document)
    db.flush()  # get document.id without full commit

    job = Job(
        document_id=document.id,
        status=JobStatus.QUEUED,
        progress=0.0,
    )
    db.add(job)
    db.commit()
    db.refresh(document)
    db.refresh(job)

    # Dispatch Celery task (idempotent: task_id stored on job)
    task = process_document.apply_async(
        args=[job.id, document.id],
        task_id=f"job-{job.id}-doc-{document.id}",
    )
    job.celery_task_id = task.id
    db.commit()
    db.refresh(job)

    return document, job


def get_all_jobs(
    db: Session,
    owner_id: Optional[int],
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "queued_at",
    sort_dir: str = "desc",
    skip: int = 0,
    limit: int = 20,
):
    """List jobs with optional search/filter/sort."""
    query = (
        db.query(Job, Document)
        .join(Document, Job.document_id == Document.id)
    )
    if owner_id:
        query = query.filter(Document.owner_id == owner_id)
    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(Job.status == status_filter)

    sort_col = {
        "queued_at": Job.queued_at,
        "status": Job.status,
        "filename": Document.original_filename,
        "progress": Job.progress,
    }.get(sort_by, Job.queued_at)

    if sort_dir == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    total = query.count()
    results = query.offset(skip).limit(limit).all()
    return results, total


def retry_job(db: Session, job_id: int, owner_id: Optional[int]) -> Job:
    """Reset a failed job and re-dispatch the Celery task."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry failed/cancelled jobs. Current status: {job.status}"
        )

    job.status = JobStatus.QUEUED
    job.progress = 0.0
    job.error_message = None
    job.current_step = None
    job.started_at = None
    job.completed_at = None
    job.retry_count += 1
    db.commit()
    db.refresh(job)

    task = process_document.apply_async(
        args=[job.id, job.document_id],
        task_id=f"job-{job.id}-retry-{job.retry_count}",
    )
    job.celery_task_id = task.id
    db.commit()
    db.refresh(job)
    return job