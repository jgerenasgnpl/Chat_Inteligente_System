from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    
    conversations = relationship(
        "Conversation", 
        back_populates="user",
        lazy="select",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        id_field = getattr(self, 'id', 'N/A')
        return f"<User(id={id_field})>"
