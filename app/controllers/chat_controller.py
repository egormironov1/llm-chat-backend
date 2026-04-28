from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import user as user_model
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.auth_service import get_current_user
from app.services.chat_service import (
    create_user_chat,
    get_user_chats,
    get_chat_messages,
    ask_llm_in_chat
)


router = APIRouter(tags=["Chats"])


@router.post("/chats")
def create_chat(
    chat: ChatCreate,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_user_chat(chat, current_user, db)


@router.get("/chats")
def get_chats(
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_user_chats(current_user, db)


@router.get("/chats/{chat_id}/messages")
def get_messages(
    chat_id: int,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_chat_messages(chat_id, current_user, db)


@router.post("/chats/{chat_id}/ask")
def ask_chat(
    chat_id: int,
    message: MessageCreate,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ask_llm_in_chat(chat_id, message, current_user, db)