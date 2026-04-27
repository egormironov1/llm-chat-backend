from datetime import datetime, timedelta, timezone
import uuid
import os

import redis
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from dotenv import load_dotenv

from app.database import Base, engine
from app.models import user as user_model
from app.models import chat as chat_model
from app.models import message as message_model
from app.schemas.user import UserCreate, UserLogin
from app.schemas.chat import ChatCreate, MessageCreate
from app.deps import get_db
from starlette.middleware.sessions import SessionMiddleware
from app.services.llm_service import generate_answer
load_dotenv()

app = FastAPI(title="LLM Chat Backend")
app.add_middleware(
    SessionMiddleware,
    secret_key="session-secret-key-change-me"
)

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

oauth = OAuth()

oauth.register(
    name="github",
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


@app.get("/")
def root():
    return {"message": "Backend is working"}


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int):
    refresh_token = str(uuid.uuid4())

    redis_client.setex(
        name=f"refresh:{refresh_token}",
        time=REFRESH_TOKEN_EXPIRE_SECONDS,
        value=str(user_id)
    )

    return refresh_token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(user_model.User).filter(
        user_model.User.id == int(user_id)
    ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(user_model.User).filter(
        user_model.User.login == user.login
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = pwd_context.hash(user.password)

    new_user = user_model.User(
        login=user.login,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()

    return {"message": "User created"}


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(user_model.User).filter(
        user_model.User.login == user.login
    ).first()

    if db_user is None:
        raise HTTPException(status_code=401, detail="Invalid login or password")

    if not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid login or password")

    access_token = create_access_token(data={"sub": str(db_user.id)})
    refresh_token = create_refresh_token(user_id=db_user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@app.post("/refresh")
def refresh(refresh_token: str):
    user_id = redis_client.get(f"refresh:{refresh_token}")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token = create_access_token(data={"sub": str(user_id)})

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@app.get("/auth/github")
async def github_login(request: Request):
    redirect_uri = "http://127.0.0.1:8000/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)


@app.get("/auth/github/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.github.authorize_access_token(request)

    resp = await oauth.github.get("user", token=token)
    profile = resp.json()

    github_id = str(profile["id"])
    login = profile.get("login", f"github_{github_id}")

    user = db.query(user_model.User).filter(
        user_model.User.login == login
    ).first()

    if not user:
        user = user_model.User(
            login=login,
            password="oauth"
        )
        db.add(user)
        db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "login": login
    }


@app.get("/me")
def me(current_user: user_model.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "login": current_user.login
    }

@app.post("/chats")
def create_chat(
    chat: ChatCreate,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_chat = chat_model.Chat(
        title=chat.title,
        user_id=current_user.id
    )

    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return {
        "id": new_chat.id,
        "title": new_chat.title,
        "user_id": new_chat.user_id
    }

@app.get("/chats")
def get_chats(
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chats = db.query(chat_model.Chat).filter(
        chat_model.Chat.user_id == current_user.id
    ).all()

    return chats

@app.get("/chats/{chat_id}/messages")
def get_messages(
    chat_id: int,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(chat_model.Chat).filter(
        chat_model.Chat.id == chat_id,
        chat_model.Chat.user_id == current_user.id
    ).first()

    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(message_model.Message).filter(
        message_model.Message.chat_id == chat_id
    ).all()

    return messages

@app.post("/chats/{chat_id}/ask")
def ask_chat(
    chat_id: int,
    message: MessageCreate,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = db.query(chat_model.Chat).filter(
        chat_model.Chat.id == chat_id,
        chat_model.Chat.user_id == current_user.id
    ).first()

    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    user_message = message_model.Message(
        chat_id=chat_id,
        role="user",
        content=message.content
    )

    db.add(user_message)

    assistant_answer = generate_answer(message.content)

    assistant_message = message_model.Message(
        chat_id=chat_id,
        role="assistant",
        content=assistant_answer
    )

    db.add(assistant_message)
    db.commit()

    return {
        "user_message": message.content,
        "assistant_answer": assistant_answer
    }