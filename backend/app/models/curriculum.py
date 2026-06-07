import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Date, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base


class DailyPlan(Base):
    __tablename__ = "daily_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    plan_date = Column(Date, nullable=False)
    learn_concept_ids = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CurriculumPlan(Base):
    __tablename__ = "curriculum_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    curriculum_json = Column(JSONB, nullable=False)
    generated_from_assessment = Column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
