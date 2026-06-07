from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.repositories.lesson_repo import LessonRepository
from app.repositories.graph_repo import GraphRepository
from app.repositories.assessment_repo import AssessmentRepository
from app.services.lesson_service import LessonService
from app.schemas.lesson import (
    StartLessonRequest, LessonSessionDTO, TutorRequest, TutorResponseDTO,
    HintRequest, HintDTO, CompleteLessonDTO,
)

router = APIRouter(prefix="/lessons", tags=["Lessons"])


def get_lesson_service(session: AsyncSession = Depends(get_db)) -> LessonService:
    return LessonService(LessonRepository(session), GraphRepository(session), AssessmentRepository(session))


@router.post("", response_model=LessonSessionDTO, status_code=201)
async def start_lesson(
    data: StartLessonRequest,
    user_id: str = Depends(get_current_user_id),
    service: LessonService = Depends(get_lesson_service),
    session: AsyncSession = Depends(get_db),
):
    result = await service.start_lesson(user_id, data.book_id, data.concept_id)
    await session.commit()
    return result


@router.get("/{session_id}", response_model=LessonSessionDTO)
async def get_lesson(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: LessonService = Depends(get_lesson_service),
):
    return await service.get_lesson(user_id, session_id)


@router.post("/{session_id}/tutor", response_model=TutorResponseDTO)
async def tutor_turn(
    session_id: str,
    data: TutorRequest,
    user_id: str = Depends(get_current_user_id),
    service: LessonService = Depends(get_lesson_service),
    session: AsyncSession = Depends(get_db),
):
    result = await service.tutor_turn(user_id, session_id, data.message, data.hint_level, data.is_question)
    await session.commit()
    return result


@router.post("/{session_id}/hint", response_model=HintDTO)
async def get_hint(
    session_id: str,
    data: HintRequest,
    user_id: str = Depends(get_current_user_id),
    service: LessonService = Depends(get_lesson_service),
):
    return await service.hint(user_id, session_id, data.question, data.hint_level)


@router.post("/{session_id}/complete", response_model=CompleteLessonDTO)
async def complete_lesson(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: LessonService = Depends(get_lesson_service),
    session: AsyncSession = Depends(get_db),
):
    result = await service.complete_lesson(user_id, session_id)
    await session.commit()
    return result
