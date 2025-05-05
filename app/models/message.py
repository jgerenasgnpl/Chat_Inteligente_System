from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(String, nullable=False)  # "user" o "system"
    text_content = Column(Text, nullable=False)
    button_selected = Column(String, nullable=True)  # Si el mensaje fue generado por botón
    previous_state = Column(String, nullable=True)
    next_state = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    conversation = relationship("Conversation", back_populates="messages")