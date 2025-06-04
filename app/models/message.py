# app/models/messages.py - GENERADO AUTOMÁTICAMENTE
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(String(50), nullable=False)
    text_content = Column(String(-1), nullable=False)
    button_selected = Column(String(255))
    previous_state = Column(String(100))
    next_state = Column(String(100))
    timestamp = Column(DateTime, nullable=False)
    
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        id_field = getattr(self, 'id', 'N/A')
        return f"<Message(id={id_field})>"
