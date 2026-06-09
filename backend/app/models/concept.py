from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint, Index, CheckConstraint, ForeignKeyConstraint
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB, TSVECTOR
from app.models.base import Base


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (
    
            CheckConstraint('difficulty_level >= 1 AND difficulty_level <= 5', name='chk_concept_difficulty'),
    
            CheckConstraint('estimated_minutes IS NULL OR estimated_minutes > 0', name='chk_concept_minutes'),
    
            CheckConstraint('graph_version > 0', name='chk_concept_graph_version'),
    
            ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE', name='concepts_book_id_fkey'),
    
            ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='SET NULL', name='concepts_chapter_id_fkey'),
    
            PrimaryKeyConstraint('id', name='concepts_pkey'),
    
            UniqueConstraint('book_id', 'name', 'graph_version', name='uq_concept_book_name_version'),
    
            Index('idx_concepts_book', 'book_id'),    
            Index('idx_concepts_chapter', 'chapter_id'),
    
            Index('idx_concepts_difficulty', 'difficulty_level'),
    
            Index('idx_concepts_graph_version', 'book_id', 'graph_version'),
    
            Index('idx_concepts_metadata', 'metadata', postgresql_using='gin'),
    
            Index('idx_concepts_name', 'name'),
    
            Index('idx_concepts_search', 'search_vector', postgresql_using='gin'),
    
            {'comment': 'KG nodes ΓÇö canonical concepts extracted from books per graph '
    
                    'version.'}
    
        )


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), nullable=True)

    name = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    learning_objective = Column(Text, nullable=True)
    difficulty_level = Column(Integer, nullable=False)
    estimated_minutes = Column(Integer, nullable=True)
    graph_version = Column(Integer, nullable=False, default=1)
    metadata_ = Column("metadata", JSONB, nullable=True)
    search_vector = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ConceptEdge(Base):
    __tablename__ = "concept_edges"
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


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    graph_version = Column(Integer, nullable=False, default=1)
    from_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    to_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    edge_type = Column(ENUM('PREREQUISITE', 'RELATED', name='edge_type', create_type=False), nullable=False, default='PREREQUISITE')
    confidence = Column(Numeric(5, 4), nullable=False, default=0.5)
    weight = Column(Numeric(5, 4), nullable=False, default=1.0)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RawConcept(Base):
    __tablename__ = "raw_concepts"
    __table_args__ = (
    
            ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='raw_concepts_graph_version_id_fkey'),
    
            PrimaryKeyConstraint('id', name='raw_concepts_pkey'),
    
            Index('ix_raw_concepts_chunk', 'source_chunk_id'),
    
            Index('ix_raw_concepts_version', 'graph_version_id')
    
        )


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    graph_version_id = Column(UUID(as_uuid=True), ForeignKey("graph_versions.id", ondelete="CASCADE"), nullable=False)
    source_chunk_id = Column(UUID(as_uuid=True), nullable=False) # Not FK to avoid NoReferencedTableError since SourceChunk model is missing
    name = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    subtopics = Column(JSONB, nullable=False, default=list)
    canonical_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True)
    canonicalized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RelationshipCandidate(Base):
    __tablename__ = "relationship_candidates"
    __table_args__ = (
    
            ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='relationship_candidates_graph_version_id_fkey'),
    
            ForeignKeyConstraint(['source_concept_id'], ['concepts.id'], ondelete='CASCADE', name='relationship_candidates_source_concept_id_fkey'),
    
            ForeignKeyConstraint(['target_concept_id'], ['concepts.id'], ondelete='CASCADE', name='relationship_candidates_target_concept_id_fkey'),
    
            PrimaryKeyConstraint('id', name='relationship_candidates_pkey'),
    
            Index('ix_rel_candidates_version_status', 'graph_version_id', 'status')
    
        )


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    graph_version_id = Column(UUID(as_uuid=True), ForeignKey("graph_versions.id", ondelete="CASCADE"), nullable=False)
    source_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    target_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    confidence = Column(Numeric(5, 4), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvaluatedPair(Base):
    __tablename__ = "evaluated_pairs"
    __table_args__ = (
    
            ForeignKeyConstraint(['graph_version_id'], ['graph_versions.id'], ondelete='CASCADE', name='evaluated_pairs_graph_version_id_fkey'),
    
            ForeignKeyConstraint(['source_concept_id'], ['concepts.id'], ondelete='CASCADE', name='evaluated_pairs_source_concept_id_fkey'),
    
            ForeignKeyConstraint(['target_concept_id'], ['concepts.id'], ondelete='CASCADE', name='evaluated_pairs_target_concept_id_fkey'),
    
            PrimaryKeyConstraint('id', name='evaluated_pairs_pkey'),
    
            UniqueConstraint('graph_version_id', 'source_concept_id', 'target_concept_id', name='uq_evaluated_pairs_version_src_tgt'),
    
            Index('ix_evaluated_pairs_version', 'graph_version_id')
    
        )


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    graph_version_id = Column(UUID(as_uuid=True), ForeignKey("graph_versions.id", ondelete="CASCADE"), nullable=False)
    source_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    target_concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=True)
    llm_version = Column(String(50), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SourceChunk(Base):
    __tablename__ = "source_chunks"
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


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    page_start = Column(Integer)
    page_end = Column(Integer)
    metadata_ = Column("metadata", JSONB)
    book_upload_id = Column(UUID(as_uuid=True), ForeignKey("book_uploads.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConceptChunk(Base):
    __tablename__ = "concept_chunks"
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


    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("source_chunks.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Numeric(5, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
