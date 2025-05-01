from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime

from app.models.message import Message
from app.models.conversation import Conversation

class LogService:
    """
    Servicio para el registro de logs de mensajes en la conversación.
    """
    
    @staticmethod
    def log_message(
        db: Session,
        conversation_id: int,
        sender_type: str,  # "user" o "system"
        text_content: str,
        button_selected: Optional[str] = None,
        previous_state: Optional[str] = None,
        next_state: Optional[str] = None
    ) -> Message:
        """
        Registra un mensaje en la conversación.
        """
        # Verificar que la conversación existe
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        # Si no se especifica el estado previo, usar el estado actual de la conversación
        if not previous_state:
            previous_state = conversation.current_state
            
        # Crear el mensaje
        new_message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            text_content=text_content,
            button_selected=button_selected,
            previous_state=previous_state,
            next_state=next_state,
            timestamp=datetime.now()
        )
        
        try:
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            return new_message
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al registrar mensaje: {str(e)}"
            )
    
    @staticmethod
    def get_conversation_history(
        db: Session, 
        conversation_id: int,
        limit: int = 50,
        skip: int = 0
    ) -> List[Message]:
        """
        Obtiene el historial de mensajes de una conversación.
        """
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id: int,
        include_active_only: bool = False,
        limit: int = 10,
        skip: int = 0
    ) -> List[Conversation]:
        """
        Obtiene las conversaciones de un usuario.
        """
        query = db.query(Conversation).filter(Conversation.user_id == user_id)
        
        if include_active_only:
            query = query.filter(Conversation.is_active == True)
            
        return (
            query
            .order_by(Conversation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )