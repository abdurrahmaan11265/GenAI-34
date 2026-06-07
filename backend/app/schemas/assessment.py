from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class StartAssessmentRequest(BaseModel):
    book_id: str


class QuestionDTO(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    question_type: str
    difficulty_level: int
    bloom_level: str
    question_text: str
    # Present only for MCQ; empty list for free-text questions.
    options: List[str] = Field(default_factory=list)


class ProgressDTO(BaseModel):
    concepts_total: int
    concepts_resolved: int
    questions_answered: int


class StartAssessmentResponse(BaseModel):
    assessment_id: str
    question: Optional[QuestionDTO] = None
    progress: ProgressDTO
    completed: bool = False


class SubmitResponseRequest(BaseModel):
    question_id: str
    # For MCQ: the 0-based option index as a string (e.g. "2").
    # For free-text: the learner's answer text.
    answer: str
    # Captured BEFORE correctness is revealed (1-5). Optional.
    confidence_level: Optional[int] = Field(default=None, ge=1, le=5)
    response_time_seconds: Optional[int] = Field(default=None, ge=0)


class ResponseResultDTO(BaseModel):
    is_correct: bool
    correctness: str            # correct | partial | incorrect
    score: float                # 0.0 - 1.0
    feedback: str = ""
    explanation: str = ""
    # Revealed only AFTER the learner answers, so they can compare.
    correct_answer: str = ""
    correct_option: Optional[int] = None   # MCQ: 0-based index of the correct option
    # True when failing the easy (MCQ) tier stops descent into dependents.
    branch_stopped: bool = False


class SubmitResponseResponse(BaseModel):
    result: ResponseResultDTO
    next_question: Optional[QuestionDTO] = None
    progress: ProgressDTO
    completed: bool = False


class OutcomeDTO(BaseModel):
    concept_id: str
    concept_name: str
    mastery_estimate: float
    placement_state: str


class AssessmentSummaryDTO(BaseModel):
    mastered: int = 0
    ready: int = 0
    learning: int = 0
    weak: int = 0
    unknown: int = 0
    locked: int = 0


class AssessmentResultDTO(BaseModel):
    assessment_id: str
    status: str
    score_percentage: Optional[float] = None
    summary: AssessmentSummaryDTO
    outcomes: List[OutcomeDTO] = Field(default_factory=list)
    dna: Optional[Dict[str, Any]] = None
