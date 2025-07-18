from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageBase(BaseModel):
    sender_type: str 
    text_content: str
    button_selected: Optional[str] = None
    previous_state: Optional[str] = None
    next_state: Optional[str] = None

class MessageCreate(MessageBase):
    conversation_id: int

class MessageInDBBase(MessageBase):
    id: int
    conversation_id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class Message(MessageInDBBase):
    pass