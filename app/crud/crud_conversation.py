from sqlalchemy.orm import Session
from typing import Optional
import datetime

from app.models.conversation import Conversation # Asegúrate de que este import sea correcto
from app.schemas.conversation import ConversationCreate, ConversationUpdate # Asegúrate de que estos imports sean correctos
from app.models.user import User # Necesario para relacionar

# Implementación específica para el modelo Conversation
class CRUDConversation:
    def get_active_by_user_id(self, db: Session, *, user_id: str) -> Optional[Conversation]:
        """
        Obtiene la conversación activa para un usuario dado.
        Args:
            db: Sesión de base de datos.
            user_id: ID del usuario (wa_id).
        Returns:
            La conversación activa si existe, None en caso contrario.
        """
        # Busca el usuario primero para asegurar que existe y obtener su ID interno si usas uno
        # O puedes filtrar directamente por wa_id si es la FK en Conversation
        # Asumiendo que Conversation tiene una FK a User usando user.id
        # user_obj = db.query(User).filter(User.wa_id == user_id).first()
        # if not user_obj:
        #     return None
        # return db.query(Conversation).filter(Conversation.user_id == user_obj.id, Conversation.is_active == True).first()

        # Si Conversation tiene una FK directa a User.wa_id (simplificado para este ejemplo)
        return db.query(Conversation).filter(Conversation.user_id == user_id, Conversation.is_active == True).first()


    def create(self, db: Session, *, obj_in: ConversationCreate) -> Conversation:
        """
        Crea una nueva conversación.
        Args:
            db: Sesión de base de datos.
            obj_in: Objeto Pydantic con los datos para crear la conversación.
                    Debería incluir user_id y el estado inicial.
        Returns:
            El objeto Conversation creado.
        """
        db_obj = Conversation(
            user_id=obj_in.user_id,
            start_time=datetime.datetime.now(),
            is_active=True,
            current_state=obj_in.current_state # Estado inicial del pitch
            # Puedes añadir otros campos aquí
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_state(self, db: Session, *, conversation: Conversation, new_state: str) -> Conversation:
        """
        Actualiza el estado actual de una conversación.
        Args:
            db: Sesión de base de datos.
            conversation: Objeto Conversation a actualizar.
            new_state: El nuevo estado (ID del nodo en la KB).
        Returns:
            El objeto Conversation actualizado.
        """
        conversation.current_state = new_state
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    def end_conversation(self, db: Session, *, conversation: Conversation) -> Conversation:
        """
        Marca una conversación como inactiva y establece la hora de finalización.
        Args:
            db: Sesión de base de datos.
            conversation: Objeto Conversation a finalizar.
        Returns:
            El objeto Conversation actualizado.
        """
        conversation.is_active = False
        conversation.end_time = datetime.datetime.now()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    # Podrías añadir un método para obtener el historial de mensajes de una conversación
    # def get_messages(self, db: Session, *, conversation_id: int):
    #     return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp).all()


# Instancia para ser usada en dependencias u otros módulos
conversation = CRUDConversation()