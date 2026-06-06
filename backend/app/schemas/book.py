from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class BookCreate(BaseModel):
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False

class BookDTO(BaseModel):
    id: str
    title: str
    author: Optional[str]
    description: Optional[str]
    source_type: str
    file_url: Optional[str]
    created_at: datetime

class BookDetailDTO(BookDTO):
    nodes: List[dict] = []

class JobStatusDTO(BaseModel):
    job_id: str
    status: str
    nodes_created: Optional[int]
    edges_created: Optional[int]
    error_message: Optional[str]

class UploadResponse(BaseModel):
    book: BookDTO
    job: JobStatusDTO

class BookStatusDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    status: str
    current_step: str = Field(alias="currentStep")
    step_index: int = Field(alias="stepIndex")
    total_steps: int = Field(alias="totalSteps", default=4)
    estimated_seconds_remaining: Optional[int] = Field(alias="estimatedSecondsRemaining", default=None)
    error: Optional[str] = None
