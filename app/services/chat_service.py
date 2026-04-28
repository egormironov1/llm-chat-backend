from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import user as user_model
from app.models import chat as chat_model
from app.models import message as message_model
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.llm_service import generate_answer


def create_user_chat(
    chat: ChatCreate,
    current_user: user_model.User,
    db: Session
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


def get_user_chats(
    current_user: user_model.User,
    db: Session
):
    chats = db.query(chat_model.Chat).filter(
        chat_model.Chat.user_id == current_user.id
    ).all()

    return chats


def get_chat_messages(
    chat_id: int,
    current_user: user_model.User,
    db: Session
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


def ask_llm_in_chat(
    chat_id: int,
    message: MessageCreate,
    current_user: user_model.User,
    db: Session
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