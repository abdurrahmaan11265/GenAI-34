from pydantic import BaseModel, ConfigDict, Field
from typing import List


class CurriculumItemDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    conceptId: str = Field(alias="conceptId")
    title: str
    orderIndex: int = Field(alias="orderIndex")
    state: str
    mastery: float
    estimatedMinutes: int = Field(alias="estimatedMinutes")
    unmetPrerequisites: List[str] = Field(alias="unmetPrerequisites", default_factory=list)
    subtopics: List[str] = Field(default_factory=list)


class CurriculumDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    bookId: str = Field(alias="bookId")
    version: int
    totalConcepts: int = Field(alias="totalConcepts")
    masteredConcepts: int = Field(alias="masteredConcepts")
    items: List[CurriculumItemDTO]


class DailyPlanDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    bookId: str = Field(alias="bookId")
    mode: str                      # revise_only | learn_only | both | all_caught_up
    revise: List[CurriculumItemDTO]
    learn: List[CurriculumItemDTO]
    totalDue: int = Field(alias="totalDue")
    totalNew: int = Field(alias="totalNew")
    estimatedMinutes: int = Field(alias="estimatedMinutes")
