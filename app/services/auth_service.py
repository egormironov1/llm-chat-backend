from datetime import datetime, timedelta, timezone
import uuid

import redis.asyncio as redis
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models import user as user_model
from app.schemas.user import UserCreate, UserLogin


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = "super-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(user_id: int):
    refresh_token = str(uuid.uuid4())

    await redis_client.setex(
        name=f"refresh:{refresh_token}",
        time=REFRESH_TOKEN_EXPIRE_SECONDS,
        value=str(user_id)
    )

    return refresh_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(user_model.User).where(user_model.User.id == int(user_id))
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def register_user(user: UserCreate, db: AsyncSession):
    result = await db.execute(
        select(user_model.User).where(user_model.User.login == user.login)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = pwd_context.hash(user.password)

    new_user = user_model.User(
        login=user.login,
        password=hashed_password
    )

    db.add(new_user)
    await db.commit()

    return {"message": "User created"}


async def login_user(user: UserLogin, db: AsyncSession):
    result = await db.execute(
        select(user_model.User).where(user_model.User.login == user.login)
    )

    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid login or password")

    if not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token = await create_refresh_token(user_id=db_user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


async def refresh_access_token(refresh_token: str):
    user_id = await redis_client.get(f"refresh:{refresh_token}")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token = create_access_token(data={"sub": str(user_id)})

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }