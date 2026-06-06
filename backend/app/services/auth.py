from fastapi import HTTPException, status
from app.schemas.user import UserCreate, UserLogin, AuthResponse
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, data: UserCreate) -> AuthResponse:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        hashed = get_password_hash(data.password)
        new_user = User(
            full_name=data.name,
            email=data.email,
            password_hash=hashed,
            role="STUDENT",
            is_active=True
        )
        
        user = await self.user_repo.create_user(new_user)
        
        token = create_access_token(subject=user.id)
        
        return AuthResponse(
            user={"id": str(user.id), "name": user.full_name, "email": user.email},
            token=token
        )

    async def login(self, data: UserLogin) -> AuthResponse:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        token = create_access_token(subject=user.id)
        
        return AuthResponse(
            user={"id": str(user.id), "name": user.full_name, "email": user.email},
            token=token
        )
