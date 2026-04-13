import os
import time
from datetime import datetime, timezone
from celery import Task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.workers.progress_publisher import publish_progress
from app.db.base import SessionLocal
from app.models.job import Job, JobStatus
from app.models.document import Document


def update_job_in_db(db: Session, job_id: int, **kwargs):
    """Helper to update job fields and commit."""
    db.query(Job).filter(Job.id == job_id).update(
        {**kwargs, "updated_at": datetime.now(timezone.utc)}
    )
    db.commit()


@celery_app.task(
    bind=True,
    name="app.workers.document_processor.process_document",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_document(self: Task, job_id: int, document_id: int):
    """
    Main async document processing task.
    Publishes progress events to Redis Pub/Sub at each stage.
    """
    db = SessionLocal()
    try:
        # ── Stage 1: Job Started ──────────────────────────────────────
        update_job_in_db(
            db, job_id,
            status=JobStatus.PROCESSING,
            started_at=datetime.now(timezone.utc),
            current_step="job_started",
            progress=5.0,
        )
        publish_progress(job_id, "job_started", 5.0, "Job has started processing")
        time.sleep(0.5)

        # ── Stage 2: Fetch Document ───────────────────────────────────
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # ── Stage 3: Document Parsing Started ────────────────────────
        update_job_in_db(db, job_id, current_step="document_parsing_started", progress=15.0)
        publish_progress(job_id, "document_parsing_started", 15.0, "Parsing document content")
        time.sleep(1.0)

        parsed_text = _parse_document(document)

        # ── Stage 4: Document Parsing Completed ──────────────────────
        update_job_in_db(db, job_id, current_step="document_parsing_completed", progress=40.0)
        publish_progress(
            job_id, "document_parsing_completed", 40.0,
            "Document parsed successfully",
            {"char_count": len(parsed_text), "filename": document.original_filename}
        )
        time.sleep(0.5)

        # ── Stage 5: Field Extraction Started ────────────────────────
        update_job_in_db(db, job_id, current_step="field_extraction_started", progress=55.0)
        publish_progress(job_id, "field_extraction_started", 55.0, "Extracting structured fields")
        time.sleep(1.5)

        extracted = _extract_fields(document, parsed_text)

        # ── Stage 6: Field Extraction Completed ──────────────────────
        update_job_in_db(db, job_id, current_step="field_extraction_completed", progress=80.0)
        publish_progress(
            job_id, "field_extraction_completed", 80.0,
            "Fields extracted successfully",
            {"fields_count": len(extracted)}
        )
        time.sleep(0.5)

        # ── Stage 7: Storing Result ───────────────────────────────────
        update_job_in_db(
            db, job_id,
            status=JobStatus.COMPLETED,
            current_step="job_completed",
            progress=100.0,
            result=extracted,
            completed_at=datetime.now(timezone.utc),
        )
        publish_progress(
            job_id, "job_completed", 100.0,
            "Document processing complete",
            {"result_fields": list(extracted.keys())}
        )

        return {"status": "completed", "job_id": job_id}

    except Exception as exc:
        error_msg = str(exc)
        update_job_in_db(
            db, job_id,
            status=JobStatus.FAILED,
            current_step="job_failed",
            error_message=error_msg,
            completed_at=datetime.now(timezone.utc),
        )
        publish_progress(job_id, "job_failed", 0.0, f"Processing failed: {error_msg}")

        # Celery retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 10)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "job_id": job_id, "error": error_msg}
    finally:
        db.close()


def _parse_document(document: Document) -> str:
    """
    Parse document content. Handles text files directly,
    generates structured mock content for other formats.
    """
    file_path = document.file_path
    ext = os.path.splitext(document.original_filename)[1].lower()

    if ext == ".txt" and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            pass

    # Structured mock content for other formats
    return (
        f"Document: {document.original_filename}\n"
        f"Type: {document.file_type}\n"
        f"Size: {document.file_size} bytes\n"
        f"Processed by DocFlow at {datetime.now(timezone.utc).isoformat()}\n\n"
        f"This document contains structured business content. "
        f"Key topics include operations, reporting, and workflow management. "
        f"The document was uploaded for async processing and field extraction."
    )


def _extract_fields(document: Document, text: str) -> dict:
    """
    Extract structured fields from parsed text.
    In production this would use an NLP/LLM pipeline.
    """
    words = text.split()
    word_count = len(words)
    ext = os.path.splitext(document.original_filename)[1].lower()

    categories = {
        ".pdf": "Report",
        ".docx": "Document",
        ".doc": "Document",
        ".txt": "Text File",
        ".csv": "Data File",
        ".xlsx": "Spreadsheet",
        ".png": "Image",
        ".jpg": "Image",
        ".jpeg": "Image",
    }
    category = categories.get(ext, "Unknown")

    # Generate keywords from the most common meaningful words
    stop_words = {"the", "a", "an", "is", "in", "of", "and", "to", "for", "this", "that", "with"}
    keywords = list(
        {w.lower().strip(".,!?") for w in words if len(w) > 4 and w.lower() not in stop_words}
    )[:8]

    return {
        "title": document.original_filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title(),
        "category": category,
        "summary": f"This {category.lower()} contains {word_count} words. "
                   f"File size is {document.file_size} bytes. "
                   f"Processed and analyzed by DocFlow automated pipeline.",
        "keywords": keywords,
        "metadata": {
            "filename": document.original_filename,
            "file_type": document.file_type,
            "mime_type": document.mime_type,
            "file_size_bytes": document.file_size,
            "word_count": word_count,
            "char_count": len(text),
        },
        "status": "extracted",
        "confidence_score": 0.87,
        "processing_version": "1.0.0",
    }