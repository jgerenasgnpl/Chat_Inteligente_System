from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import json
from datetime import datetime

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User

import yaml
try:
    with open("base_conocimiento.yaml", encoding="utf-8") as f:
        kb = yaml.safe_load(f)
except:
    kb = {}

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
        # conversacion activa
        active_conversation = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id, Conversation.is_active == True)
            .first()
        )
        
        if active_conversation:
            return active_conversation
        
        # Crear nueva conversación
        if not title:
            title = f"Negociación {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
        new_conversation = Conversation(
            user_id=user_id,
            current_state="validar_documento",
            is_active=True
        )
        
        print(f"Creando nueva conversación con estado inicial: {new_conversation.current_state}")
        
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
        ✅ VERSIÓN CORREGIDA CON MANEJO JSON SEGURO
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        try:
            # Actualizar estado
            conversation.current_state = new_state
            
            # ✅ MANEJO SEGURO DEL CONTEXTO
            if context_data:
                existing_context = {}
                
                # Obtener contexto existente de forma segura
                if hasattr(conversation, 'context_data') and conversation.context_data:
                    if isinstance(conversation.context_data, dict):
                        existing_context = conversation.context_data.copy()
                    elif isinstance(conversation.context_data, str):
                        try:
                            existing_context = json.loads(conversation.context_data)
                        except Exception as e:
                            print(f"⚠️ Error parseando contexto existente: {e}")
                            existing_context = {}
                    else:
                        existing_context = {}
                
                # Actualizar contexto con nuevos datos
                if isinstance(context_data, dict):
                    existing_context.update(context_data)
                    
                    # ✅ CONVERTIR A JSON STRING ANTES DE GUARDAR
                    try:
                        json_context = json.dumps(existing_context, ensure_ascii=False, default=str)
                        conversation.context_data = json_context
                        print(f"💾 Contexto guardado como JSON: {len(existing_context)} elementos")
                    except Exception as e:
                        print(f"❌ Error convirtiendo contexto a JSON: {e}")
                        # Fallback: guardar como string simple
                        conversation.context_data = str(existing_context)
                else:
                    # Si context_data no es dict, intentar convertirlo
                    try:
                        json_context = json.dumps(context_data, ensure_ascii=False, default=str)
                        conversation.context_data = json_context
                    except:
                        conversation.context_data = str(context_data)
            
            db.commit()
            db.refresh(conversation)
            print(f"✅ Estado actualizado: {conversation.current_state}")
            return conversation
            
        except SQLAlchemyError as e:
            db.rollback()
            error_msg = f"Error al actualizar estado: {str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        except Exception as e:
            db.rollback()
            error_msg = f"Error inesperado: {str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
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
    
    @staticmethod
    def safe_get_context_data(conversation: Conversation) -> Dict[str, Any]:
        """
        Obtiene context_data como diccionario de forma segura
        """
        try:
            if hasattr(conversation, 'context_data') and conversation.context_data:
                if isinstance(conversation.context_data, dict):
                    return conversation.context_data
                elif isinstance(conversation.context_data, str):
                    return json.loads(conversation.context_data)
                else:
                    return {}
            else:
                return {}
        except Exception as e:
            print(f"⚠️ Error obteniendo contexto: {e}")
            return {}
