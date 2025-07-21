from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime
from typing import Dict, Any
import json

from app.models.message import Message
from app.models.conversation import Conversation

class LogService:
    """
    Servicio para el registro de logs de mensajes en la conversación.
    ✅ VERSIÓN CORREGIDA - Acepta parámetro metadata
    """
    
    @staticmethod
    def log_message(
        db: Session,
        conversation_id: int,
        sender_type: str, 
        text_content: str,
        button_selected: Optional[str] = None,
        previous_state: Optional[str] = None,
        next_state: Optional[str] = None,
        metadata: Optional[str] = None  # ✅ AGREGADO - Parámetro metadata
    ) -> Message:
        """
        Registra un mensaje en la conversación.
        
        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            sender_type: Tipo de emisor ("user" o "system")
            text_content: Contenido del mensaje
            button_selected: Botón seleccionado (opcional)
            previous_state: Estado anterior (opcional)
            next_state: Estado siguiente (opcional)
            metadata: Metadata adicional en formato JSON (opcional)
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
        
        # ✅ CORREGIDO - Crear mensaje con todos los campos soportados
        try:
            new_message = Message(
                conversation_id=conversation_id,
                sender_type=sender_type,
                text_content=text_content,
                button_selected=button_selected,
                previous_state=previous_state,
                next_state=next_state,
                timestamp=datetime.now()
                # Nota: metadata se puede agregar como campo adicional si la tabla lo soporta
            )
            
            # Si hay metadata y el modelo lo soporta, agregarlo
            if metadata and hasattr(new_message, 'metadata'):
                new_message.metadata = metadata
            elif metadata:
                # Si no soporta metadata, agregarlo al text_content como nota
                if not text_content.endswith('[META]'):
                    new_message.text_content = f"{text_content} [META: {metadata}]"
            
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            
            return new_message
            
        except SQLAlchemyError as e:
            db.rollback()
            print(f"❌ Error registrando mensaje: {e}")
            
            # ✅ FALLBACK - Crear mensaje básico sin metadata si falla
            try:
                basic_message = Message(
                    conversation_id=conversation_id,
                    sender_type=sender_type,
                    text_content=text_content,
                    timestamp=datetime.now()
                )
                db.add(basic_message)
                db.commit()
                db.refresh(basic_message)
                return basic_message
                
            except Exception as fallback_error:
                print(f"❌ Error en fallback logging: {fallback_error}")
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error crítico registrando mensaje: {str(fallback_error)}"
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
            .order_by(Conversation.id.desc())  # ✅ CORREGIDO - Usar .id en lugar de .created_at
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def log_system_event(
        db: Session,
        event_type: str,
        description: str,
        conversation_id: Optional[int] = None,
        additional_data: Optional[dict] = None
    ) -> bool:
        """
        ✅ NUEVO - Registra eventos del sistema
        """
        try:
            metadata_json = json.dumps(additional_data) if additional_data else None
            
            event_message = f"[SYSTEM_EVENT:{event_type}] {description}"
            
            if conversation_id:
                # Log en conversación específica
                LogService.log_message(
                    db=db,
                    conversation_id=conversation_id,
                    sender_type="system",
                    text_content=event_message,
                    metadata=metadata_json
                )
            else:
                # Log general del sistema (podría ir a una tabla separada)
                print(f"📝 {event_message}")
                if metadata_json:
                    print(f"   Metadata: {metadata_json}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error registrando evento del sistema: {e}")
            return False
    
    @staticmethod
    def log_timeout_event(
        db: Session,
        conversation_id: int,
        event_type: str,
        stats: dict,
        reason: str
    ) -> bool:
        """
        ✅ NUEVO - Log específico para eventos de timeout
        """
        try:
            event_data = {
                "event_type": event_type,
                "stats": stats,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            
            return LogService.log_system_event(
                db=db,
                event_type="TIMEOUT",
                description=f"Timeout event: {event_type} - {reason}",
                conversation_id=conversation_id,
                additional_data=event_data
            )
            
        except Exception as e:
            print(f"❌ Error registrando timeout event: {e}")
            return False
    
    @staticmethod
    def log_message_safe(
        db: Session,
        conversation_id: int,
        sender_type: str, 
        text_content: str,
        button_selected: Optional[str] = None,
        previous_state: Optional[str] = None,
        next_state: Optional[str] = None,
        metadata_dict: Optional[Dict[str, Any]] = None 
    ) -> Message:
        """
        ✅ VERSIÓN SEGURA - Maneja automáticamente la serialización de metadata
        """
        metadata_json = None
        if metadata_dict:
            try:
                from app.api.endpoints.chat import clean_data_for_json, safe_json_dumps
            except ImportError:
                def clean_data_for_json(data):
                    return data
                def safe_json_dumps(data):
                    import json
                    return json.dumps(data, ensure_ascii=False)
            try:
                metadata_limpio = clean_data_for_json(metadata_dict)
                metadata_json = safe_json_dumps(metadata_limpio)
            except Exception as e:
                print(f"⚠️ Error serializando metadata: {e}")
                metadata_json = None
        
        # ✅ USAR MÉTODO ORIGINAL CON METADATA YA SERIALIZADA
        return LogService.log_message(
            db=db,
            conversation_id=conversation_id,
            sender_type=sender_type,
            text_content=text_content,
            button_selected=button_selected,
            previous_state=previous_state,
            next_state=next_state,
            metadata=metadata_json
        )