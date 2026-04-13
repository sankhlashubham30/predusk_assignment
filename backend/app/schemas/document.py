from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    mime_type: str
    owner_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}