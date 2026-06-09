import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import UploadFile
from app.models.book import Book, GraphBuildJob, GraphVersion, UserBook
from app.repositories.book_repo import BookRepository
from app.schemas.book import BookDTO, JobStatusDTO, UploadResponse, BookStatusDTO

class BookService:
    def __init__(self, book_repo: BookRepository):
        self.book_repo = book_repo

    async def create_book(self, user_id: str, title: str, author: str, description: str, is_public: bool) -> BookDTO:
        book = Book(
            owner_id=user_id,
            title=title,
            author=author,
            description=description,
            visibility="PUBLIC" if is_public else "PRIVATE",
            source_type="PDF", # Defaulting until file is uploaded
            file_url=None
        )
        book = await self.book_repo.create_book(book)
        
        user_book = UserBook(user_id=user_id, book_id=book.id)
        await self.book_repo.create_user_book(user_book)
        
        return BookDTO(
            id=str(book.id),
            title=book.title,
            author=book.author,
            description=book.description,
            source_type=book.source_type,
            file_url=book.file_url,
            created_at=book.created_at or datetime.now(timezone.utc)
        )

    async def upload_book_file(self, book_id: str, user_id: str, file: UploadFile) -> JobStatusDTO:
        from app.services.storage import get_storage_provider
        from sqlalchemy import text
        import uuid

        storage_provider = get_storage_provider()
        
        # 1. Save the file locally
        storage_path = await storage_provider.save(file, user_id)
        
        # Calculate file size since we aren't reading it into memory here
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        # 2. Insert into book_uploads
        upload_id = str(uuid.uuid4())
        await self.book_repo.session.execute(text('''
            INSERT INTO book_uploads (id, book_id, user_id, original_filename, storage_path, file_size_bytes, mime_type, upload_status)
            VALUES (:id, :bid, :uid, :fname, :path, :size, :mime, 'PENDING')
        '''), {
            "id": upload_id, "bid": book_id, "uid": user_id,
            "fname": file.filename, "path": storage_path,
            "size": file_size, "mime": file.content_type
        })
        
        # 3. Insert into graph_build_jobs
        job_id = str(uuid.uuid4())
        await self.book_repo.session.execute(text('''
            INSERT INTO graph_build_jobs (id, book_id, graph_version, status, book_upload_id)
            VALUES (:id, :bid, 1, 'QUEUED', :upload_id)
        '''), {
            "id": job_id, "bid": book_id, "upload_id": upload_id
        })
        
        return JobStatusDTO(
            job_id=job_id,
            status="QUEUED",
            nodes_created=None,
            edges_created=None,
            error_message=None
        )

    async def get_book_processing_status(self, book_id: str) -> 'BookStatusDTO | None':
        from app.schemas.book import BookStatusDTO
        job = await self.book_repo.get_latest_job_for_book(book_id)
        if not job:
            return None
            
        step_index = 0
        current_step = "Parsing & chunking"
        status = "parsing"
        
        if job.status == "QUEUED" or job.status == "PARSING":
            step_index = 0
            current_step = "Parsing & chunking"
            status = "parsing"
        elif job.status == "EXTRACTING_CONCEPTS":
            step_index = 1
            current_step = "Extracting concepts"
            status = "parsing"
        elif job.status == "BUILDING_GRAPH":
            step_index = 2
            current_step = "Inferring prerequisites"
            status = "parsing"
        elif job.status == "VALIDATING":
            step_index = 3
            current_step = "Ready for review"
            status = "kg_built"
        elif job.status == "COMPLETED":
            step_index = 4
            current_step = "Ready for review"
            status = "ready"
        elif job.status == "FAILED":
            status = "uploaded"
            
        return BookStatusDTO(
            status=status,
            current_step=current_step,
            step_index=step_index,
            total_steps=4,
            estimated_seconds_remaining=30 if status == "parsing" else None,
            error=job.error_message
        )

    async def get_book_graph(self, book_id: str):
        from sqlalchemy import text
        from app.schemas.book import GraphDTO, KGNodeDTO, KGEdgeDTO, DIFFICULTY_MAPPING
        
        concept_rows = await self.book_repo.session.execute(text('''
            SELECT id, name as title, summary, difficulty_level, created_at
            FROM concepts
            WHERE book_id = :bid
        '''), {"bid": book_id})
        
        nodes = []
        for r in concept_rows:
            diff_str = DIFFICULTY_MAPPING.get(r.difficulty_level, "beginner")
            nodes.append(KGNodeDTO(
                id=str(r.id),
                bookId=book_id,
                title=r.title,
                summary=r.summary,
                sourceChunks=[],
                difficultyTier=diff_str,
                orderIndex=0,
                sectionName=None,
                createdAt=r.created_at.isoformat()
            ))
            
        edge_rows = await self.book_repo.session.execute(text('''
            SELECT id, from_concept_id, to_concept_id, edge_type, weight, confidence
            FROM concept_edges
            WHERE book_id = :bid
        '''), {"bid": book_id})
        
        edges = []
        for r in edge_rows:
            edges.append(KGEdgeDTO(
                id=str(r.id),
                fromNodeId=str(r.from_concept_id),
                toNodeId=str(r.to_concept_id),
                type=r.edge_type,
                weight=float(r.weight),
                confidence=float(r.confidence)
            ))
            
        return GraphDTO(nodes=nodes, edges=edges)

async def mock_process_book_job(job_id: str, book_id: str, user_id: str, session):
    """
    Simulates the AI processing pipeline.
    Because SQLAlchemy sessions shouldn't easily cross thread boundaries if not careful,
    we do this in the same async loop with a fresh or existing session.
    """
    repo = BookRepository(session)
    job = await repo.get_job_by_id(job_id)
    if not job: return

    job.status = "PARSING"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()
    
    # Simulate work
    await asyncio.sleep(5)
    
    # Finish work
    job.status = "COMPLETED"
    job.completed_at = datetime.now(timezone.utc)
    job.nodes_created = 42
    job.edges_created = 84
    
    # Create the graph version
    version = GraphVersion(
        book_id=book_id,
        version=job.graph_version,
        build_job_id=job.id
    )
    version = await repo.create_version(version)
    
    # Tie to user
    user_book = UserBook(
        user_id=user_id,
        book_id=book_id,
        pinned_graph_version_id=version.id
    )
    await repo.create_user_book(user_book)
    
    await session.commit()
