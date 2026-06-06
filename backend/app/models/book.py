import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from app.models.base import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id")) # We'll assume the FK is to users.id
    title = Column(Text, nullable=False)
    author = Column(Text)
    description = Column(Text)
    visibility = Column(ENUM('PRIVATE', 'PUBLIC', name='book_visibility', create_type=False), nullable=False, default='PRIVATE')
    source_type = Column(String(50), nullable=False)
    file_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    build_jobs = relationship("GraphBuildJob", back_populates="book", cascade="all, delete-orphan")
    graph_versions = relationship("GraphVersion", back_populates="book", cascade="all, delete-orphan")

class GraphBuildJob(Base):
    __tablename__ = "graph_build_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    graph_version = Column(Integer, nullable=False)
    status = Column(ENUM('QUEUED', 'PARSING', 'EXTRACTING_CONCEPTS', 'BUILDING_GRAPH', 'VALIDATING', 'COMPLETED', 'FAILED', name='graph_build_status', create_type=False), nullable=False, default='QUEUED')
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    nodes_created = Column(Integer)
    edges_created = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    book = relationship("Book", back_populates="build_jobs")
    versions_produced = relationship("GraphVersion", back_populates="build_job")

class GraphVersion(Base):
    __tablename__ = "graph_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    build_job_id = Column(UUID(as_uuid=True), ForeignKey("graph_build_jobs.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    book = relationship("Book", back_populates="graph_versions")
    build_job = relationship("GraphBuildJob", back_populates="versions_produced")

class UserBook(Base):
    __tablename__ = "user_books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    pinned_graph_version_id = Column(UUID(as_uuid=True), ForeignKey("graph_versions.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
