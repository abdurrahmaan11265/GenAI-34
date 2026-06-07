from typing import Any, Optional
import datetime
import decimal
import enum
import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, Double, Enum, ForeignKeyConstraint, Index, Integer, Numeric, PrimaryKeyConstraint, String, Table, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class AssessmentStatus(str, enum.Enum):
    DRAFT = 'DRAFT'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    ABANDONED = 'ABANDONED'


class AssessmentType(str, enum.Enum):
    INITIAL = 'INITIAL'
    PLACEMENT = 'PLACEMENT'
    CHAPTER = 'CHAPTER'
    REVISION = 'REVISION'


class BookStatus(str, enum.Enum):
    UPLOADING = 'UPLOADING'
    PARSING = 'PARSING'
    EXTRACTING_CONCEPTS = 'EXTRACTING_CONCEPTS'
    KG_BUILT = 'KG_BUILT'
    KG_VERIFIED = 'KG_VERIFIED'
    READY = 'READY'
    FAILED = 'FAILED'
    ARCHIVED = 'ARCHIVED'


class BookVisibility(str, enum.Enum):
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'
    TEAM = 'TEAM'


class EdgeType(str, enum.Enum):
    PREREQUISITE = 'PREREQUISITE'
    RELATED = 'RELATED'


class ExperienceLevel(str, enum.Enum):
    BEGINNER = 'BEGINNER'
    INTERMEDIATE = 'INTERMEDIATE'
    ADVANCED = 'ADVANCED'


class GraphBuildStatus(str, enum.Enum):
    QUEUED = 'QUEUED'
    PARSING = 'PARSING'
    EXTRACTING_CONCEPTS = 'EXTRACTING_CONCEPTS'
    BUILDING_GRAPH = 'BUILDING_GRAPH'
    VALIDATING = 'VALIDATING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CHUNKING = 'CHUNKING'
    CANONICALIZING = 'CANONICALIZING'
    EXTRACTING_RELATIONSHIPS = 'EXTRACTING_RELATIONSHIPS'
    REPAIRING = 'REPAIRING'
    PUBLISHING = 'PUBLISHING'


class LessonStatus(str, enum.Enum):
    NOT_STARTED = 'NOT_STARTED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    ABANDONED = 'ABANDONED'


class MasteryState(str, enum.Enum):
    UNKNOWN = 'UNKNOWN'
    LEARNING = 'LEARNING'
    PRACTICING = 'PRACTICING'
    MASTERED = 'MASTERED'
    FORGOTTEN = 'FORGOTTEN'


class NodeState(str, enum.Enum):
    LOCKED = 'LOCKED'
    AVAILABLE = 'AVAILABLE'
    IN_PROGRESS = 'IN_PROGRESS'
    MASTERED = 'MASTERED'
    DUE = 'DUE'


class NotificationType(str, enum.Enum):
    REVISION_DUE = 'REVISION_DUE'
    STREAK_WARNING = 'STREAK_WARNING'
    GRAPH_BUILT = 'GRAPH_BUILT'
    SYSTEM_ALERT = 'SYSTEM_ALERT'


class PlacementState(str, enum.Enum):
    MASTERED = 'MASTERED'
    READY = 'READY'
    LEARNING = 'LEARNING'
    WEAK = 'WEAK'
    UNKNOWN = 'UNKNOWN'


class QuestionSource(str, enum.Enum):
    GENERATED = 'GENERATED'
    USER_ASKED = 'USER_ASKED'
    ASSESSMENT_MISS = 'ASSESSMENT_MISS'
    REVISION = 'REVISION'


class QuestionType(str, enum.Enum):
    MCQ = 'MCQ'
    TRUE_FALSE = 'TRUE_FALSE'
    SHORT_ANSWER = 'SHORT_ANSWER'
    SCENARIO = 'SCENARIO'
    ORDERING = 'ORDERING'
    MATCHING = 'MATCHING'


class ReviewSource(str, enum.Enum):
    ASSESSMENT = 'ASSESSMENT'
    LESSON = 'LESSON'
    QUIZ = 'QUIZ'
    REVISION = 'REVISION'
    MANUAL = 'MANUAL'


class UploadStatus(str, enum.Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class UserRole(str, enum.Enum):
    STUDENT = 'STUDENT'
    ADMIN = 'ADMIN'


t_mv_concept_performance = Table(
    'mv_concept_performance', Base.metadata,
    Column('concept_id', Uuid),
    Column('attempts', BigInteger),
    Column('accuracy_rate', Numeric),
    Column('average_confidence', Numeric),
    Column('confident_wrong_count', BigInteger),
    Index('idx_mv_concept_performance_concept', 'concept_id'),
    Index('uq_mv_concept_performance', 'concept_id', unique=True)
)


t_mv_revision_queue = Table(
    'mv_revision_queue', Base.metadata,
    Column('user_id', Uuid),
    Column('concept_id', Uuid),
    Column('concept_name', Text),
    Column('book_id', Uuid),
    Column('difficulty_level', Integer),
    Column('next_due', DateTime(True)),
    Column('retrievability', Double(53)),
    Column('stability', Double(53)),
    Column('difficulty', Double(53)),
    Column('repetitions', Integer),
    Column('lapses', Integer),
    Index('idx_mv_revision_queue_due', 'user_id', 'next_due'),
    Index('idx_mv_revision_queue_user', 'user_id'),
    Index('uq_mv_revision_queue', 'user_id', 'concept_id', unique=True)
)


t_mv_user_book_progress = Table(
    'mv_user_book_progress', Base.metadata,
    Column('user_id', Uuid),
    Column('book_id', Uuid),
    Column('total_concepts', BigInteger),
    Column('mastered_concepts', BigInteger),
    Column('learning_concepts', BigInteger),
    Column('forgotten_concepts', BigInteger),
    Column('average_mastery', Numeric),
    Index('idx_mv_user_book_progress', 'user_id', 'book_id'),
    Index('uq_mv_user_book_progress', 'user_id', 'book_id', unique=True)
)


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='users_pkey'),
        UniqueConstraint('email', name='users_email_key'),
        Index('idx_users_active', 'is_active', postgresql_where='(is_active = true)'),
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role'),
        {'comment': 'Platform users.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda cls: [member.value for member in cls], name='user_role'), nullable=False, server_default=text("'STUDENT'::user_role"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    daily_new_node_cap: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('10'))
    session_length_pref: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('30'))
    notify_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    notify_due_reviews: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    notify_processing: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    global_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    last_login_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    daily_reminder_time: Mapped[Optional[str]] = mapped_column(String(5))
    last_active_date: Mapped[Optional[datetime.date]] = mapped_column(Date)

    books: Mapped[list['Books']] = relationship('Books', back_populates='owner')
    content_completions: Mapped[list['ContentCompletions']] = relationship('ContentCompletions', back_populates='user')
    daily_activity: Mapped[list['DailyActivity']] = relationship('DailyActivity', back_populates='user')
    learner_profiles: Mapped['LearnerProfiles'] = relationship('LearnerProfiles', uselist=False, back_populates='user')
    learning_dna: Mapped[list['LearningDna']] = relationship('LearningDna', back_populates='user')
    notifications: Mapped[list['Notifications']] = relationship('Notifications', back_populates='user')
    assessments: Mapped[list['Assessments']] = relationship('Assessments', back_populates='user')
    book_streaks: Mapped[list['BookStreaks']] = relationship('BookStreaks', back_populates='user')
    book_uploads: Mapped[list['BookUploads']] = relationship('BookUploads', back_populates='user')
    progress_snapshots: Mapped[list['ProgressSnapshots']] = relationship('ProgressSnapshots', back_populates='user')
    curriculum_plans: Mapped[list['CurriculumPlans']] = relationship('CurriculumPlans', back_populates='user')
    concept_fsrs: Mapped[list['ConceptFsrs']] = relationship('ConceptFsrs', back_populates='user')
    concept_mastery: Mapped[list['ConceptMastery']] = relationship('ConceptMastery', back_populates='user')
    fsrs_reviews: Mapped[list['FsrsReviews']] = relationship('FsrsReviews', back_populates='user')
    lesson_sessions: Mapped[list['LessonSessions']] = relationship('LessonSessions', back_populates='user')
    mastery_events: Mapped[list['MasteryEvents']] = relationship('MasteryEvents', back_populates='user')
    user_concept_state: Mapped[list['UserConceptState']] = relationship('UserConceptState', back_populates='user')
    user_books: Mapped[list['UserBooks']] = relationship('UserBooks', back_populates='user')


t_v_book_progress = Table(
    'v_book_progress', Base.metadata,
    Column('user_id', Uuid),
    Column('book_id', Uuid),
    Column('total_concepts', BigInteger),
    Column('mastered_concepts', BigInteger),
    Column('progress_percent', Numeric)
)


t_v_concept_prerequisites = Table(
    'v_concept_prerequisites', Base.metadata,
    Column('concept_id', Uuid),
    Column('prerequisite_id', Uuid),
    Column('prerequisite_name', Text),
    Column('confidence', Numeric(5, 4)),
    Column('is_verified', Boolean)
)


t_v_user_mastery_summary = Table(
    'v_user_mastery_summary', Base.metadata,
    Column('user_id', Uuid),
    Column('total_concepts', BigInteger),
    Column('mastered', BigInteger),
    Column('learning', BigInteger),
    Column('forgotten', BigInteger),
    Column('avg_mastery', Numeric)
)


t_v_user_revision_tasks = Table(
    'v_user_revision_tasks', Base.metadata,
    Column('user_id', Uuid),
    Column('concept_id', Uuid),
    Column('name', Text),
    Column('book_id', Uuid),
    Column('next_due', DateTime(True)),
    Column('retrievability', Double(53)),
    Column('stability', Double(53)),
    Column('lapses', Integer)
)


class Books(Base):
    __tablename__ = 'books'
    __table_args__ = (
        CheckConstraint('page_count IS NULL OR page_count > 0', name='chk_page_count'),
        CheckConstraint('processing_completed_at IS NULL OR processing_started_at IS NULL OR processing_completed_at >= processing_started_at', name='chk_processing_time'),
        CheckConstraint("source_type::text = ANY (ARRAY['PDF'::character varying, 'EPUB'::character varying, 'TXT'::character varying, 'DOCX'::character varying, 'URL'::character varying]::text[])", name='books_source_type_check'),
        ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL', name='fk_books_owner'),
        PrimaryKeyConstraint('id', name='books_pkey'),
        Index('idx_books_created_at', 'created_at'),
        Index('idx_books_owner', 'owner_id'),
        Index('idx_books_status', 'status'),
        Index('idx_books_title', 'title'),
        Index('idx_books_visibility', 'visibility'),
        {'comment': 'Uploaded books and learning resources. Status lifecycle: '
                'UPLOADINGΓåÆPARSINGΓåÆEXTRACTING_CONCEPTSΓåÆKG_BUILTΓåÆKG_VERIFIEDΓåÆREADY.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'en'::character varying"))
    status: Mapped[BookStatus] = mapped_column(Enum(BookStatus, values_callable=lambda cls: [member.value for member in cls], name='book_status'), nullable=False, server_default=text("'UPLOADING'::book_status"))
    visibility: Mapped[BookVisibility] = mapped_column(Enum(BookVisibility, values_callable=lambda cls: [member.value for member in cls], name='book_visibility'), nullable=False, server_default=text("'PRIVATE'::book_visibility"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    author: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    file_url: Mapped[Optional[str]] = mapped_column(Text)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    processing_started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    processing_completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    owner: Mapped[Optional['Users']] = relationship('Users', back_populates='books')
    assessments: Mapped[list['Assessments']] = relationship('Assessments', back_populates='book')
    book_streaks: Mapped[list['BookStreaks']] = relationship('BookStreaks', back_populates='book')
    book_uploads: Mapped[list['BookUploads']] = relationship('BookUploads', back_populates='book')
    chapters: Mapped[list['Chapters']] = relationship('Chapters', back_populates='book')
    progress_snapshots: Mapped[list['ProgressSnapshots']] = relationship('ProgressSnapshots', back_populates='book')
    concepts: Mapped[list['Concepts']] = relationship('Concepts', back_populates='book')
    curriculum_plans: Mapped[list['CurriculumPlans']] = relationship('CurriculumPlans', back_populates='book')
    graph_build_jobs: Mapped[list['GraphBuildJobs']] = relationship('GraphBuildJobs', back_populates='book')
    source_chunks: Mapped[list['SourceChunks']] = relationship('SourceChunks', back_populates='book')
    concept_edges: Mapped[list['ConceptEdges']] = relationship('ConceptEdges', back_populates='book')
    graph_versions: Mapped[list['GraphVersions']] = relationship('GraphVersions', back_populates='book')
    user_books: Mapped[list['UserBooks']] = relationship('UserBooks', back_populates='book')


class ContentCompletions(Base):
    __tablename__ = 'content_completions'
    __table_args__ = (
        CheckConstraint('content_version > 0', name='chk_content_version'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='content_completions_user_id_fkey'),
        PrimaryKeyConstraint('id', name='content_completions_pkey'),
        UniqueConstraint('user_id', 'content_type', 'content_id', 'content_version', name='uq_completion'),
        Index('idx_content_completions_content', 'content_type', 'content_id'),
        Index('idx_content_completions_user', 'user_id'),
        {'comment': 'Idempotency guard for bonus awards. First completion wins.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    content_version: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    user: Mapped['Users'] = relationship('Users', back_populates='content_completions')


class DailyActivity(Base):
    __tablename__ = 'daily_activity'
    __table_args__ = (
        CheckConstraint('assessments_completed >= 0', name='chk_assessments_comp'),
        CheckConstraint('concepts_learned >= 0', name='chk_concepts_learned'),
        CheckConstraint('concepts_reviewed >= 0', name='chk_concepts_reviewed'),
        CheckConstraint('lessons_completed >= 0', name='chk_lessons_completed'),
        CheckConstraint('minutes_studied >= 0', name='chk_minutes_studied'),
        CheckConstraint('questions_answered >= 0', name='chk_questions_answered'),
        CheckConstraint('tutor_messages_sent >= 0', name='chk_tutor_messages'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='daily_activity_user_id_fkey'),
        PrimaryKeyConstraint('id', name='daily_activity_pkey'),
        UniqueConstraint('user_id', 'activity_date', name='uq_daily_activity'),
        Index('idx_daily_activity_date', 'activity_date'),
        Index('idx_daily_activity_user', 'user_id'),
        Index('idx_daily_activity_user_date', 'user_id', 'activity_date'),
        {'comment': 'One row per (user, date). Source of truth for streak computation.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    activity_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    minutes_studied: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    concepts_learned: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    concepts_reviewed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    lessons_completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    assessments_completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    questions_answered: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    tutor_messages_sent: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    user: Mapped['Users'] = relationship('Users', back_populates='daily_activity')


class LearnerProfiles(Base):
    __tablename__ = 'learner_profiles'
    __table_args__ = (
        CheckConstraint('confidence_level IS NULL OR confidence_level >= 1 AND confidence_level <= 5', name='chk_confidence'),
        CheckConstraint('preferred_study_minutes IS NULL OR preferred_study_minutes > 0', name='chk_study_minutes'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='learner_profiles_user_id_fkey'),
        PrimaryKeyConstraint('id', name='learner_profiles_pkey'),
        UniqueConstraint('user_id', name='learner_profiles_user_id_key'),
        {'comment': 'Learner preferences and initial calibration.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    confidence_level: Mapped[Optional[int]] = mapped_column(Integer)
    experience_level: Mapped[Optional[ExperienceLevel]] = mapped_column(Enum(ExperienceLevel, values_callable=lambda cls: [member.value for member in cls], name='experience_level'))
    preferred_examples: Mapped[Optional[str]] = mapped_column(String(100))
    learning_velocity: Mapped[Optional[str]] = mapped_column(String(20))
    preferred_study_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped['Users'] = relationship('Users', back_populates='learner_profiles')


class LearningDna(Base):
    __tablename__ = 'learning_dna'
    __table_args__ = (
        CheckConstraint('dna_version > 0', name='chk_dna_version'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='learning_dna_user_id_fkey'),
        PrimaryKeyConstraint('id', name='learning_dna_pkey'),
        UniqueConstraint('user_id', 'dna_version', name='uq_user_dna_version'),
        Index('idx_learning_dna_data', 'dna_data', postgresql_using='gin'),
        Index('idx_learning_dna_user', 'user_id'),
        Index('uq_active_dna_per_user', 'user_id', postgresql_where='(is_active = true)', unique=True),
        {'comment': 'Versioned personalized learner model. Append-only.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    dna_version: Mapped[int] = mapped_column(Integer, nullable=False)
    dna_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    user: Mapped['Users'] = relationship('Users', back_populates='learning_dna')


class LearningStreaks(Users):
    __tablename__ = 'learning_streaks'
    __table_args__ = (
        CheckConstraint('current_streak_days >= 0', name='chk_current_streak'),
        CheckConstraint('longest_streak_days >= 0', name='chk_longest_streak'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='learning_streaks_user_id_fkey'),
        PrimaryKeyConstraint('user_id', name='learning_streaks_pkey'),
        {'comment': 'Global daily-activity streak per user.'}
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    current_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    longest_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    last_activity_date: Mapped[Optional[datetime.date]] = mapped_column(Date)


class Notifications(Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='notifications_user_id_fkey'),
        PrimaryKeyConstraint('id', name='notifications_pkey'),
        Index('idx_notifications_unread', 'user_id', postgresql_where='(is_read = false)'),
        Index('idx_notifications_user', 'user_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, values_callable=lambda cls: [member.value for member in cls], name='notification_type'), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    action_url: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped['Users'] = relationship('Users', back_populates='notifications')


class Assessments(Base):
    __tablename__ = 'assessments'
    __table_args__ = (
        CheckConstraint('completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at', name='chk_assessment_time'),
        CheckConstraint('score_percentage IS NULL OR score_percentage >= 0::numeric AND score_percentage <= 100::numeric', name='chk_score'),
        CheckConstraint('total_questions IS NULL OR total_questions > 0', name='chk_total_questions'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='assessments_book_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='assessments_user_id_fkey'),
        PrimaryKeyConstraint('id', name='assessments_pkey'),
        Index('idx_active_assessments', 'user_id', postgresql_where="(status = 'IN_PROGRESS'::assessment_status)"),
        Index('idx_assessment_user_book', 'user_id', 'book_id'),
        Index('idx_assessments_book', 'book_id'),
        Index('idx_assessments_status', 'status'),
        Index('idx_assessments_user', 'user_id'),
        {'comment': 'Placement/chapter/revision assessments per user per book.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    assessment_type: Mapped[AssessmentType] = mapped_column(Enum(AssessmentType, values_callable=lambda cls: [member.value for member in cls], name='assessment_type'), nullable=False)
    status: Mapped[AssessmentStatus] = mapped_column(Enum(AssessmentStatus, values_callable=lambda cls: [member.value for member in cls], name='assessment_status'), nullable=False, server_default=text("'DRAFT'::assessment_status"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    total_questions: Mapped[Optional[int]] = mapped_column(Integer)
    score_percentage: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2))

    book: Mapped['Books'] = relationship('Books', back_populates='assessments')
    user: Mapped['Users'] = relationship('Users', back_populates='assessments')
    curriculum_plans: Mapped[list['CurriculumPlans']] = relationship('CurriculumPlans', back_populates='assessments')
    assessment_outcomes: Mapped[list['AssessmentOutcomes']] = relationship('AssessmentOutcomes', back_populates='assessment')
    assessment_responses: Mapped[list['AssessmentResponses']] = relationship('AssessmentResponses', back_populates='assessment')


class BookStreaks(Base):
    __tablename__ = 'book_streaks'
    __table_args__ = (
        CheckConstraint('current_streak_days >= 0', name='chk_book_current_streak'),
        CheckConstraint('longest_streak_days >= 0', name='chk_book_longest_streak'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='book_streaks_book_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='book_streaks_user_id_fkey'),
        PrimaryKeyConstraint('id', name='book_streaks_pkey'),
        UniqueConstraint('user_id', 'book_id', name='uq_book_streak'),
        Index('idx_book_streaks_book', 'book_id'),
        Index('idx_book_streaks_user', 'user_id'),
        {'comment': 'Per-book consistency streak per user.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    current_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    longest_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    last_activity_date: Mapped[Optional[datetime.date]] = mapped_column(Date)

    book: Mapped['Books'] = relationship('Books', back_populates='book_streaks')
    user: Mapped['Users'] = relationship('Users', back_populates='book_streaks')


class BookUploads(Base):
    __tablename__ = 'book_uploads'
    __table_args__ = (
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='book_uploads_book_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='book_uploads_user_id_fkey'),
        PrimaryKeyConstraint('id', name='book_uploads_pkey')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    upload_status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus, values_callable=lambda cls: [member.value for member in cls], name='upload_status'), nullable=False, server_default=text("'PENDING'::upload_status"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    mime_type: Mapped[Optional[str]] = mapped_column(Text)

    book: Mapped[Optional['Books']] = relationship('Books', back_populates='book_uploads')
    user: Mapped[Optional['Users']] = relationship('Users', back_populates='book_uploads')
    graph_build_jobs: Mapped[list['GraphBuildJobs']] = relationship('GraphBuildJobs', back_populates='book_upload')
    source_chunks: Mapped[list['SourceChunks']] = relationship('SourceChunks', back_populates='book_upload')


class Chapters(Base):
    __tablename__ = 'chapters'
    __table_args__ = (
        CheckConstraint('chapter_number > 0', name='chk_chapter_number'),
        CheckConstraint('estimated_minutes IS NULL OR estimated_minutes > 0', name='chk_estimated_minutes'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='chapters_book_id_fkey'),
        PrimaryKeyConstraint('id', name='chapters_pkey'),
        UniqueConstraint('book_id', 'chapter_number', name='uq_book_chapter_number'),
        Index('idx_chapters_book_id', 'book_id'),
        Index('idx_chapters_number', 'book_id', 'chapter_number'),
        {'comment': 'Book chapters. Structural prior for concept extraction and '
                'chunking.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer)

    book: Mapped['Books'] = relationship('Books', back_populates='chapters')
    concepts: Mapped[list['Concepts']] = relationship('Concepts', back_populates='chapter')
    source_chunks: Mapped[list['SourceChunks']] = relationship('SourceChunks', back_populates='chapter')
    user_books: Mapped[list['UserBooks']] = relationship('UserBooks', back_populates='current_chapter')


class ProgressSnapshots(Base):
    __tablename__ = 'progress_snapshots'
    __table_args__ = (
        CheckConstraint('average_mastery IS NULL OR average_mastery >= 0::numeric AND average_mastery <= 1::numeric', name='chk_avg_mastery'),
        CheckConstraint('average_retrievability IS NULL OR average_retrievability >= 0::numeric AND average_retrievability <= 1::numeric', name='chk_avg_retrievability'),
        CheckConstraint('overall_progress >= 0::numeric AND overall_progress <= 100::numeric', name='chk_progress'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='progress_snapshots_book_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='progress_snapshots_user_id_fkey'),
        PrimaryKeyConstraint('id', name='progress_snapshots_pkey'),
        UniqueConstraint('user_id', 'book_id', 'snapshot_date', name='uq_snapshot'),
        Index('idx_progress_snapshots_book', 'book_id'),
        Index('idx_progress_snapshots_date', 'snapshot_date'),
        Index('idx_progress_snapshots_user', 'user_id'),
        Index('idx_progress_user_book', 'user_id', 'book_id'),
        {'comment': 'Daily snapshot of per-book progress metrics for trend charts.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    mastered_concepts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    learning_concepts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    weak_concepts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    total_concepts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    overall_progress: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default=text('0'))
    snapshot_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    average_mastery: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))
    average_retrievability: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))

    book: Mapped['Books'] = relationship('Books', back_populates='progress_snapshots')
    user: Mapped['Users'] = relationship('Users', back_populates='progress_snapshots')


class Concepts(Base):
    __tablename__ = 'concepts'
    __table_args__ = (
        CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5', name='chk_concept_difficulty'),
        CheckConstraint('estimated_minutes IS NULL OR estimated_minutes > 0', name='chk_concept_minutes'),
        CheckConstraint('graph_version > 0', name='chk_concept_graph_version'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='concepts_book_id_fkey'),
        ForeignKeyConstraint(['canonical_concept_id'], ['concepts.id'], ondelete='SET NULL', name='concepts_canonical_concept_id_fkey'),
        ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='SET NULL', name='concepts_chapter_id_fkey'),
        PrimaryKeyConstraint('id', name='concepts_pkey'),
        UniqueConstraint('book_id', 'name', 'graph_version', name='uq_concept_book_name_version'),
        Index('idx_concepts_book', 'book_id'),
        Index('idx_concepts_canonical', 'canonical_concept_id'),
        Index('idx_concepts_chapter', 'chapter_id'),
        Index('idx_concepts_difficulty', 'difficulty_level'),
        Index('idx_concepts_graph_version', 'book_id', 'graph_version'),
        Index('idx_concepts_metadata', 'metadata', postgresql_using='gin'),
        Index('idx_concepts_name', 'name'),
        Index('idx_concepts_search', 'search_vector', postgresql_using='gin'),
        {'comment': 'KG nodes ΓÇö canonical concepts extracted from books per graph '
                'version.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    canonical_concept_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    learning_objective: Mapped[Optional[str]] = mapped_column(Text)
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_: Mapped[Optional[dict]] = mapped_column('metadata', JSONB)
    search_vector: Mapped[Optional[Any]] = mapped_column(TSVECTOR)

    book: Mapped['Books'] = relationship('Books', back_populates='concepts')
    canonical_concept: Mapped[Optional['Concepts']] = relationship('Concepts', remote_side=[id], back_populates='canonical_concept_reverse')
    canonical_concept_reverse: Mapped[list['Concepts']] = relationship('Concepts', remote_side=[canonical_concept_id], back_populates='canonical_concept')
    chapter: Mapped[Optional['Chapters']] = relationship('Chapters', back_populates='concepts')
    assessment_outcomes: Mapped[list['AssessmentOutcomes']] = relationship('AssessmentOutcomes', back_populates='concept')
    concept_chunks: Mapped[list['ConceptChunks']] = relationship('ConceptChunks', back_populates='concept')
    concept_edges_from_concept: Mapped[list['ConceptEdges']] = relationship('ConceptEdges', foreign_keys='[ConceptEdges.from_concept_id]', back_populates='from_concept')
    concept_edges_to_concept: Mapped[list['ConceptEdges']] = relationship('ConceptEdges', foreign_keys='[ConceptEdges.to_concept_id]', back_populates='to_concept')
    concept_fsrs: Mapped[list['ConceptFsrs']] = relationship('ConceptFsrs', back_populates='concept')
    concept_mastery: Mapped[list['ConceptMastery']] = relationship('ConceptMastery', back_populates='concept')
    fsrs_reviews: Mapped[list['FsrsReviews']] = relationship('FsrsReviews', back_populates='concept')
    generated_questions: Mapped[list['GeneratedQuestions']] = relationship('GeneratedQuestions', back_populates='concept')
    lesson_sessions: Mapped[list['LessonSessions']] = relationship('LessonSessions', back_populates='concept')
    mastery_events: Mapped[list['MasteryEvents']] = relationship('MasteryEvents', back_populates='concept')
    user_concept_state: Mapped[list['UserConceptState']] = relationship('UserConceptState', back_populates='concept')
    assessment_responses: Mapped[list['AssessmentResponses']] = relationship('AssessmentResponses', back_populates='concept')
    evaluated_pairs_source_concept: Mapped[list['EvaluatedPairs']] = relationship('EvaluatedPairs', foreign_keys='[EvaluatedPairs.source_concept_id]', back_populates='source_concept')
    evaluated_pairs_target_concept: Mapped[list['EvaluatedPairs']] = relationship('EvaluatedPairs', foreign_keys='[EvaluatedPairs.target_concept_id]', back_populates='target_concept')
    relationship_candidates_source_concept: Mapped[list['RelationshipCandidates']] = relationship('RelationshipCandidates', foreign_keys='[RelationshipCandidates.source_concept_id]', back_populates='source_concept')
    relationship_candidates_target_concept: Mapped[list['RelationshipCandidates']] = relationship('RelationshipCandidates', foreign_keys='[RelationshipCandidates.target_concept_id]', back_populates='target_concept')


class CurriculumPlans(Base):
    __tablename__ = 'curriculum_plans'
    __table_args__ = (
        CheckConstraint('version > 0', name='chk_curriculum_version'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='curriculum_plans_book_id_fkey'),
        ForeignKeyConstraint(['generated_from_assessment'], ['assessments.id'], ondelete='SET NULL', name='curriculum_plans_generated_from_assessment_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='curriculum_plans_user_id_fkey'),
        PrimaryKeyConstraint('id', name='curriculum_plans_pkey'),
        UniqueConstraint('user_id', 'book_id', 'version', name='uq_curriculum_user_book_version'),
        Index('idx_curriculum_book', 'book_id'),
        Index('idx_curriculum_json', 'curriculum_json', postgresql_using='gin'),
        Index('idx_curriculum_user', 'user_id'),
        Index('idx_curriculum_user_book_version', 'user_id', 'book_id', 'version'),
        {'comment': 'Generated learning order for a user on a book.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    curriculum_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    generated_from_assessment: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)

    book: Mapped['Books'] = relationship('Books', back_populates='curriculum_plans')
    assessments: Mapped[Optional['Assessments']] = relationship('Assessments', back_populates='curriculum_plans')
    user: Mapped['Users'] = relationship('Users', back_populates='curriculum_plans')
    lesson_sessions: Mapped[list['LessonSessions']] = relationship('LessonSessions', back_populates='curriculum_plan')


class GraphBuildJobs(Base):
    __tablename__ = 'graph_build_jobs'
    __table_args__ = (
        CheckConstraint('chunks_processed IS NULL OR chunks_processed >= 0', name='chk_chunks_processed'),
        CheckConstraint('completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at', name='chk_graph_job_time'),
        CheckConstraint('concepts_created IS NULL OR concepts_created >= 0', name='chk_concepts_created'),
        CheckConstraint('edges_created IS NULL OR edges_created >= 0', name='chk_edges_created'),
        CheckConstraint('graph_version > 0', name='chk_graph_version_positive'),
        CheckConstraint('nodes_created IS NULL OR nodes_created >= 0', name='chk_nodes_created'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='graph_build_jobs_book_id_fkey'),
        ForeignKeyConstraint(['book_upload_id'], ['book_uploads.id'], ondelete='CASCADE', name='graph_build_jobs_book_upload_id_fkey'),
        PrimaryKeyConstraint('id', name='graph_build_jobs_pkey'),
        Index('idx_graph_build_jobs_book', 'book_id'),
        Index('idx_graph_build_jobs_metadata', 'metadata', postgresql_using='gin'),
        Index('idx_graph_build_jobs_status', 'status'),
        Index('idx_graph_build_jobs_version', 'book_id', 'graph_version'),
        Index('uq_completed_graph_version', 'book_id', 'graph_version', postgresql_where="(status = 'COMPLETED'::graph_build_status)", unique=True),
        {'comment': 'Async pipeline job tracker. Only one COMPLETED build per (book, '
                'graph_version).'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[GraphBuildStatus] = mapped_column(Enum(GraphBuildStatus, values_callable=lambda cls: [member.value for member in cls], name='graph_build_status'), nullable=False, server_default=text("'QUEUED'::graph_build_status"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    current_offset: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    nodes_created: Mapped[Optional[int]] = mapped_column(Integer)
    edges_created: Mapped[Optional[int]] = mapped_column(Integer)
    concepts_created: Mapped[Optional[int]] = mapped_column(Integer)
    chunks_processed: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[Optional[dict]] = mapped_column('metadata', JSONB)
    book_upload_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    current_stage: Mapped[Optional[str]] = mapped_column(String(50))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    next_retry_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    book: Mapped['Books'] = relationship('Books', back_populates='graph_build_jobs')
    book_upload: Mapped[Optional['BookUploads']] = relationship('BookUploads', back_populates='graph_build_jobs')
    graph_versions: Mapped[list['GraphVersions']] = relationship('GraphVersions', back_populates='build_job')


class SourceChunks(Base):
    __tablename__ = 'source_chunks'
    __table_args__ = (
        CheckConstraint('chunk_index >= 0', name='chk_chunk_index'),
        CheckConstraint('page_start IS NULL AND page_end IS NULL OR page_start IS NOT NULL AND page_end IS NOT NULL AND page_end >= page_start', name='chk_page_numbers'),
        CheckConstraint('token_count IS NULL OR token_count > 0', name='chk_token_count'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='source_chunks_book_id_fkey'),
        ForeignKeyConstraint(['book_upload_id'], ['book_uploads.id'], ondelete='CASCADE', name='source_chunks_book_upload_id_fkey'),
        ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='SET NULL', name='source_chunks_chapter_id_fkey'),
        PrimaryKeyConstraint('id', name='source_chunks_pkey'),
        UniqueConstraint('book_id', 'chunk_index', name='uq_chunk_position'),
        Index('idx_source_chunks_book', 'book_id'),
        Index('idx_source_chunks_chapter', 'chapter_id'),
        Index('idx_source_chunks_metadata', 'metadata', postgresql_using='gin'),
        Index('idx_source_chunks_position', 'book_id', 'chunk_index'),
        {'comment': 'Text chunks from books. Every concept is traceable back to its '
                'source chunks.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    token_count: Mapped[Optional[int]] = mapped_column(Integer)
    page_start: Mapped[Optional[int]] = mapped_column(Integer)
    page_end: Mapped[Optional[int]] = mapped_column(Integer)
    metadata_: Mapped[Optional[dict]] = mapped_column('metadata', JSONB)
    book_upload_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)

    book: Mapped['Books'] = relationship('Books', back_populates='source_chunks')
    book_upload: Mapped[Optional['BookUploads']] = relationship('BookUploads', back_populates='source_chunks')
    chapter: Mapped[Optional['Chapters']] = relationship('Chapters', back_populates='source_chunks')
    concept_chunks: Mapped[list['ConceptChunks']] = relationship('ConceptChunks', back_populates='chunk')


class AssessmentOutcomes(Base):
    __tablename__ = 'assessment_outcomes'
    __table_args__ = (
        CheckConstraint('mastery_estimate >= 0::numeric AND mastery_estimate <= 1::numeric', name='chk_mastery_estimate'),
        ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE', name='assessment_outcomes_assessment_id_fkey'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='assessment_outcomes_concept_id_fkey'),
        PrimaryKeyConstraint('id', name='assessment_outcomes_pkey'),
        UniqueConstraint('assessment_id', 'concept_id', name='uq_assessment_concept_outcome'),
        Index('idx_assessment_outcomes_assessment', 'assessment_id'),
        Index('idx_assessment_outcomes_concept', 'concept_id'),
        {'comment': 'Per-concept placement result seeding mastery and node_state.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    mastery_estimate: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    placement_state: Mapped[PlacementState] = mapped_column(Enum(PlacementState, values_callable=lambda cls: [member.value for member in cls], name='placement_state'), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    assessment: Mapped['Assessments'] = relationship('Assessments', back_populates='assessment_outcomes')
    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='assessment_outcomes')


class ConceptChunks(Base):
    __tablename__ = 'concept_chunks'
    __table_args__ = (
        CheckConstraint('relevance_score IS NULL OR relevance_score >= 0::numeric AND relevance_score <= 1::numeric', name='chk_relevance_score'),
        ForeignKeyConstraint(['chunk_id'], ['source_chunks.id'], ondelete='CASCADE', name='concept_chunks_chunk_id_fkey'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='concept_chunks_concept_id_fkey'),
        PrimaryKeyConstraint('id', name='concept_chunks_pkey'),
        UniqueConstraint('concept_id', 'chunk_id', name='uq_concept_chunk'),
        Index('idx_concept_chunks_chunk', 'chunk_id'),
        Index('idx_concept_chunks_concept', 'concept_id'),
        {'comment': 'Many-to-many: concept Γåö source chunks used to ground it.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    relevance_score: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))

    chunk: Mapped['SourceChunks'] = relationship('SourceChunks', back_populates='concept_chunks')
    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='concept_chunks')


class ConceptEdges(Base):
    __tablename__ = 'concept_edges'
    __table_args__ = (
        CheckConstraint('confidence >= 0::numeric AND confidence <= 1::numeric', name='chk_confidence'),
        CheckConstraint('from_concept_id <> to_concept_id', name='chk_no_self_loop'),
        CheckConstraint('graph_version > 0', name='chk_graph_version_edge'),
        CheckConstraint('weight >= 0::numeric', name='chk_weight'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='concept_edges_book_id_fkey'),
        ForeignKeyConstraint(['from_concept_id'], ['concepts.id'], ondelete='CASCADE', name='concept_edges_from_concept_id_fkey'),
        ForeignKeyConstraint(['to_concept_id'], ['concepts.id'], ondelete='CASCADE', name='concept_edges_to_concept_id_fkey'),
        PrimaryKeyConstraint('id', name='concept_edges_pkey'),
        UniqueConstraint('book_id', 'graph_version', 'from_concept_id', 'to_concept_id', 'edge_type', name='uq_concept_edge'),
        Index('idx_concept_edges_book', 'book_id', 'graph_version'),
        Index('idx_concept_edges_from', 'from_concept_id'),
        Index('idx_concept_edges_to', 'to_concept_id'),
        Index('idx_concept_edges_type', 'edge_type'),
        Index('idx_concept_edges_unverified', 'book_id', postgresql_where='(is_verified = false)'),
        {'comment': 'KG edges ΓÇö prerequisite/related links between concepts forming a '
                'DAG. DAG invariant enforced at pipeline layer.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('1'))
    from_concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    to_concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    edge_type: Mapped[EdgeType] = mapped_column(Enum(EdgeType, values_callable=lambda cls: [member.value for member in cls], name='edge_type'), nullable=False, server_default=text("'PREREQUISITE'::edge_type"))
    confidence: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default=text('0.5'))
    weight: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default=text('1.0'))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    book: Mapped['Books'] = relationship('Books', back_populates='concept_edges')
    from_concept: Mapped['Concepts'] = relationship('Concepts', foreign_keys=[from_concept_id], back_populates='concept_edges_from_concept')
    to_concept: Mapped['Concepts'] = relationship('Concepts', foreign_keys=[to_concept_id], back_populates='concept_edges_to_concept')


class ConceptFsrs(Base):
    __tablename__ = 'concept_fsrs'
    __table_args__ = (
        CheckConstraint('difficulty >= 1::double precision AND difficulty <= 10::double precision', name='chk_difficulty'),
        CheckConstraint('lapses >= 0', name='chk_lapses'),
        CheckConstraint('repetitions >= 0', name='chk_repetitions'),
        CheckConstraint('retrievability >= 0::double precision AND retrievability <= 1::double precision', name='chk_retrievability'),
        CheckConstraint('stability >= 0::double precision', name='chk_stability'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='concept_fsrs_concept_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='concept_fsrs_user_id_fkey'),
        PrimaryKeyConstraint('id', name='concept_fsrs_pkey'),
        UniqueConstraint('user_id', 'concept_id', name='uq_user_concept_fsrs'),
        Index('idx_concept_fsrs_concept', 'concept_id'),
        Index('idx_concept_fsrs_due_user', 'user_id', 'next_due'),
        Index('idx_concept_fsrs_user', 'user_id'),
        Index('idx_due_reviews', 'user_id', 'next_due', postgresql_where='(next_due IS NOT NULL)'),
        {'comment': 'FSRS-5 scheduling state per (user, concept). Initialized on first '
                'lesson completion.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    stability: Mapped[float] = mapped_column(Double(53), nullable=False, server_default=text('0.4'))
    difficulty: Mapped[float] = mapped_column(Double(53), nullable=False, server_default=text('5.0'))
    retrievability: Mapped[float] = mapped_column(Double(53), nullable=False, server_default=text('1.0'))
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    next_due: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='concept_fsrs')
    user: Mapped['Users'] = relationship('Users', back_populates='concept_fsrs')


class ConceptMastery(Base):
    __tablename__ = 'concept_mastery'
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

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    mastery_score: Mapped[decimal.Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default=text('0'))
    mastery_state: Mapped[MasteryState] = mapped_column(Enum(MasteryState, values_callable=lambda cls: [member.value for member in cls], name='mastery_state'), nullable=False, server_default=text("'UNKNOWN'::mastery_state"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    first_mastered_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    last_reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    updated_by_source: Mapped[Optional[ReviewSource]] = mapped_column(Enum(ReviewSource, values_callable=lambda cls: [member.value for member in cls], name='review_source'))

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='concept_mastery')
    user: Mapped['Users'] = relationship('Users', back_populates='concept_mastery')


class FsrsReviews(Base):
    __tablename__ = 'fsrs_reviews'
    __table_args__ = (
        CheckConstraint('review_grade >= 1 AND review_grade <= 4', name='chk_review_grade'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='fsrs_reviews_concept_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fsrs_reviews_user_id_fkey'),
        PrimaryKeyConstraint('id', name='fsrs_reviews_pkey'),
        Index('idx_fsrs_reviews_concept', 'concept_id'),
        Index('idx_fsrs_reviews_reviewed_at', 'reviewed_at'),
        Index('idx_fsrs_reviews_user', 'user_id'),
        Index('idx_fsrs_reviews_user_concept', 'user_id', 'concept_id'),
        {'comment': 'Immutable FSRS review event log with before/after state delta.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    review_source: Mapped[ReviewSource] = mapped_column(Enum(ReviewSource, values_callable=lambda cls: [member.value for member in cls], name='review_source'), nullable=False)
    review_grade: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    stability_before: Mapped[Optional[float]] = mapped_column(Double(53))
    stability_after: Mapped[Optional[float]] = mapped_column(Double(53))
    difficulty_before: Mapped[Optional[float]] = mapped_column(Double(53))
    difficulty_after: Mapped[Optional[float]] = mapped_column(Double(53))
    retrievability_before: Mapped[Optional[float]] = mapped_column(Double(53))
    retrievability_after: Mapped[Optional[float]] = mapped_column(Double(53))

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='fsrs_reviews')
    user: Mapped['Users'] = relationship('Users', back_populates='fsrs_reviews')


class GeneratedQuestions(Base):
    __tablename__ = 'generated_questions'
    __table_args__ = (
        CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5', name='chk_question_difficulty'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='generated_questions_concept_id_fkey'),
        PrimaryKeyConstraint('id', name='generated_questions_pkey'),
        Index('idx_generated_questions_answer_key', 'answer_key', postgresql_using='gin'),
        Index('idx_generated_questions_concept', 'concept_id'),
        Index('idx_generated_questions_concept_source', 'concept_id', 'question_source'),
        Index('idx_generated_questions_difficulty', 'difficulty_level'),
        Index('idx_generated_questions_source', 'question_source'),
        Index('idx_generated_questions_type', 'question_type'),
        {'comment': 'Questions per concept. source=USER_ASKED|ASSESSMENT_MISS powers '
                'targeted revision.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, values_callable=lambda cls: [member.value for member in cls], name='question_type'), nullable=False)
    question_source: Mapped[QuestionSource] = mapped_column(Enum(QuestionSource, values_callable=lambda cls: [member.value for member in cls], name='question_source'), nullable=False, server_default=text("'GENERATED'::question_source"))
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_key: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    generation_model: Mapped[Optional[str]] = mapped_column(String(100))
    generation_version: Mapped[Optional[str]] = mapped_column(String(50))

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='generated_questions')
    assessment_responses: Mapped[list['AssessmentResponses']] = relationship('AssessmentResponses', back_populates='question')
    tutor_interactions: Mapped[list['TutorInteractions']] = relationship('TutorInteractions', back_populates='question')


class GraphVersions(Base):
    __tablename__ = 'graph_versions'
    __table_args__ = (
        CheckConstraint('edge_count >= 0', name='chk_gv_edge_count'),
        CheckConstraint('node_count >= 0', name='chk_gv_node_count'),
        CheckConstraint('version > 0', name='chk_gv_version'),
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='graph_versions_book_id_fkey'),
        ForeignKeyConstraint(['build_job_id'], ['graph_build_jobs.id'], ondelete='RESTRICT', name='graph_versions_build_job_id_fkey'),
        PrimaryKeyConstraint('id', name='graph_versions_pkey'),
        UniqueConstraint('book_id', 'version', name='uq_graph_version_per_book'),
        Index('idx_graph_versions_book', 'book_id'),
        Index('idx_graph_versions_current', 'book_id', postgresql_where='(is_current = true)'),
        Index('uq_current_graph_version_per_book', 'book_id', postgresql_where='(is_current = true)', unique=True),
        {'comment': 'Named snapshot of each completed graph build per book. Single '
                'source for version lookups.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    build_job_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    label: Mapped[Optional[str]] = mapped_column(Text)

    book: Mapped['Books'] = relationship('Books', back_populates='graph_versions')
    build_job: Mapped['GraphBuildJobs'] = relationship('GraphBuildJobs', back_populates='graph_versions')
    evaluated_pairs: Mapped[list['EvaluatedPairs']] = relationship('EvaluatedPairs', back_populates='graph_version')
    graph_repair_log: Mapped[list['GraphRepairLog']] = relationship('GraphRepairLog', back_populates='graph_version')
    graph_validation_results: Mapped[list['GraphValidationResults']] = relationship('GraphValidationResults', back_populates='graph_version')
    raw_concepts: Mapped[list['RawConcepts']] = relationship('RawConcepts', back_populates='graph_version')
    relationship_candidates: Mapped[list['RelationshipCandidates']] = relationship('RelationshipCandidates', back_populates='graph_version')
    user_books: Mapped[list['UserBooks']] = relationship('UserBooks', back_populates='pinned_graph_version')


class LessonSessions(Base):
    __tablename__ = 'lesson_sessions'
    __table_args__ = (
        CheckConstraint('completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at', name='chk_lesson_time'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='lesson_sessions_concept_id_fkey'),
        ForeignKeyConstraint(['curriculum_plan_id'], ['curriculum_plans.id'], ondelete='SET NULL', name='lesson_sessions_curriculum_plan_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='lesson_sessions_user_id_fkey'),
        PrimaryKeyConstraint('id', name='lesson_sessions_pkey'),
        Index('idx_active_lesson_sessions', 'user_id', postgresql_where="(status = 'IN_PROGRESS'::lesson_status)"),
        Index('idx_lesson_sessions_concept', 'concept_id'),
        Index('idx_lesson_sessions_content', 'generated_content', postgresql_using='gin'),
        Index('idx_lesson_sessions_status', 'status'),
        Index('idx_lesson_sessions_user', 'user_id'),
        {'comment': 'One session = Socratic teaching of one concept.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[LessonStatus] = mapped_column(Enum(LessonStatus, values_callable=lambda cls: [member.value for member in cls], name='lesson_status'), nullable=False, server_default=text("'NOT_STARTED'::lesson_status"))
    generated_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    curriculum_plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    generation_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='lesson_sessions')
    curriculum_plan: Mapped[Optional['CurriculumPlans']] = relationship('CurriculumPlans', back_populates='lesson_sessions')
    user: Mapped['Users'] = relationship('Users', back_populates='lesson_sessions')
    tutor_interactions: Mapped[list['TutorInteractions']] = relationship('TutorInteractions', back_populates='lesson_session')


class MasteryEvents(Base):
    __tablename__ = 'mastery_events'
    __table_args__ = (
        CheckConstraint('new_mastery IS NULL OR new_mastery >= 0::numeric AND new_mastery <= 1::numeric', name='chk_new_mastery'),
        CheckConstraint('previous_mastery IS NULL OR previous_mastery >= 0::numeric AND previous_mastery <= 1::numeric', name='chk_prev_mastery'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='mastery_events_concept_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='mastery_events_user_id_fkey'),
        PrimaryKeyConstraint('id', name='mastery_events_pkey'),
        Index('idx_mastery_events_concept', 'concept_id'),
        Index('idx_mastery_events_created', 'created_at'),
        Index('idx_mastery_events_user', 'user_id'),
        {'comment': 'Audit trail for every mastery_score change. Useful for '
                'visualization and debugging.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source: Mapped[ReviewSource] = mapped_column(Enum(ReviewSource, values_callable=lambda cls: [member.value for member in cls], name='review_source'), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    previous_mastery: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))
    new_mastery: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))
    reason: Mapped[Optional[str]] = mapped_column(Text)

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='mastery_events')
    user: Mapped['Users'] = relationship('Users', back_populates='mastery_events')


class UserConceptState(Base):
    __tablename__ = 'user_concept_state'
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

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[NodeState] = mapped_column(Enum(NodeState, values_callable=lambda cls: [member.value for member in cls], name='node_state'), nullable=False, server_default=text("'LOCKED'::node_state"))
    state_updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='user_concept_state')
    user: Mapped['Users'] = relationship('Users', back_populates='user_concept_state')


class AssessmentResponses(Base):
    __tablename__ = 'assessment_responses'
    __table_args__ = (
        CheckConstraint('confidence_level IS NULL OR confidence_level >= 1 AND confidence_level <= 5', name='chk_confidence_response'),
        CheckConstraint('response_time_seconds IS NULL OR response_time_seconds >= 0', name='chk_response_time'),
        ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE', name='assessment_responses_assessment_id_fkey'),
        ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE', name='assessment_responses_concept_id_fkey'),
        ForeignKeyConstraint(['question_id'], ['generated_questions.id'], ondelete='CASCADE', name='assessment_responses_question_id_fkey'),
        PrimaryKeyConstraint('id', name='assessment_responses_pkey'),
        Index('idx_assessment_responses_assessment', 'assessment_id'),
        Index('idx_assessment_responses_concept', 'concept_id'),
        Index('idx_assessment_responses_miss', 'concept_id', postgresql_where='(is_correct = false)'),
        Index('idx_assessment_responses_question', 'question_id'),
        Index('idx_assessment_responses_response', 'response', postgresql_using='gin'),
        {'comment': 'Per-question responses. confidence_level before reveal = '
                'calibration signal.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    confidence_level: Mapped[Optional[int]] = mapped_column(Integer)
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    assessment: Mapped['Assessments'] = relationship('Assessments', back_populates='assessment_responses')
    concept: Mapped['Concepts'] = relationship('Concepts', back_populates='assessment_responses')
    question: Mapped['GeneratedQuestions'] = relationship('GeneratedQuestions', back_populates='assessment_responses')


class EvaluatedPairs(Base):
    __tablename__ = 'evaluated_pairs'
    __table_args__ = (
        ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='evaluated_pairs_graph_version_id_fkey'),
        ForeignKeyConstraint(['source_concept_id'], ['concepts.id'], ondelete='CASCADE', name='evaluated_pairs_source_concept_id_fkey'),
        ForeignKeyConstraint(['target_concept_id'], ['concepts.id'], ondelete='CASCADE', name='evaluated_pairs_target_concept_id_fkey'),
        PrimaryKeyConstraint('id', name='evaluated_pairs_pkey'),
        UniqueConstraint('graph_version_id', 'source_concept_id', 'target_concept_id', name='uq_evaluated_pairs_version_src_tgt'),
        Index('ix_evaluated_pairs_version', 'graph_version_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    graph_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    confidence: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))
    llm_version: Mapped[Optional[str]] = mapped_column(String(50))

    graph_version: Mapped['GraphVersions'] = relationship('GraphVersions', back_populates='evaluated_pairs')
    source_concept: Mapped['Concepts'] = relationship('Concepts', foreign_keys=[source_concept_id], back_populates='evaluated_pairs_source_concept')
    target_concept: Mapped['Concepts'] = relationship('Concepts', foreign_keys=[target_concept_id], back_populates='evaluated_pairs_target_concept')


class GraphRepairLog(Base):
    __tablename__ = 'graph_repair_log'
    __table_args__ = (
        ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='graph_repair_log_graph_version_id_fkey'),
        PrimaryKeyConstraint('id', name='graph_repair_log_pkey')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    graph_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    before_value: Mapped[Optional[dict]] = mapped_column(JSONB)

    graph_version: Mapped[Optional['GraphVersions']] = relationship('GraphVersions', back_populates='graph_repair_log')


class GraphValidationResults(Base):
    __tablename__ = 'graph_validation_results'
    __table_args__ = (
        ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='graph_validation_results_graph_version_id_fkey'),
        PrimaryKeyConstraint('id', name='graph_validation_results_pkey')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    rule_code: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    graph_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    detail: Mapped[Optional[dict]] = mapped_column(JSONB)

    graph_version: Mapped[Optional['GraphVersions']] = relationship('GraphVersions', back_populates='graph_validation_results')


class RawConcepts(Base):
    __tablename__ = 'raw_concepts'
    __table_args__ = (
        ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='raw_concepts_graph_version_id_fkey'),
        PrimaryKeyConstraint('id', name='raw_concepts_pkey'),
        Index('ix_raw_concepts_chunk', 'source_chunk_id'),
        Index('ix_raw_concepts_version', 'graph_version_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    graph_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty_level: Mapped[int] = mapped_column(Integer, nullable=False)
    subtopics: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))

    graph_version: Mapped['GraphVersions'] = relationship('GraphVersions', back_populates='raw_concepts')


class RelationshipCandidates(Base):
    __tablename__ = 'relationship_candidates'
    __table_args__ = (
        ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='relationship_candidates_graph_version_id_fkey'),
        ForeignKeyConstraint(['source_concept_id'], ['concepts.id'], ondelete='CASCADE', name='relationship_candidates_source_concept_id_fkey'),
        ForeignKeyConstraint(['target_concept_id'], ['concepts.id'], ondelete='CASCADE', name='relationship_candidates_target_concept_id_fkey'),
        PrimaryKeyConstraint('id', name='relationship_candidates_pkey'),
        Index('ix_rel_candidates_version_status', 'graph_version_id', 'status')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    graph_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_concept_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'PENDING'::character varying"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    confidence: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 4))
    processed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    graph_version: Mapped['GraphVersions'] = relationship('GraphVersions', back_populates='relationship_candidates')
    source_concept: Mapped['Concepts'] = relationship('Concepts', foreign_keys=[source_concept_id], back_populates='relationship_candidates_source_concept')
    target_concept: Mapped['Concepts'] = relationship('Concepts', foreign_keys=[target_concept_id], back_populates='relationship_candidates_target_concept')


class TutorInteractions(Base):
    __tablename__ = 'tutor_interactions'
    __table_args__ = (
        CheckConstraint('hint_level >= 0 AND hint_level <= 4', name='chk_hint_level'),
        CheckConstraint('latency_ms IS NULL OR latency_ms >= 0', name='chk_latency'),
        CheckConstraint('token_input_count IS NULL OR token_input_count >= 0', name='chk_input_tokens'),
        CheckConstraint('token_output_count IS NULL OR token_output_count >= 0', name='chk_output_tokens'),
        CheckConstraint('turn_index >= 0', name='chk_turn_index'),
        ForeignKeyConstraint(['lesson_session_id'], ['lesson_sessions.id'], ondelete='CASCADE', name='tutor_interactions_lesson_session_id_fkey'),
        ForeignKeyConstraint(['question_id'], ['generated_questions.id'], ondelete='SET NULL', name='tutor_interactions_question_id_fkey'),
        PrimaryKeyConstraint('id', name='tutor_interactions_pkey'),
        UniqueConstraint('lesson_session_id', 'turn_index', name='uq_session_turn'),
        Index('idx_tutor_interactions_created', 'created_at'),
        Index('idx_tutor_interactions_question', 'question_id', postgresql_where='(question_id IS NOT NULL)'),
        Index('idx_tutor_interactions_session', 'lesson_session_id'),
        {'comment': 'Immutable turn-by-turn Socratic conversation log with turn_index '
                'ordering.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    lesson_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_message: Mapped[str] = mapped_column(Text, nullable=False)
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    question_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    model_name: Mapped[Optional[str]] = mapped_column(String(100))
    token_input_count: Mapped[Optional[int]] = mapped_column(Integer)
    token_output_count: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)

    lesson_session: Mapped['LessonSessions'] = relationship('LessonSessions', back_populates='tutor_interactions')
    question: Mapped[Optional['GeneratedQuestions']] = relationship('GeneratedQuestions', back_populates='tutor_interactions')


class UserBooks(Base):
    __tablename__ = 'user_books'
    __table_args__ = (
        ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='user_books_book_id_fkey'),
        ForeignKeyConstraint(['current_chapter_id'], ['chapters.id'], ondelete='SET NULL', name='user_books_current_chapter_id_fkey'),
        ForeignKeyConstraint(['pinned_graph_version_id'], ['graph_versions.id'], ondelete='RESTRICT', name='user_books_pinned_graph_version_id_fkey'),
        ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='user_books_user_id_fkey'),
        PrimaryKeyConstraint('id', name='user_books_pkey'),
        UniqueConstraint('user_id', 'book_id', name='uq_user_book'),
        Index('idx_user_books_book', 'book_id'),
        Index('idx_user_books_user', 'user_id'),
        Index('idx_user_books_version', 'pinned_graph_version_id'),
        {'comment': 'User enrollment in a book. Pins graph version at enrollment time.'}
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    book_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    pinned_graph_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    current_chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    last_activity_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    book: Mapped['Books'] = relationship('Books', back_populates='user_books')
    current_chapter: Mapped[Optional['Chapters']] = relationship('Chapters', back_populates='user_books')
    pinned_graph_version: Mapped[Optional['GraphVersions']] = relationship('GraphVersions', back_populates='user_books')
    user: Mapped['Users'] = relationship('Users', back_populates='user_books')
