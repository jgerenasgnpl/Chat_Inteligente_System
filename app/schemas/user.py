from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str

# app/schemas/conversation.py
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

# app/schemas/message.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MessageBase(BaseModel):
    sender_type: str  # "user" o "system"
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

# app/schemas/chat.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    user_id: int
    message: Optional[str] = None
    button_selected: Optional[str] = None
    conversation_id: Optional[int] = None

class ButtonOption(BaseModel):
    id: str
    text: str

class ChatResponse(BaseModel):
    conversation_id: int
    message: str
    current_state: str
    buttons: Optional[List[ButtonOption]] = None
    context_data: Optional[Dict[str, Any]] = None

class ConversationHistoryRequest(BaseModel):
    user_id: int
    conversation_id: Optional[int] = None
    limit: Optional[int] = 50
    skip: Optional[int] = 0

class ConversationListItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    is_active: bool
    message_count: int  # Número de mensajes en la conversación

class ConversationListResponse(BaseModel):
    conversations: List[ConversationListItem]
    total: int