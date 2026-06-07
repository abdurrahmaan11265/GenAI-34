from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept, ConceptEdge
from app.models.mastery import ConceptMastery, UserConceptState


class GraphRepository:
    """Read-only access for the personalized graph-reveal view."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_enrolled(self, user_id: str, book_id: str) -> bool:
        result = await self.session.execute(
            text("SELECT 1 FROM user_books WHERE user_id = :uid AND book_id = :bid"),
            {"uid": user_id, "bid": book_id},
        )
        return result.first() is not None

    async def active_graph_version(self, book_id: str) -> Optional[int]:
        result = await self.session.execute(
            select(Concept.graph_version)
            .where(Concept.book_id == book_id)
            .order_by(Concept.graph_version.desc())
            .limit(1)
        )
        v = result.scalars().first()
        return int(v) if v is not None else None

    async def concepts(self, book_id: str, graph_version: int) -> List[Concept]:
        result = await self.session.execute(
            select(Concept).where(
                Concept.book_id == book_id,
                Concept.graph_version == graph_version,
            )
        )
        return list(result.scalars().all())

    async def prerequisite_edges(self, book_id: str, graph_version: int) -> List[ConceptEdge]:
        result = await self.session.execute(
            select(ConceptEdge).where(
                ConceptEdge.book_id == book_id,
                ConceptEdge.graph_version == graph_version,
                ConceptEdge.edge_type == "PREREQUISITE",
            )
        )
        return list(result.scalars().all())

    async def node_states(self, user_id: str, book_id: str) -> Dict[str, str]:
        rows = await self.session.execute(
            text("""
                SELECT ucs.concept_id, ucs.state
                FROM user_concept_state ucs
                JOIN concepts c ON c.id = ucs.concept_id
                WHERE ucs.user_id = :uid AND c.book_id = :bid
            """),
            {"uid": user_id, "bid": book_id},
        )
        return {str(r.concept_id): r.state for r in rows}

    async def masteries(self, user_id: str, book_id: str) -> Dict[str, Tuple[float, Optional[str]]]:
        rows = await self.session.execute(
            text("""
                SELECT cm.concept_id, cm.mastery_score, cm.last_reviewed_at
                FROM concept_mastery cm
                JOIN concepts c ON c.id = cm.concept_id
                WHERE cm.user_id = :uid AND c.book_id = :bid
            """),
            {"uid": user_id, "bid": book_id},
        )
        out: Dict[str, Tuple[float, Optional[str]]] = {}
        for r in rows:
            out[str(r.concept_id)] = (
                float(r.mastery_score),
                r.last_reviewed_at.isoformat() if r.last_reviewed_at else None,
            )
        return out

    async def next_due(self, user_id: str, book_id: str) -> Dict[str, Optional[str]]:
        """FSRS next-due per concept. Empty until the FSRS engine (PR5) runs."""
        rows = await self.session.execute(
            text("""
                SELECT cf.concept_id, cf.next_due
                FROM concept_fsrs cf
                JOIN concepts c ON c.id = cf.concept_id
                WHERE cf.user_id = :uid AND c.book_id = :bid
            """),
            {"uid": user_id, "bid": book_id},
        )
        return {str(r.concept_id): (r.next_due.isoformat() if r.next_due else None) for r in rows}
