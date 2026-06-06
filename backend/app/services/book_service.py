import asyncio
from datetime import datetime, timezone
from fastapi import UploadFile
from app.models.book import Book, GraphBuildJob, GraphVersion, UserBook
from app.repositories.book_repo import BookRepository
from app.schemas.book import BookDTO, JobStatusDTO, UploadResponse

class BookService:
    def __init__(self, book_repo: BookRepository):
        self.book_repo = book_repo

    async def upload_book(self, user_id: str, title: str, author: str, description: str, file: UploadFile) -> UploadResponse:
        # 1. Fake saving the file
        file_url = f"s3://lexis-books/mock/{file.filename}"
        
        # 2. Create the book
        book = Book(
            owner_id=user_id,
            title=title,
            author=author,
            description=description,
            source_type="PDF",
            file_url=file_url
        )
        book = await self.book_repo.create_book(book)
        
        # 3. Create GraphBuildJob (PENDING/QUEUED)
        job = GraphBuildJob(
            book_id=book.id,
            graph_version=1,
            status="QUEUED"
        )
        job = await self.book_repo.create_job(job)

        # 4. We will trigger the background job in the router.
        # But for now, we return the upload response.
        
        return UploadResponse(
            book=BookDTO(
                id=str(book.id),
                title=book.title,
                author=book.author,
                description=book.description,
                source_type=book.source_type,
                file_url=book.file_url,
                created_at=book.created_at or datetime.now(timezone.utc)
            ),
            job=JobStatusDTO(
                job_id=str(job.id),
                status=job.status,
                nodes_created=None,
                edges_created=None,
                error_message=None
            )
        )

    async def get_job_status(self, job_id: str) -> JobStatusDTO | None:
        job = await self.book_repo.get_job_by_id(job_id)
        if not job:
            return None
        return JobStatusDTO(
            job_id=str(job.id),
            status=job.status,
            nodes_created=job.nodes_created,
            edges_created=job.edges_created,
            error_message=job.error_message
        )

async def mock_process_book_job(job_id: str, book_id: str, user_id: str, session):
    """
    Simulates the AI processing pipeline.
    Because SQLAlchemy sessions shouldn't easily cross thread boundaries if not careful,
    we do this in the same async loop with a fresh or existing session.
    """
    repo = BookRepository(session)
    job = await repo.get_job_by_id(job_id)
    if not job: return

    job.status = "PROCESSING"
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
