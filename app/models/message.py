from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(String(50), nullable=False)  # "user" o "system"
    text_content = Column(Text, nullable=False)
    button_selected = Column(String(255), nullable=True)
    previous_state = Column(String(100), nullable=True)
    next_state = Column(String(100), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # ✅ RELACIÓN CORREGIDA
    conversation = relationship("Conversation", back_populates="messages", lazy="select")
    
    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender='{self.sender_type}')>"