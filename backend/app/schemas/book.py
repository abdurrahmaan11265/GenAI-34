from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    description: Optional[str] = None

class BookDTO(BaseModel):
    id: str
    title: str
    author: Optional[str]
    description: Optional[str]
    source_type: str
    file_url: str
    created_at: datetime

class JobStatusDTO(BaseModel):
    job_id: str
    status: str
    nodes_created: Optional[int]
    edges_created: Optional[int]
    error_message: Optional[str]

class UploadResponse(BaseModel):
    book: BookDTO
    job: JobStatusDTO
