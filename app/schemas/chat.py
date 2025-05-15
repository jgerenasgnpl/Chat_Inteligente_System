from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    user_id: int
    message: Optional[str] = None
    text: Optional[str] = None  
    button_selected: Optional[str] = None
    is_button: Optional[bool] = False 
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
    user_id: int
    title: str
    created_at: datetime
    is_active: bool
    last_message_at: datetime
    message_count: int  # Número de mensajes en la conversación

    model_config = {
        "from_attributes": True
    }

class ConversationListResponse(BaseModel):
    conversations: List[ConversationListItem]
    total: int