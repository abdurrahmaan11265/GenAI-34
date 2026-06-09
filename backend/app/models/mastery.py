from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, Index, CheckConstraint, ForeignKeyConstraint
import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID, ENUM
from app.models.base import Base


class UserConceptState(Base):
    __tablename__ = "user_concept_state"
    __table_args__ = (
    
            CheckConstraint('graph_version > 0', name='chk_ucs_graph_version'),
    
            ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='user_concept_state_concept_id_fkey'),
    
            ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='user_concept_state_user_id_fkey'),
    
            PrimaryKeyConstraint('id', name='user_concept_state_pkey'),
    
            UniqueConstraint('user_id', 'concept_id', 'graph_version', name='uq_user_concept_state'),
    
            Index('idx_ucs_concept', 'concept_id'),
    
            Index('idx_ucs_due', 'user_id', postgresql_where="(state = 'DUE'::node_state)"),
    
            Index('idx_ucs_locked', 'user_id', postgresql_where="(state = 'LOCKED'::node_state)"),
    
            Index('idx_ucs_state', 'state'),
    
            Index('idx_ucs_user', 'user_id'),
    
            Index('idx_ucs_user_state', 'user_id', 'state'),
    
            {'comment': 'DAG overlay per user: LOCKED|AVAILABLE|IN_PROGRESS|MASTERED|DUE. '
    
                    'Drives graph reveal UI.'}
    
        )


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    graph_version = Column(Integer, nullable=False)
    state = Column(
        ENUM('LOCKED', 'AVAILABLE', 'IN_PROGRESS', 'MASTERED', 'DUE', name='node_state', create_type=False),
        nullable=False, default='LOCKED',
    )
    state_updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ConceptMastery(Base):
    __tablename__ = "concept_mastery"
    __table_args__ = (
    
            CheckConstraint('mastery_score >= 0::numeric AND mastery_score <= 1::numeric', name='chk_mastery_score'),
    
            CheckConstraint("mastery_state <> 'MASTERED'::mastery_state OR first_mastered_at IS NOT NULL", name='chk_mastery_mastered_timestamp'),
    
            ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='concept_mastery_concept_id_fkey'),
    
            ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='concept_mastery_user_id_fkey'),
    
            PrimaryKeyConstraint('id', name='concept_mastery_pkey'),
    
            UniqueConstraint('user_id', 'concept_id', name='uq_user_concept_mastery'),
    
            Index('idx_concept_mastery_concept', 'concept_id'),
    
            Index('idx_concept_mastery_score', 'mastery_score'),
    
            Index('idx_concept_mastery_state', 'mastery_state'),
    
            Index('idx_concept_mastery_user', 'user_id'),
    
            Index('idx_concept_mastery_user_state', 'user_id', 'mastery_state'),
    
            Index('idx_mastery_user_concept_score', 'user_id', 'concept_id', 'mastery_score'),
    
            {'comment': 'Source of truth for numeric mastery score per (user, concept).'}
    
        )


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    mastery_score = Column(Numeric(5, 4), nullable=False, default=0)
    retention_score = Column(Numeric(5, 4), nullable=False, default=0)
    mastery_state = Column(
        ENUM('UNKNOWN', 'LEARNING', 'PRACTICING', 'MASTERED', 'FORGOTTEN', name='mastery_state', create_type=False),
        nullable=False, default='UNKNOWN',
    )
    first_mastered_at = Column(DateTime(timezone=True), nullable=True)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    updated_by_source = Column(
        ENUM('ASSESSMENT', 'LESSON', 'QUIZ', 'REVISION', 'MANUAL', name='review_source', create_type=False),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
