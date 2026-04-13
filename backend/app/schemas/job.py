from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel
from app.models.job import JobStatus


class JobOut(BaseModel):
    id: int
    celery_task_id: Optional[str]
    document_id: int
    status: str
    progress: float
    current_step: Optional[str]
    error_message: Optional[str]
    retry_count: int
    result: Optional[dict]
    is_reviewed: bool
    is_finalized: bool
    reviewed_result: Optional[dict]
    queued_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobWithDocumentOut(JobOut):
    document: "DocumentOut"

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: int
    document_id: int
    status: str
    progress: float
    current_step: Optional[str]
    is_finalized: bool
    retry_count: int
    queued_at: datetime
    completed_at: Optional[datetime]
    original_filename: str
    file_size: int

    model_config = {"from_attributes": True}


class UpdateResultRequest(BaseModel):
    reviewed_result: dict


class FinalizeRequest(BaseModel):
    pass


# Resolve forward ref
from app.schemas.document import DocumentOut  # noqa: E402
JobWithDocumentOut.model_rebuild()