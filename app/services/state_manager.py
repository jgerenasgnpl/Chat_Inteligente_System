from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import json
from datetime import datetime

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User

class StateManager:
    """
    Gestiona el estado de las conversaciones en el sistema de negociación.
    Se encarga de crear, actualizar y obtener información sobre las conversaciones.
    """
    
    @staticmethod
    def get_or_create_conversation(db: Session, user_id: int, title: Optional[str] = None) -> Conversation:
        """
        Obtiene la conversación activa del usuario o crea una nueva si no existe.
        """
        # Buscar conversación activa
        active_conversation = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id, Conversation.is_active == True)
            .first()
        )
        
        if active_conversation:
            return active_conversation
        
        # Crear nueva conversación si no hay una activa
        if not title:
            title = f"Negociación {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
        new_conversation = Conversation(
            user_id=user_id,
            title=title,
            current_state="initial",
            is_active=True
        )
        
        try:
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
            return new_conversation
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear conversación: {str(e)}"
            )
    
    @staticmethod
    def update_conversation_state(
        db: Session, 
        conversation_id: int, 
        new_state: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Actualiza el estado de una conversación y opcionalmente su contexto.
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        try:
            conversation.current_state = new_state
            
            if context_data:
                # Si ya existe contexto, actualizarlo
                if conversation.context_data:
                    existing_context = conversation.context_data
                    existing_context.update(context_data)
                    conversation.context_data = existing_context
                else:
                    conversation.context_data = context_data
            
            db.commit()
            db.refresh(conversation)
            return conversation
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar estado: {str(e)}"
            )
    
    @staticmethod
    def get_current_state(db: Session, conversation_id: int) -> str:
        """
        Obtiene el estado actual de una conversación.
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        return conversation.current_state
    
    @staticmethod
    def end_conversation(db: Session, conversation_id: int) -> Conversation:
        """
        Marca una conversación como finalizada.
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        try:
            conversation.is_active = False
            conversation.ended_at = datetime.now()
            db.commit()
            db.refresh(conversation)
            return conversation
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al finalizar conversación: {str(e)}"
            )