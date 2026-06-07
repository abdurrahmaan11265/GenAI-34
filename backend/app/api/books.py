from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user_id
from app.repositories.book_repo import BookRepository
from app.services.book_service import BookService, mock_process_book_job
from app.schemas.book import UploadResponse, JobStatusDTO, BookDTO, BookCreate, BookStatusDTO, BookDetailDTO, GraphDTO, BookSummaryDTO
from app.schemas.graph_reveal import PersonalGraphDTO
from app.repositories.graph_repo import GraphRepository
from app.services.graph_reveal_service import GraphRevealService
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
    
    # We no longer spawn a background task here because the separate ingestion_worker.py
    # daemon polling the graph_build_jobs table will pick up this QUEUED job.
    
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

@router.get("/{book_id}/graph", response_model=GraphDTO)
async def get_book_graph(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy import text
    
    # Verify ownership
    check = await session.execute(text(
        'SELECT 1 FROM user_books WHERE user_id = :uid AND book_id = :bid'
    ), {"uid": user_id, "bid": book_id})
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Book not found in your library")
    
    service = BookService(BookRepository(session))
    return await service.get_book_graph(book_id)

@router.get("/{book_id}/knowledge-graph", response_model=PersonalGraphDTO)
async def get_personal_knowledge_graph(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Personalized graph reveal: nodes + edges overlaid with this user's
    per-concept state and mastery (four-state coloring for the map view)."""
    service = GraphRevealService(GraphRepository(session))
    return await service.get_personal_graph(user_id, book_id)


@router.post("/{book_id}/graph/confirm")
async def confirm_book_graph(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy import text
    
    # 1. Update book status to READY
    await session.execute(text('''
        UPDATE books SET status = 'READY' WHERE id = :bid
    '''), {"bid": book_id})
    
    # 2. Add UserNodeStates for all nodes
    await session.execute(text('''
        INSERT INTO user_concept_state (user_id, concept_id, graph_version, state)
        SELECT :uid, id, graph_version, 'LOCKED'
        FROM concepts
        WHERE book_id = :bid
        ON CONFLICT (user_id, concept_id, graph_version) DO NOTHING
    '''), {"uid": user_id, "bid": book_id})
    
    await session.commit()
    return {"success": True}

@router.get("", response_model=dict)
async def get_user_books(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
):
    service = BookService(BookRepository(session))
    books = await service.book_repo.get_books_by_user(user_id)
    summaries = []
    for b in books:
        status_str = getattr(b, 'status', 'UPLOADING').lower()
        if status_str == 'uploading':
            status_str = 'uploaded'
            
        summaries.append(BookSummaryDTO(
            id=str(b.id),
            title=b.title,
            author=b.author,
            coverUrl=None,
            status=status_str,
            progress=0,
            totalNodes=0,
            masteredNodes=0,
            dueToday=0,
            lastStudied=None,
            createdAt=b.created_at.isoformat()
        ).model_dump(by_alias=True))
        
    return {"books": summaries}

@router.get("/{book_id}", response_model=dict)
async def get_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
):
    service = BookService(BookRepository(session))
    # Ownership check
    user_book = await service.book_repo.get_user_book(user_id, book_id)
    if not user_book:
        raise HTTPException(status_code=404, detail="Book not found in your library")
        
    book = await service.book_repo.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    from sqlalchemy import text
    states = await session.execute(text('''
        SELECT ucs.concept_id, ucs.state 
        FROM user_concept_state ucs
        JOIN concepts c ON c.id = ucs.concept_id
        WHERE ucs.user_id = :uid AND c.book_id = :bid
    '''), {"uid": user_id, "bid": book_id})
    
    nodes = []
    for r in states:
        nodes.append({
            "id": str(r.concept_id),
            "userNodeStates": [{
                "nodeId": str(r.concept_id),
                "state": r.state
            }]
        })
        
    return {
        "book": BookDetailDTO(
            id=str(book.id),
            title=book.title,
            author=book.author,
            description=book.description,
            source_type=book.source_type,
            file_url=book.file_url,
            created_at=book.created_at,
            nodes=nodes
        ).model_dump()
    }

@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy import text
    
    # Verify ownership via user_books
    result = await session.execute(text('''
        SELECT ub.id, b.owner_id
        FROM user_books ub
        JOIN books b ON b.id = ub.book_id
        WHERE ub.user_id = :uid AND ub.book_id = :bid
    '''), {"uid": user_id, "bid": book_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Book not found in your library")
    
    user_book_id, owner_id = row
    
    # Remove from user's library
    await session.execute(
        text('DELETE FROM user_books WHERE id = :id'),
        {"id": str(user_book_id)}
    )
    
    # If this user owns the book, delete it entirely (cascades to all children)
    if str(owner_id) == user_id:
        await session.execute(
            text('DELETE FROM books WHERE id = :id'),
            {"id": book_id}
        )
    
    await session.commit()
    return None
