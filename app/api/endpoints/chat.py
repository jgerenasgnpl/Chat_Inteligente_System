from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationHistoryRequest, ConversationListResponse
from app.schemas.message import Message
from app.services.state_manager import StateManager
from app.services.log_service import LogService
# Este servicio se implementará en el Recurso 3
# from app.services.chat_logic import ChatLogicService

router = APIRouter()

@router.post("/message", response_model=ChatResponse)
def process_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Procesa un mensaje de chat y devuelve la respuesta.
    """
    # Obtener o crear conversación
    if request.conversation_id:
        # Verificar que la conversación existe y pertenece al usuario
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == request.user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no pertenece al usuario"
            )
    else:
        # Crear nueva conversación
        conversation = StateManager.get_or_create_conversation(db, request.user_id)
    
    # Obtener estado actual de la conversación
    current_state = conversation.current_state
    
    # Registrar mensaje del usuario
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="user",
        text_content=request.message or "",
        button_selected=request.button_selected,
        previous_state=current_state
    )
    
    # Por ahora, simulamos la respuesta del sistema
    # En el Recurso 3 se implementará la lógica real de negociación
    system_response = "Esta es una respuesta temporal del sistema. La lógica de negociación se implementará en el Recurso 3."
    buttons = [
        {"id": "option1", "text": "Opción 1"},
        {"id": "option2", "text": "Opción 2"}
    ]
    
    # Actualizar estado (temporal, hasta que se implemente la lógica real)
    new_state = "responding" if current_state == "initial" else "in_progress"
    conversation = StateManager.update_conversation_state(
        db=db,
        conversation_id=conversation.id,
        new_state=new_state
    )
    
    # Registrar respuesta del sistema
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="system",
        text_content=system_response,
        previous_state=current_state,
        next_state=new_state
    )
    
    # Devolver respuesta
    return ChatResponse(
        conversation_id=conversation.id,
        message=system_response,
        current_state=new_state,
        buttons=buttons,
        context_data=conversation.context_data
    )

@router.get("/history/{user_id}", response_model=List[Message])
def get_conversation_history(
    user_id: int,
    conversation_id: Optional[int] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de mensajes de una conversación.
    """
    # Si no se especifica conversation_id, obtener la conversación activa
    if not conversation_id:
        conversation = StateManager.get_or_create_conversation(db, user_id)
        conversation_id = conversation.id
    else:
        # Verificar que la conversación pertenece al usuario
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no pertenece al usuario"
            )
    
    # Obtener historial de mensajes
    messages = LogService.get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        skip=skip
    )
    
    return messages

@router.get("/conversations/{user_id}", response_model=ConversationListResponse)
def get_user_conversations(
    user_id: int,
    active_only: bool = False,
    limit: int = 10,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """
    Obtiene las conversaciones de un usuario.
    """
    # Verificar que el usuario existe
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Obtener conversaciones
    conversations = LogService.get_user_conversations(
        db=db,
        user_id=user_id,
        include_active_only=active_only,
        limit=limit,
        skip=skip
    )
    
    # Contar el número de mensajes en cada conversación
    result = []
    for conv in conversations:
        message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append({
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at,
            "is_active": conv.is_active,
            "message_count": message_count
        })
    
    # Contar el total de conversaciones
    total = db.query(Conversation).filter(Conversation.user_id == user_id).count()
    
    return ConversationListResponse(
        conversations=result,
        total=total
    )