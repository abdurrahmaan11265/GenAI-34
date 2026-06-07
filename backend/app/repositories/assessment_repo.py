from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept, ConceptEdge
from app.models.question import GeneratedQuestion
from app.models.assessment import Assessment, AssessmentResponse, AssessmentOutcome
from app.models.mastery import ConceptMastery, UserConceptState
from app.models.learner import LearningDNA


class AssessmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- graph reads --------------------------------------------------------

    async def get_active_graph_version(self, book_id: str) -> Optional[int]:
        """Active version = MAX(graph_version) of the book's concepts.

        Concepts and edges are keyed by graph_version; for a single-build book
        this is 1. Deterministic and matches how the ingestion pipeline writes.
        """
        result = await self.session.execute(
            select(Concept.graph_version)
            .where(Concept.book_id == book_id)
            .order_by(Concept.graph_version.desc())
            .limit(1)
        )
        row = result.scalars().first()
        return int(row) if row is not None else None

    async def get_concepts(self, book_id: str, graph_version: int) -> List[Concept]:
        result = await self.session.execute(
            select(Concept).where(
                Concept.book_id == book_id,
                Concept.graph_version == graph_version,
            )
        )
        return list(result.scalars().all())

    async def get_prerequisite_edges(self, book_id: str, graph_version: int) -> List[ConceptEdge]:
        result = await self.session.execute(
            select(ConceptEdge).where(
                ConceptEdge.book_id == book_id,
                ConceptEdge.graph_version == graph_version,
                ConceptEdge.edge_type == "PREREQUISITE",
            )
        )
        return list(result.scalars().all())

    async def is_enrolled(self, user_id: str, book_id: str) -> bool:
        result = await self.session.execute(
            text("SELECT 1 FROM user_books WHERE user_id = :uid AND book_id = :bid"),
            {"uid": user_id, "bid": book_id},
        )
        return result.first() is not None

    # ---- assessments --------------------------------------------------------

    async def create_assessment(self, assessment: Assessment) -> Assessment:
        self.session.add(assessment)
        await self.session.flush()
        return assessment

    async def get_assessment(self, assessment_id: str) -> Optional[Assessment]:
        result = await self.session.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        return result.scalars().first()

    # ---- questions ----------------------------------------------------------

    async def create_question(self, question: GeneratedQuestion) -> GeneratedQuestion:
        self.session.add(question)
        await self.session.flush()
        return question

    async def get_question(self, question_id: str) -> Optional[GeneratedQuestion]:
        result = await self.session.execute(
            select(GeneratedQuestion).where(GeneratedQuestion.id == question_id)
        )
        return result.scalars().first()

    # ---- responses ----------------------------------------------------------

    async def create_response(self, response: AssessmentResponse) -> AssessmentResponse:
        self.session.add(response)
        await self.session.flush()
        return response

    async def get_responses(self, assessment_id: str) -> List[AssessmentResponse]:
        result = await self.session.execute(
            select(AssessmentResponse)
            .where(AssessmentResponse.assessment_id == assessment_id)
            .order_by(AssessmentResponse.created_at.asc())
        )
        return list(result.scalars().all())

    # ---- outcomes -----------------------------------------------------------

    async def upsert_outcome(self, assessment_id: str, concept_id: str,
                             mastery_estimate: float, placement_state: str) -> None:
        stmt = pg_insert(AssessmentOutcome.__table__).values(
            assessment_id=assessment_id,
            concept_id=concept_id,
            mastery_estimate=mastery_estimate,
            placement_state=placement_state,
        ).on_conflict_do_update(
            constraint="uq_assessment_concept_outcome",
            set_={"mastery_estimate": mastery_estimate, "placement_state": placement_state},
        )
        await self.session.execute(stmt)

    async def get_outcomes(self, assessment_id: str) -> List[AssessmentOutcome]:
        result = await self.session.execute(
            select(AssessmentOutcome).where(AssessmentOutcome.assessment_id == assessment_id)
        )
        return list(result.scalars().all())

    # ---- mastery + node state (learner model writers) -----------------------

    async def upsert_concept_mastery(self, user_id: str, concept_id: str,
                                     mastery_score: float, mastery_state: str,
                                     source: str = "ASSESSMENT") -> None:
        now = datetime.now(timezone.utc)
        first_mastered = now if mastery_state == "MASTERED" else None
        set_ = {
            "mastery_score": mastery_score,
            "mastery_state": mastery_state,
            "last_reviewed_at": now,
            "updated_by_source": source,
        }
        # Only stamp first_mastered_at when transitioning into MASTERED and not set.
        if mastery_state == "MASTERED":
            set_["first_mastered_at"] = text(
                "COALESCE(concept_mastery.first_mastered_at, NOW())"
            )
        stmt = pg_insert(ConceptMastery.__table__).values(
            user_id=user_id,
            concept_id=concept_id,
            mastery_score=mastery_score,
            mastery_state=mastery_state,
            first_mastered_at=first_mastered,
            last_reviewed_at=now,
            updated_by_source=source,
        ).on_conflict_do_update(
            constraint="uq_user_concept_mastery",
            set_=set_,
        )
        await self.session.execute(stmt)

    async def upsert_node_state(self, user_id: str, concept_id: str,
                                graph_version: int, state: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = pg_insert(UserConceptState.__table__).values(
            user_id=user_id,
            concept_id=concept_id,
            graph_version=graph_version,
            state=state,
            state_updated_at=now,
        ).on_conflict_do_update(
            constraint="uq_user_concept_state",
            set_={"state": state, "state_updated_at": now},
        )
        await self.session.execute(stmt)

    # ---- learning DNA -------------------------------------------------------

    async def next_dna_version(self, user_id: str) -> int:
        result = await self.session.execute(
            select(LearningDNA.dna_version)
            .where(LearningDNA.user_id == user_id)
            .order_by(LearningDNA.dna_version.desc())
            .limit(1)
        )
        latest = result.scalars().first()
        return (int(latest) + 1) if latest is not None else 1

    async def deactivate_active_dna(self, user_id: str) -> None:
        """Clear the current active DNA before inserting a new active one.

        The `uq_active_dna_per_user` partial unique index is enforced at INSERT
        time, before the schema's AFTER-INSERT one-active trigger can run, so we
        must deactivate the prior row explicitly within the same transaction.
        """
        await self.session.execute(
            text("UPDATE learning_dna SET is_active = FALSE WHERE user_id = :uid AND is_active = TRUE"),
            {"uid": user_id},
        )

    async def create_dna(self, dna: LearningDNA) -> LearningDNA:
        self.session.add(dna)
        await self.session.flush()
        return dna

    async def get_active_dna(self, user_id: str) -> Optional[LearningDNA]:
        result = await self.session.execute(
            select(LearningDNA).where(
                LearningDNA.user_id == user_id,
                LearningDNA.is_active.is_(True),
            )
        )
        return result.scalars().first()
