from typing import Optional

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import CurriculumPlan, DailyPlan


class CurriculumRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def latest_assessment_id(self, user_id: str, book_id: str) -> Optional[str]:
        row = await self.session.execute(
            text("""
                SELECT id FROM assessments
                WHERE user_id = :uid AND book_id = :bid AND status = 'COMPLETED'
                ORDER BY completed_at DESC NULLS LAST LIMIT 1
            """),
            {"uid": user_id, "bid": book_id},
        )
        r = row.first()
        return str(r[0]) if r else None

    async def next_version(self, user_id: str, book_id: str) -> int:
        row = await self.session.execute(
            select(CurriculumPlan.version)
            .where(CurriculumPlan.user_id == user_id, CurriculumPlan.book_id == book_id)
            .order_by(CurriculumPlan.version.desc())
            .limit(1)
        )
        latest = row.scalars().first()
        return (int(latest) + 1) if latest is not None else 1

    async def create_plan(self, plan: CurriculumPlan) -> CurriculumPlan:
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def latest_plan(self, user_id: str, book_id: str) -> Optional[CurriculumPlan]:
        row = await self.session.execute(
            select(CurriculumPlan)
            .where(CurriculumPlan.user_id == user_id, CurriculumPlan.book_id == book_id)
            .order_by(CurriculumPlan.version.desc())
            .limit(1)
        )
        return row.scalars().first()

    async def get_today_plan(self, user_id: str, book_id: str) -> "DailyPlan | None":
        row = await self.session.execute(
            select(DailyPlan).where(
                DailyPlan.user_id == user_id,
                DailyPlan.book_id == book_id,
                DailyPlan.plan_date == date.today(),
            )
        )
        return row.scalars().first()

    async def save_today_plan(self, user_id: str, book_id: str, learn_concept_ids: list) -> None:
        existing = await self.get_today_plan(user_id, book_id)
        if existing is not None:
            existing.learn_concept_ids = learn_concept_ids
        else:
            self.session.add(DailyPlan(
                user_id=user_id, book_id=book_id,
                plan_date=date.today(), learn_concept_ids=learn_concept_ids,
            ))
        await self.session.flush()

    async def daily_new_node_cap(self, user_id: str) -> int:
        row = await self.session.execute(
            text("SELECT daily_new_node_cap FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        r = row.first()
        return int(r[0]) if r and r[0] is not None else 10
