from pydantic import BaseModel

class ChatCreate(BaseModel):
    title: str = "New chat"

class MessageCreate(BaseModel):
    content: str