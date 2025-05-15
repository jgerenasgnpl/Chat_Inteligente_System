from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ConversationBase(BaseModel):
    title: Optional[str] = None
    current_state: str = "initial"
    is_active: bool = True

class ConversationCreate(ConversationBase):
    user_id: int

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    current_state: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ConversationInDBBase(ConversationBase):
    id: int
    user_id: int
    context_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class Conversation(ConversationInDBBase):
    pass