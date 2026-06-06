from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user_id
from app.repositories.book_repo import BookRepository
from app.services.book_service import BookService, mock_process_book_job
from app.schemas.book import UploadResponse, JobStatusDTO, BookDTO, BookCreate, BookStatusDTO, BookDetailDTO
from app.core.db import AsyncSessionLocal

router = APIRouter(prefix="/books", tags=["Books"])

def get_book_service(session: AsyncSession = Depends(get_db)) -> BookService:
    return BookService(BookRepository(session))

@router.post("", response_model=dict, status_code=201)
async def create_book(
    data: BookCreate,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db)
):
    # This matches the frontend expectation: { book: BookDetailDTO }
    # For now we reuse BookDTO as BookDetailDTO
    book_dto = await service.create_book(user_id, data.title, data.author or "", data.description or "", data.is_public)
    await session.commit()
    return {"book": book_dto}

@router.post("/{book_id}/upload", response_model=JobStatusDTO, status_code=202)
async def upload_book_file(
    book_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith((".pdf", ".epub", ".txt")):
        raise HTTPException(status_code=400, detail="Unsupported file format.")
        
    job_status = await service.upload_book_file(book_id, user_id, file)
    await session.commit()
    
    # We must spawn a background task with a fresh DB session because the request session will close.
    async def run_job():
        async with AsyncSessionLocal() as bg_session:
            await mock_process_book_job(job_status.job_id, book_id, user_id, bg_session)

    background_tasks.add_task(run_job)
    return job_status

@router.get("/{book_id}/status", response_model=BookStatusDTO)
async def get_book_status(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service)
):
    status = await service.get_book_processing_status(book_id)
    if not status:
        raise HTTPException(status_code=404, detail="Book processing status not found")
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

@router.get("/{book_id}", response_model=BookDetailDTO)
async def get_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db)
):
    # Ownership check
    user_book = await service.book_repo.get_user_book(user_id, book_id)
    if not user_book:
        raise HTTPException(status_code=404, detail="Book not found in your library")
        
    book = await service.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    return BookDetailDTO(
        id=str(book.id),
        title=book.title,
        author=book.author,
        description=book.description,
        source_type=book.source_type,
        file_url=book.file_url,
        created_at=book.created_at,
        nodes=[]
    )

@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: BookService = Depends(get_book_service),
    session: AsyncSession = Depends(get_db)
):
    user_book = await service.book_repo.get_user_book(user_id, book_id)
    if not user_book:
        raise HTTPException(status_code=404, detail="Book not found in your library")
        
    book = await service.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    await service.book_repo.delete_user_book(user_book)
    
    if str(book.owner_id) == user_id:
        await service.book_repo.delete_book(book)
        
    await session.commit()
    return None
