import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, String, func
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from app.models.base import Base


class LessonSession(Base):
    __tablename__ = "lesson_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    curriculum_plan_id = Column(UUID(as_uuid=True), ForeignKey("curriculum_plans.id", ondelete="SET NULL"), nullable=True)
    status = Column(
        ENUM('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'ABANDONED', name='lesson_status', create_type=False),
        nullable=False, default='NOT_STARTED',
    )
    generated_content = Column(JSONB, nullable=False)
    generation_metadata = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TutorInteraction(Base):
    __tablename__ = "tutor_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_session_id = Column(UUID(as_uuid=True), ForeignKey("lesson_sessions.id", ondelete="CASCADE"), nullable=False)
    turn_index = Column(Integer, nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=False)
    hint_level = Column(Integer, nullable=False, default=0)
    question_id = Column(UUID(as_uuid=True), ForeignKey("generated_questions.id", ondelete="SET NULL"), nullable=True)
    model_name = Column(String(100), nullable=True)
    token_input_count = Column(Integer, nullable=True)
    token_output_count = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
