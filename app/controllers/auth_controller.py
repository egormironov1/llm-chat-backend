from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import (
    register_user,
    login_user,
    refresh_access_token
)


router = APIRouter(tags=["Authentication"])


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await register_user(user, db)


@router.post("/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    return await login_user(user, db)


@router.post("/refresh")
async def refresh(refresh_token: str):
    return await refresh_access_token(refresh_token)