from fastapi import APIRouter, Depends
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
async def get_notifications(user_id: str = Depends(get_current_user_id)):
    # Mock endpoint returning an empty list so the frontend doesn't 404
    return {"notifications": []}
