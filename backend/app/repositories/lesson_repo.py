from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.concept import Concept
from app.models.question import GeneratedQuestion
from app.models.lesson import LessonSession, TutorInteraction

SOURCE_TEXT_MAX_CHARS = 2500


class LessonRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_enrolled(self, user_id: str, book_id: str) -> bool:
        r = await self.session.execute(
            text("SELECT 1 FROM user_books WHERE user_id = :uid AND book_id = :bid"),
            {"uid": user_id, "bid": book_id})
        return r.first() is not None

    async def get_concept(self, concept_id: str) -> Optional[Concept]:
        r = await self.session.execute(select(Concept).where(Concept.id == concept_id))
        return r.scalars().first()

    async def get_source_text(self, concept_id: str) -> str:
        """Concatenated source chunks for grounding; falls back to empty."""
        r = await self.session.execute(
            text("""
                SELECT sc.content
                FROM concept_chunks cc
                JOIN source_chunks sc ON sc.id = cc.chunk_id
                WHERE cc.concept_id = :cid
                ORDER BY sc.created_at ASC
                LIMIT 4
            """),
            {"cid": concept_id})
        chunks = [row[0] for row in r if row[0]]
        return ("\n\n".join(chunks))[:SOURCE_TEXT_MAX_CHARS]

    async def get_mastery(self, user_id: str, concept_id: str) -> float:
        r = await self.session.execute(
            text("SELECT mastery_score FROM concept_mastery WHERE user_id = :uid AND concept_id = :cid"),
            {"uid": user_id, "cid": concept_id})
        row = r.first()
        return float(row[0]) if row else 0.0

    # ---- lesson sessions ----------------------------------------------------

    async def create_session(self, sess: LessonSession) -> LessonSession:
        self.session.add(sess)
        await self.session.flush()
        return sess

    async def get_session(self, session_id: str) -> Optional[LessonSession]:
        r = await self.session.execute(select(LessonSession).where(LessonSession.id == session_id))
        return r.scalars().first()

    async def get_active_session(self, user_id: str, concept_id: str) -> Optional[LessonSession]:
        """Most recent IN_PROGRESS lesson for this user+concept (for resume)."""
        r = await self.session.execute(
            select(LessonSession)
            .where(
                LessonSession.user_id == user_id,
                LessonSession.concept_id == concept_id,
                LessonSession.status == "IN_PROGRESS",
            )
            .order_by(LessonSession.created_at.desc())
            .limit(1)
        )
        return r.scalars().first()

    # ---- tutor interactions -------------------------------------------------

    async def get_turns(self, session_id: str) -> List[TutorInteraction]:
        r = await self.session.execute(
            select(TutorInteraction)
            .where(TutorInteraction.lesson_session_id == session_id)
            .order_by(TutorInteraction.turn_index.asc()))
        return list(r.scalars().all())

    async def create_turn(self, turn: TutorInteraction) -> TutorInteraction:
        self.session.add(turn)
        await self.session.flush()
        return turn

    async def create_user_asked_question(self, concept_id: str, question_text: str) -> str:
        """Capture a learner's own question (source=USER_ASKED) for later revision."""
        q = GeneratedQuestion(
            concept_id=concept_id,
            question_type="SHORT_ANSWER",
            question_source="USER_ASKED",
            difficulty_level=3,
            question_text=question_text,
            answer_key={"note": "captured from tutor session"},
        )
        self.session.add(q)
        await self.session.flush()
        return str(q.id)
