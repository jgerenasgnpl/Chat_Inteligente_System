# app/models/conversation.py - VERSIÓN CORREGIDA CON JSON
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import json

class Conversation(Base):
    __tablename__ = "conversations"
    
    # Columnas básicas que existen en la tabla
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_state = Column(String(100), default="inicial")
    is_active = Column(Boolean, default=True)
    
    # Relaciones
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    # ✅ PROPIEDADES MEJORADAS PARA MANEJO DE CONTEXTO
    @property
    def context(self):
        """Context como string JSON"""
        return getattr(self, '_context', None)
    
    @context.setter
    def context(self, value):
        """Context setter que acepta string o dict"""
        if isinstance(value, dict):
            self._context = json.dumps(value, ensure_ascii=False, default=str)
        else:
            self._context = value
    
    @property
    def context_data(self):
        """Context data como diccionario"""
        # Usar cache si existe
        if hasattr(self, '_context_data_cache'):
            return self._context_data_cache
            
        try:
            if hasattr(self, '_context') and self._context:
                self._context_data_cache = json.loads(self._context)
                return self._context_data_cache
        except:
            pass
            
        # Fallback: diccionario vacío
        self._context_data_cache = {}
        return self._context_data_cache
    
    @context_data.setter  
    def context_data(self, value):
        """Context data setter - guarda como JSON"""
        if isinstance(value, dict):
            try:
                self._context = json.dumps(value, ensure_ascii=False, default=str)
                self._context_data_cache = value
            except Exception as e:
                print(f"❌ Error guardando context_data: {e}")
                self._context = "{}"
                self._context_data_cache = {}
        elif isinstance(value, str):
            try:
                # Validar que sea JSON válido
                parsed = json.loads(value)
                self._context = value
                self._context_data_cache = parsed
            except:
                self._context = "{}"
                self._context_data_cache = {}
        else:
            self._context = "{}"
            self._context_data_cache = {}
    
    # Propiedades para compatibilidad con código existente
    @property
    def last_message(self):
        """Último mensaje vacío por defecto"""
        return ""
    
    @last_message.setter
    def last_message(self, value):
        """Setter dummy para compatibilidad"""
        pass
    
    @property
    def response(self):
        """Respuesta vacía por defecto"""
        return ""
    
    @response.setter
    def response(self, value):
        """Setter dummy para compatibilidad"""
        pass
    
    @property
    def title(self):
        """Título por defecto"""
        return f"Conversación {self.id}"
    
    @property
    def created_at(self):
        from datetime import datetime
        return datetime.now()
    
    @property
    def ended_at(self):
        return None
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, state='{self.current_state}')>"
