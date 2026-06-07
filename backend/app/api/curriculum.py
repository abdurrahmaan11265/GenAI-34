from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user_id
from app.repositories.graph_repo import GraphRepository
from app.repositories.curriculum_repo import CurriculumRepository
from app.services.curriculum_service import CurriculumService
from app.schemas.curriculum import CurriculumDTO, DailyPlanDTO

router = APIRouter(prefix="/books", tags=["Curriculum"])


def get_curriculum_service(session: AsyncSession = Depends(get_db)) -> CurriculumService:
    return CurriculumService(GraphRepository(session), CurriculumRepository(session))


@router.post("/{book_id}/curriculum", response_model=CurriculumDTO, status_code=201)
async def generate_curriculum(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: CurriculumService = Depends(get_curriculum_service),
    session: AsyncSession = Depends(get_db),
):
    result = await service.generate_curriculum(user_id, book_id)
    await session.commit()
    return result


@router.get("/{book_id}/curriculum", response_model=CurriculumDTO)
async def get_curriculum(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: CurriculumService = Depends(get_curriculum_service),
    session: AsyncSession = Depends(get_db),
):
    result = await service.get_curriculum(user_id, book_id)
    await session.commit()  # may generate-on-read
    return result


@router.get("/{book_id}/daily-plan", response_model=DailyPlanDTO)
async def get_daily_plan(
    book_id: str,
    user_id: str = Depends(get_current_user_id),
    service: CurriculumService = Depends(get_curriculum_service),
    session: AsyncSession = Depends(get_db),
):
    result = await service.get_daily_plan(user_id, book_id)
    await session.commit()  # persists today's frozen plan on first build
    return result
