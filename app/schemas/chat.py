from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    user_id: int
    message: Optional[str] = None
    text: Optional[str] = None 
    conversation_id: Optional[int] = None
    button_selected: Optional[str] = None
    intention: Optional[str] = None

class ButtonOption(BaseModel):
    id: str
    text: str
    next_state: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: int
    message: str
    current_state: str
    buttons: Optional[List[ButtonOption]] = []
    context_data: Optional[Dict[str, Any]] = {}

class MessageResponse(BaseModel):
    """Modelo para respuesta de mensaje individual"""
    id: int
    sender_type: str
    text_content: str
    timestamp: Optional[str] = None
    button_selected: Optional[str] = None
    previous_state: Optional[str] = None
    next_state: Optional[str] = None

class ConversationHistoryResponse(BaseModel):
    conversation_id: int
    messages: List[Dict[str, Any]]
    total: int
    current_state: str

class ConversationListResponse(BaseModel):
    conversations: List[Dict[str, Any]]
    total: int

class CedulaTestRequest(BaseModel):
    """Modelo para test de cédula"""
    cedula: str

class CedulaTestResponse(BaseModel):
    """Modelo para respuesta de test de cédula"""
    cedula: str
    cliente_encontrado: bool
    nombre_cliente: Optional[str] = None
    saldo_total: Optional[str] = None
    banco: Optional[str] = None
    mensaje: str
    
class ConfiguracionEstado(BaseModel):
    nombre: str
    mensaje_template: str
    accion: Optional[str] = None
    condicion: Optional[str] = None
    estado_siguiente_true: Optional[str] = None
    estado_siguiente_false: Optional[str] = None
    estado_siguiente_default: Optional[str] = None

class ConfiguracionIntencion(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    estado_siguiente: Optional[str] = None
    patrones: List[str] = []