from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Dependencias
from app.api.deps import get_db, get_current_active_user

# Modelos SQLAlchemy
from app.models.conversation import Conversation
from app.models.message import Message as MessageModel
from app.models.user import User as UserModel

# Schemas Pydantic
from app.schemas.chat import ChatRequest, ChatResponse, ConversationListResponse
from app.schemas.message import Message as MessageSchema

# Servicios
from app.services.state_manager import StateManager
from app.services.log_service import LogService

router = APIRouter(
    prefix="",
    dependencies=[Depends(get_current_active_user)],
    tags=["chat"]
)

@router.post("/message", response_model=ChatResponse)
def process_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Procesa un mensaje de chat y devuelve la respuesta.
    El usuario se toma de `current_user`.
    """
    # Validar o crear conversación
    if request.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == request.conversation_id,
                    Conversation.user_id == current_user.id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    else:
        conversation = StateManager.get_or_create_conversation(db, current_user.id)

    # Log mensaje usuario
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="user",
        text_content=request.message or "",
        button_selected=request.button_selected,
        previous_state=conversation.current_state
    )

    # … lógica de negocio temporaria …
    system_response = "Respuesta temporal del sistema."
    buttons = [{"id": "opt1", "text": "Opción 1"}]

    # Actualizar estado
    new_state = (
        "responding"
        if conversation.current_state == "initial"
        else "in_progress"
    )
    conversation = StateManager.update_conversation_state(
        db=db,
        conversation_id=conversation.id,
        new_state=new_state
    )

    # Log respuesta sistema
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="system",
        text_content=system_response,
        previous_state=conversation.current_state,
        next_state=new_state
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message=system_response,
        current_state=new_state,
        buttons=buttons,
        context_data=conversation.context_data
    )

@router.get("/history", response_model=List[MessageSchema])
def get_conversation_history(
    conversation_id: Optional[int] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Historial de mensajes. Sin path params: tomo `current_user.id`.
    """
    if not conversation_id:
        conv = StateManager.get_or_create_conversation(db, current_user.id)
        conversation_id = conv.id
    else:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id)
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no existe")

    return LogService.get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        skip=skip
    )

@router.get("/conversations", response_model=ConversationListResponse)
def get_user_conversations(
    active_only: bool = False,
    limit: int = 10,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """
    Lista de conversaciones del usuario autenticado.
    """
    # Ya no necesitas recibir user_id: uso current_user.id
    total = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .count()
    )
    convs = LogService.get_user_conversations(
        db=db,
        user_id=current_user.id,
        include_active_only=active_only,
        limit=limit,
        skip=skip
    )

    items = []
    for c in convs:
        count = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_id == c.id)
            .count()
        )
        items.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
            "is_active": c.is_active,
            "message_count": count
        })

    return ConversationListResponse(conversations=items, total=total)