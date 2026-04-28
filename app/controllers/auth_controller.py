from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.user import UserCreate, UserLogin
from app.services.auth_service import register_user, login_user, refresh_access_token


router = APIRouter(tags=["Authentication"])


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    return login_user(user, db)


@router.post("/refresh")
def refresh(refresh_token: str):
    return refresh_access_token(refresh_token)