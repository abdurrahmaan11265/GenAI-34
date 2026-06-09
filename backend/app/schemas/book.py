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

DIFFICULTY_MAPPING = {
    1: "beginner",
    2: "beginner",
    3: "intermediate",
    4: "advanced",
    5: "advanced"
}

class KGNodeDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    bookId: str = Field(alias="bookId")
    title: str
    summary: str
    sourceChunks: List[str] = Field(alias="sourceChunks")
    difficultyTier: str = Field(alias="difficultyTier")
    orderIndex: int = Field(alias="orderIndex")
    sectionName: Optional[str] = Field(alias="sectionName", default=None)
    createdAt: str = Field(alias="createdAt")

class KGEdgeDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    fromNodeId: str = Field(alias="fromNodeId")
    toNodeId: str = Field(alias="toNodeId")
    type: str
    weight: float = 1.0
    confidence: float = 0.5

class GraphDTO(BaseModel):
    nodes: List[KGNodeDTO]
    edges: List[KGEdgeDTO]

class BookSummaryDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    title: str
    author: Optional[str] = None
    coverUrl: Optional[str] = Field(alias="coverUrl", default=None)
    status: str
    progress: int = 0
    totalNodes: int = Field(alias="totalNodes", default=0)
    masteredNodes: int = Field(alias="masteredNodes", default=0)
    dueToday: int = Field(alias="dueToday", default=0)
    lastStudied: Optional[str] = Field(alias="lastStudied", default=None)
    createdAt: str = Field(alias="createdAt")
