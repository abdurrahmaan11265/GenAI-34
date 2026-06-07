from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


class GraphNodeStateDTO(BaseModel):
    """A concept node overlaid with the current user's learning state.

    Implements the four-state graph reveal (System Design Section E):
    LOCKED / AVAILABLE / IN_PROGRESS / MASTERED / DUE.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    summary: str
    difficulty: int
    state: str
    masteryScore: float = Field(alias="masteryScore", default=0.0)
    lastReviewed: Optional[str] = Field(alias="lastReviewed", default=None)
    nextDue: Optional[str] = Field(alias="nextDue", default=None)
    # Direct prerequisite concept ids — drives "Complete X first" gating reasons.
    prerequisites: List[str] = Field(default_factory=list)


class GraphRevealEdgeDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fromNodeId: str = Field(alias="fromNodeId")
    toNodeId: str = Field(alias="toNodeId")
    type: str


class GraphRevealSummaryDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    total: int = 0
    mastered: int = 0
    available: int = 0
    inProgress: int = Field(alias="inProgress", default=0)
    due: int = 0
    locked: int = 0
    percentMastered: float = Field(alias="percentMastered", default=0.0)
    percentRevealed: float = Field(alias="percentRevealed", default=0.0)


class PersonalGraphDTO(BaseModel):
    nodes: List[GraphNodeStateDTO]
    edges: List[GraphRevealEdgeDTO]
    summary: GraphRevealSummaryDTO
