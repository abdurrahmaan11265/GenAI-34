import sys

def inject_columns(fpath, class_name, cols_to_add, cols_to_remove=None):
    with open(fpath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_class = False
    out_lines = []
    for line in lines:
        if line.startswith(f'class {class_name}('):
            in_class = True
            
        if in_class and cols_to_remove:
            skip = False
            for c in cols_to_remove:
                if line.strip().startswith(c + ' ='):
                    skip = True
                    break
            if skip: continue
            
        out_lines.append(line)
        
        # We append the new columns right before the relationship or at the end of the class
        if in_class and line.strip().startswith('id ='):
            for c in cols_to_add:
                out_lines.append(f'    {c}\n')
            cols_to_add = [] # prevent duplicate injection
            
    with open(fpath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

# user.py
inject_columns('backend/app/models/user.py', 'ContentCompletion', 
               ['completed_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)',
                'content_version = Column(Integer, nullable=False, default=1)'], 
               ['created_at'])

inject_columns('backend/app/models/user.py', 'DailyActivity', 
               ['tutor_messages_sent = Column(Integer, nullable=False, default=0)',
                'lessons_completed = Column(Integer, nullable=False, default=0)',
                'assessments_completed = Column(Integer, nullable=False, default=0)',
                'concepts_learned = Column(Integer, nullable=False, default=0)',
                'questions_answered = Column(Integer, nullable=False, default=0)',
                'concepts_reviewed = Column(Integer, nullable=False, default=0)'],
               ['updated_at'])

inject_columns('backend/app/models/user.py', 'ProgressSnapshot',
               ['learning_concepts = Column(Integer, nullable=False, default=0)',
                'total_concepts = Column(Integer, nullable=False, default=0)',
                'average_mastery = Column(Numeric(5,4))',
                'overall_progress = Column(Numeric(5,2), nullable=False, default=0)',
                'average_retrievability = Column(Numeric(5,4))',
                'mastered_concepts = Column(Integer, nullable=False, default=0)',
                'weak_concepts = Column(Integer, nullable=False, default=0)'],
               ['concepts_mastered', 'concepts_in_progress', 'total_minutes_studied'])

inject_columns('backend/app/models/user.py', 'LearningStreak', [], ['created_at'])
inject_columns('backend/app/models/user.py', 'BookStreak', [], ['created_at'])

inject_columns('backend/app/models/user.py', 'UserBook',
               ['completed_at = Column(DateTime(timezone=True))',
                'current_chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id"))',
                'last_activity_at = Column(DateTime(timezone=True))',
                'started_at = Column(DateTime(timezone=True))'])

# book.py
inject_columns('backend/app/models/book.py', 'Book',
               ['processing_started_at = Column(DateTime(timezone=True))',
                'processing_completed_at = Column(DateTime(timezone=True))',
                'page_count = Column(Integer)',
                'file_size_bytes = Column(BigInteger)',
                'language = Column(String(10), default="en", nullable=False)'])
                
inject_columns('backend/app/models/book.py', 'GraphBuildJob',
               ['concepts_created = Column(Integer)',
                'chunks_processed = Column(Integer)',
                'metadata_ = Column("metadata", JSONB)',
                'book_upload_id = Column(UUID(as_uuid=True), ForeignKey("book_uploads.id", ondelete="CASCADE"))'])

inject_columns('backend/app/models/book.py', 'SourceChunk',
               ['book_upload_id = Column(UUID(as_uuid=True), ForeignKey("book_uploads.id", ondelete="CASCADE"))'])

inject_columns('backend/app/models/book.py', 'GraphVersion',
               ['updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())'])

# concept.py
inject_columns('backend/app/models/concept.py', 'Concept',
               ['search_vector = Column(TSVECTOR)'])

# For book uploads and graphversions is_current, just do string replace
with open('backend/app/models/book.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('file_size_bytes = Column(Integer)', 'file_size_bytes = Column(BigInteger)')
c = c.replace('is_current = Column(String)', 'is_current = Column(Boolean, default=False)')
with open('backend/app/models/book.py', 'w', encoding='utf-8') as f:
    f.write(c)
