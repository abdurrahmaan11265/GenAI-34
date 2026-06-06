import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, func, Date
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(ENUM('STUDENT', 'TEACHER', 'ADMIN', name='user_role', create_type=False), nullable=False, default='STUDENT')
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    daily_new_node_cap = Column(Integer, nullable=False, default=10)
    daily_reminder_time = Column(String(5), nullable=True)
    session_length_pref = Column(Integer, nullable=False, default=30)
    notify_reminders = Column(Boolean, nullable=False, default=True)
    notify_due_reviews = Column(Boolean, nullable=False, default=True)
    notify_processing = Column(Boolean, nullable=False, default=True)
    global_streak = Column(Integer, nullable=False, default=0)
    last_active_date = Column(Date, nullable=True)
