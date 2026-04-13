from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_optional_user, get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.document import Document
from app.schemas.job import JobOut, JobWithDocumentOut, JobListItem, UpdateResultRequest
from app.schemas.document import DocumentOut
from app.services.document_service import create_document_and_job, get_all_jobs, retry_job
from app.services.export_service import export_as_json, export_as_csv

router = APIRouter()


@router.post("/upload", status_code=202)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Upload one or more documents and dispatch background processing jobs."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    owner_id = current_user.id if current_user else None

    for file in files:
        document, job = create_document_and_job(db, file, owner_id)
        results.append({
            "document_id": document.id,
            "job_id": job.id,
            "filename": document.original_filename,
            "status": job.status,
            "celery_task_id": job.celery_task_id,
        })

    return {"uploaded": len(results), "jobs": results}


@router.get("/", response_model=dict)
def list_documents(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("queued_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List all jobs/documents with search, filter, and sort."""
    owner_id = current_user.id if current_user else None
    skip = (page - 1) * page_size

    results, total = get_all_jobs(
        db, owner_id=owner_id,
        search=search, status_filter=status,
        sort_by=sort_by, sort_dir=sort_dir,
        skip=skip, limit=page_size,
    )

    items = []
    for job, document in results:
        items.append({
            "id": job.id,
            "document_id": document.id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step,
            "is_finalized": job.is_finalized,
            "retry_count": job.retry_count,
            "queued_at": job.queued_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "original_filename": document.original_filename,
            "file_size": document.file_size,
            "file_type": document.file_type,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{document_id}", response_model=dict)
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get full document + job details."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    job = db.query(Job).filter(Job.document_id == document_id).first()

    return {
        "document": {
            "id": document.id,
            "original_filename": document.original_filename,
            "file_size": document.file_size,
            "file_type": document.file_type,
            "mime_type": document.mime_type,
            "created_at": document.created_at.isoformat(),
        },
        "job": {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "current_step": job.current_step,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "result": job.result,
            "reviewed_result": job.reviewed_result,
            "is_reviewed": job.is_reviewed,
            "is_finalized": job.is_finalized,
            "queued_at": job.queued_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "celery_task_id": job.celery_task_id,
        } if job else None,
    }


@router.put("/{document_id}/result")
def update_result(
    document_id: int,
    payload: UpdateResultRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Save user-reviewed/edited result."""
    job = db.query(Job).filter(Job.document_id == document_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job must be completed before reviewing")

    job.reviewed_result = payload.reviewed_result
    job.is_reviewed = True
    db.commit()
    return {"message": "Result updated", "job_id": job.id}


@router.post("/{document_id}/finalize")
def finalize_result(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Finalize a reviewed result — locks it from further editing."""
    job = db.query(Job).filter(Job.document_id == document_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job must be completed to finalize")

    job.is_finalized = True
    job.is_reviewed = True
    if not job.reviewed_result:
        job.reviewed_result = job.result
    db.commit()
    return {"message": "Result finalized", "job_id": job.id}


@router.post("/{document_id}/retry")
def retry_document_job(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Retry a failed processing job."""
    job = db.query(Job).filter(Job.document_id == document_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    updated_job = retry_job(db, job.id, current_user.id if current_user else None)
    return {
        "message": "Job queued for retry",
        "job_id": updated_job.id,
        "retry_count": updated_job.retry_count,
        "celery_task_id": updated_job.celery_task_id,
    }


@router.get("/{document_id}/export")
def export_document(
    document_id: int,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Export finalized result as JSON or CSV."""
    job = db.query(Job).filter(Job.document_id == document_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job must be completed to export")

    document = db.query(Document).filter(Document.id == document_id).first()
    base_name = document.original_filename.rsplit(".", 1)[0] if document else f"document_{document_id}"

    if format == "csv":
        content = export_as_csv(job)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_result.csv"'},
        )
    else:
        content = export_as_json(job)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_result.json"'},
        )