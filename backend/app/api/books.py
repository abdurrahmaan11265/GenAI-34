from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user_id
from app.repositories.book_repo import BookRepository
from app.services.book_service import BookService, mock_process_book_job
from app.schemas.book import UploadResponse, JobStatusDTO, BookDTO
from app.core.db import AsyncSessionLocal

router = APIRouter(prefix="/books", tags=["Books"])

def get_book_service(session: AsyncSession = Depends(get_db)) -> BookService:
    return BookService(BookRepository(session))

@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_book(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    author: str = Form(None),
    description: str = Form(None),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db)
):
    # Ensure PDF
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    response = await service.upload_book(user_id, title, author or "", description or "", file)
    await session.commit()
    
    # We must spawn a background task with a fresh DB session because the request session will close.
    async def run_job():
        async with AsyncSessionLocal() as bg_session:
            await mock_process_book_job(response.job.job_id, response.book.id, user_id, bg_session)

    background_tasks.add_task(run_job)
    return response

@router.get("/{job_id}/status", response_model=JobStatusDTO)
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service)
):
    status = await service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@router.get("", response_model=List[BookDTO])
async def get_user_books(
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db)
):
    books = await service.book_repo.get_books_by_user(user_id)
    return [
        BookDTO(
            id=str(b.id),
            title=b.title,
            author=b.author,
            description=b.description,
            source_type=b.source_type,
            file_url=b.file_url,
            created_at=b.created_at
        )
        for b in books
    ]
