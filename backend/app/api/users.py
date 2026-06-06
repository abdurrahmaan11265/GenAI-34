from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserDTO, UserUpdateDTO
from app.repositories.user_repo import UserRepository
from app.api.deps import get_db, get_current_user_id

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserDTO)
async def get_me(user_id: str = Depends(get_current_user_id), session: AsyncSession = Depends(get_db)):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return UserDTO.from_orm(user)

@router.patch("/me", response_model=UserDTO)
async def update_me(
    data: UserUpdateDTO,
    user_id: str = Depends(get_current_user_id), 
    session: AsyncSession = Depends(get_db)
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields that were provided
    update_data = data.model_dump(exclude_unset=True)
    
    if "name" in update_data:
        user.full_name = update_data.pop("name")
        
    for key, value in update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)
            
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return UserDTO.from_orm(user)
