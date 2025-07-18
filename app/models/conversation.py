from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_state = Column(String(100), default="inicial")
    context_data = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="conversations", lazy="select")
    messages = relationship(
        "Message", 
        back_populates="conversation",
        lazy="select",
        cascade="all, delete-orphan"
    )
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, state='{self.current_state}')>"