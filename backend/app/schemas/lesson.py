from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class LessonContentDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    introduction: str = ""
    mentalModel: str = Field(alias="mentalModel", default="")
    coreExplanation: str = Field(alias="coreExplanation", default="")
    analogy: str = ""
    workedExamples: List[str] = Field(alias="workedExamples", default_factory=list)
    commonMistakes: List[str] = Field(alias="commonMistakes", default_factory=list)
    practiceExercises: List[str] = Field(alias="practiceExercises", default_factory=list)
    summary: str = ""
    keyTakeaways: List[str] = Field(alias="keyTakeaways", default_factory=list)


class StartLessonRequest(BaseModel):
    book_id: str
    concept_id: str


class TurnDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    turnIndex: int = Field(alias="turnIndex")
    userMessage: str = Field(alias="userMessage")
    assistantMessage: str = Field(alias="assistantMessage")
    hintLevel: int = Field(alias="hintLevel", default=0)


class LessonSessionDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sessionId: str = Field(alias="sessionId")
    conceptId: str = Field(alias="conceptId")
    conceptTitle: str = Field(alias="conceptTitle")
    status: str
    content: LessonContentDTO
    transcript: List[TurnDTO] = Field(default_factory=list)


class TutorRequest(BaseModel):
    message: str
    hint_level: int = Field(default=0, ge=0, le=4)
    # Set true when the learner's message is a question they want captured.
    is_question: bool = False


class TutorResponseDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    turnIndex: int = Field(alias="turnIndex")
    tutorResponse: str = Field(alias="tutorResponse")
    followUpQuestion: str = Field(alias="followUpQuestion", default="")
    hint: str = ""
    reasoningPrompt: str = Field(alias="reasoningPrompt", default="")
    misconceptionsDetected: List[str] = Field(alias="misconceptionsDetected", default_factory=list)
    questionCaptured: bool = Field(alias="questionCaptured", default=False)


class HintRequest(BaseModel):
    question: str
    hint_level: int = Field(default=1, ge=1, le=4)


class HintDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    hintLevel: int = Field(alias="hintLevel")
    hint: str
    reason: str = ""


class CompleteLessonDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: str
    unlockedConcepts: List[str] = Field(alias="unlockedConcepts", default_factory=list)


# ---- mastery-check quiz ----------------------------------------------------

class QuizQuestionDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    conceptId: str = Field(alias="conceptId")
    questionType: str = Field(alias="questionType")
    questionText: str = Field(alias="questionText")
    options: List[str] = Field(default_factory=list)


class QuizDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sessionId: str = Field(alias="sessionId")
    conceptId: str = Field(alias="conceptId")
    conceptTitle: str = Field(alias="conceptTitle")
    questions: List[QuizQuestionDTO]


class QuizAnswerDTO(BaseModel):
    question_id: str
    answer: str


class QuizSubmitRequest(BaseModel):
    responses: List[QuizAnswerDTO]


class QuizResultItemDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    questionId: str = Field(alias="questionId")
    isCorrect: bool = Field(alias="isCorrect")
    correctAnswer: str = Field(alias="correctAnswer", default="")
    explanation: str = ""


class QuizResultDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    passed: bool
    score: float
    results: List[QuizResultItemDTO]
    unlockedConcepts: List[str] = Field(alias="unlockedConcepts", default_factory=list)
    message: str = ""
