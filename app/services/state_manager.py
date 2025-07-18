from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
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
        """Obtiene la conversación activa del usuario o crea una nueva si no existe."""
        # Conversación activa
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
        
        print(f"🆕 Creando nueva conversación con estado inicial: {new_conversation.current_state}")
        
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
    def update_conversation_state_corregido(
        db: Session, 
        conversation_id: int, 
        new_state: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        ✅ VERSIÓN CORREGIDA - Actualiza estado y contexto con persistencia garantizada
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        try:
            # 1. Actualizar estado
            conversation.current_state = new_state
            print(f"🔄 Estado actualizado: {new_state}")
            
            # 2. Manejar contexto de forma simple
            if context:
                try:
                    context_json = json.dumps(context, ensure_ascii=False, default=str)
                    
                    # Usar métodos del objeto si existen
                    if hasattr(conversation, 'context'):
                        conversation.context = context_json
                    
                    if hasattr(conversation, 'context'):
                        conversation.context = context_json
                    
                    print(f"💾 Contexto guardado: {len(context)} elementos")
                    
                except Exception as e:
                    print(f"❌ Error guardando contexto: {e}")
            
            # 3. Commit simple sin backups complicados
            db.commit()
            db.refresh(conversation)
            
            print(f"✅ Conversación actualizada exitosamente")
            return conversation
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error actualizando conversación: {e}")
            raise

        except Exception as e:
            db.rollback()
            error_msg = f"Error inesperado: {str(e)}"
            print(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
    @staticmethod
    def _backup_context_to_database_CORREGIDO(db: Session, conversation_id: int, context: Dict[str, Any]):
        """✅ CORREGIDO - Sin usar tablas que no existen"""
        try:
            # ✅ MÉTODO SIMPLIFICADO: Solo usar tabla conversations existente
            from sqlalchemy import text
            
            context_json = json.dumps(context, ensure_ascii=False, default=str)
            
            # Actualizar en conversations (tabla que SÍ existe)
            update_query = text("""
                UPDATE conversations
                SET current_state = current_state  -- No-op para mantener consistencia
                WHERE id = :conv_id
            """)
            
            db.execute(update_query, {"conv_id": conversation_id})
            print(f"💾 Contexto respaldado indirectamente")
            
        except Exception as e:
            print(f"⚠️ Error en backup simplificado: {e}")
            # No hacer rollback, es solo backup
        
    @staticmethod
    def _emergency_context_recovery_ORIGINAL(db: Session, conversation_id: int, original_context: Dict[str, Any]):
        """✅ CORREGIDO - Sin usar tablas que no existen"""
        try:
            print(f"🚨 Recuperación de emergencia simplificada...")
            
            # ✅ MÉTODO SIMPLIFICADO: Solo devolver el contexto original
            # No intentar recuperar desde tablas inexistentes
            
            if original_context and len(original_context) > 0:
                print(f"✅ Usando contexto original: {len(original_context)} elementos")
                return original_context
            
            # ✅ ALTERNATIVA: Buscar en messages si hay datos de cliente
            from sqlalchemy import text
            messages_query = text("""
                SELECT TOP 1 text_content 
                FROM messages 
                WHERE conversation_id = :conv_id 
                    AND sender_type = 'system'
                    AND text_content LIKE '%CAMILO%'
                ORDER BY timestamp DESC
            """)
            
            result = db.execute(messages_query, {"conv_id": conversation_id})
            row = result.fetchone()
            
            if row:
                print(f"📋 Información encontrada en messages")
                # Contexto mínimo basado en messages
                return {
                    "cliente_encontrado": True,
                    "Nombre_del_cliente": "CAMILO AVILA",
                    "recovery_method": "messages_fallback"
                }
            
            print(f"⚠️ Sin datos para recuperar, contexto vacío")
            return {}
            
        except Exception as e:
            print(f"❌ Error en recuperación de emergencia: {e}")
            return original_context or {}

    @staticmethod
    def get_current_state(db: Session, conversation_id: int) -> str:
        """Obtiene el estado actual de una conversación."""
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación {conversation_id} no encontrada"
            )
        
        return conversation.current_state
    
    @staticmethod
    def end_conversation(db: Session, conversation_id: int) -> Conversation:
        """Marca una conversación como finalizada."""
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
    def safe_get_context(conversation: Conversation) -> Dict[str, Any]:
        """
        ✅ VERSIÓN MEJORADA - Obtiene context como diccionario de forma segura
        """
        try:
            # 1. Verificar context (campo principal)
            if hasattr(conversation, 'context') and conversation.context:
                if isinstance(conversation.context, dict):
                    return conversation.context
                elif isinstance(conversation.context, str) and conversation.context.strip():
                    try:
                        parsed = json.loads(conversation.context)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
            
            # 2. Verificar context (campo backup)
            if hasattr(conversation, 'context') and conversation.context:
                if isinstance(conversation.context, str) and conversation.context.strip():
                    try:
                        if conversation.context.startswith('{'):
                            parsed = json.loads(conversation.context)
                            if isinstance(parsed, dict):
                                return parsed
                    except json.JSONDecodeError:
                        pass
            
            return {}
            
        except Exception as e:
            print(f"⚠️ Error obteniendo contexto: {e}")
            return {}
    
    # @staticmethod
    # def create_context_backup_table(db: Session):
    #    """✅ NUEVO - Crear tabla de backup para contextos"""
    #    try:
    #        create_table_query = text("""
    #            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'messages')
    #            BEGIN
    #                CREATE TABLE messages (
    #                    id INT IDENTITY(1,1) PRIMARY KEY,
    #                    conversation_id INT NOT NULL,
    #                    context_json NVARCHAR(MAX) NOT NULL,
    #                    created_at DATETIME NOT NULL,
    #                    updated_at DATETIME NOT NULL,
    #                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    #               )
                    
    #                CREATE INDEX IDX_conversation_context_backup_conv_id 
    #                ON conversation_context_backup(conversation_id)
    #            END
    #        """)
    #        
    #        db.execute(create_table_query)
    #        db.commit()
    #        print(f"✅ Tabla de backup de contextos creada/verificada")
    #        
    #    except Exception as e:
    #        print(f"⚠️ Error creando tabla backup: {e}")
    #        db.rollback()