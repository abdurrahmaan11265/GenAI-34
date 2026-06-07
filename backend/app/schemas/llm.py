from pydantic import BaseModel, Field
from typing import List, Optional

class ConceptCandidate(BaseModel):
    name: str = Field(description="The canonical name of the concept.")
    summary: str = Field(description="A concise definition or explanation of the concept based ONLY on the provided text.")
    difficulty: int = Field(description="Difficulty rating from 1 to 5.")
    subtopics: List[str] = Field(default_factory=list, description="3-5 short sub-topic titles (2-5 words each) that make up this concept.")

class ConceptExtractionResponse(BaseModel):
    concepts: List[ConceptCandidate]

class RelationshipExtractionResponse(BaseModel):
    relationship_type: str = Field(description="Must be one of: PREREQUISITE, RELATED, NO_RELATIONSHIP")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    evidence: Optional[str] = Field(description="Brief quote or reasoning supporting the relationship.")

class MergedConceptCandidate(BaseModel):
    canonical_name: str
    canonical_summary: str
    difficulty: int = Field(description="Difficulty rating from 1 to 5.")


# ---------------------------------------------------------------------------
# Assessment Engine structured outputs (Gemini response_schema targets)
# Kept free of Optional/dict types because google-genai structured output
# does not reliably support nullable or free-form object fields.
# ---------------------------------------------------------------------------

class AssessmentQuestionOutput(BaseModel):
    """Output of the assessment_question_generator prompt."""
    question: str = Field(description="The question text shown to the learner.")
    options: List[str] = Field(default_factory=list, description="Exactly 4 options for MCQ; empty array otherwise.")
    correct_option: int = Field(default=-1, description="0-based index of the correct MCQ option; -1 when not MCQ.")
    expected_answer: str = Field(description="Model answer. For MCQ, the text of the correct option.")
    hints: List[str] = Field(default_factory=list, description="1-2 short hints, no spoilers.")
    explanation: str = Field(default="", description="Short explanation shown after the learner answers.")
    difficulty: str = Field(default="", description="Echoed difficulty tier.")
    bloom_level: str = Field(default="", description="Echoed bloom level.")


class AssessmentEvalOutput(BaseModel):
    """Output of the assessment_evaluator prompt (free-text answers only)."""
    correctness: str = Field(description='One of "correct", "partial", "incorrect".')
    score: float = Field(description="Degree of understanding, 0.0 to 1.0.")
    understanding_level: str = Field(default="none", description='One of "full", "partial", "weak", "none".')
    misconceptions: List[str] = Field(default_factory=list, description="Short snake_case misconception categories.")
    feedback: str = Field(default="", description="One or two sentences of constructive feedback.")


class DNAItem(BaseModel):
    area: str = Field(description="Concept or topic area.")
    evidence: str = Field(description="Concrete evidence from the assessment results.")


class DNAMisconception(BaseModel):
    category: str = Field(description="Short snake_case misconception category.")
    evidence: str = Field(description="Evidence supporting this misconception.")


class DNAFocusArea(BaseModel):
    area: str = Field(description="Concept or topic to focus on next.")
    reason: str = Field(description="Why this area is recommended, grounded in evidence.")


class LearningDNAOutput(BaseModel):
    """Output of the learning_dna_generator prompt."""
    strengths: List[DNAItem] = Field(default_factory=list)
    weaknesses: List[DNAItem] = Field(default_factory=list)
    misconceptions: List[DNAMisconception] = Field(default_factory=list)
    recommended_focus_areas: List[DNAFocusArea] = Field(default_factory=list)
    confidence_profile: str = Field(default="", description="Narrative summary of confidence calibration.")
    learning_path_explanation: str = Field(default="", description="2-4 sentence narrative of the learner's starting point.")


class LessonOutput(BaseModel):
    """Output of the lesson_generator prompt (pls2 #7)."""
    introduction: str = Field(default="")
    mental_model: str = Field(default="")
    core_explanation: str = Field(default="")
    analogy: str = Field(default="")
    worked_examples: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    practice_exercises: List[str] = Field(default_factory=list)
    summary: str = Field(default="")
    key_takeaways: List[str] = Field(default_factory=list)


class TutorOutput(BaseModel):
    """Output of the socratic_tutor prompt (pls3 #10)."""
    tutor_response: str = Field(default="")
    follow_up_question: str = Field(default="")
    hint: str = Field(default="")
    reasoning_prompt: str = Field(default="")
    misconceptions_detected: List[str] = Field(default_factory=list)


class HintOutput(BaseModel):
    """Output of the hint_generator prompt (pls3 #11)."""
    hint_level: int = Field(default=1)
    hint: str = Field(default="")
    reason: str = Field(default="")


class SubtopicsOutput(BaseModel):
    """Sub-topics that make up a concept (shown in the course/daily plan)."""
    subtopics: List[str] = Field(default_factory=list, description="3-5 short sub-topic titles within the concept.")
