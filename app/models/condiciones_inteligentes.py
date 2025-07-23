from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.dialects.mssql import JSON
from app.db.base import Base
from datetime import datetime

class CondicionesInteligentes(Base):
    __tablename__ = "Condiciones_Inteligentes"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), unique=True, nullable=False)
    tipo_condicion = Column(String(50), nullable=False)
    configuracion_json = Column(JSON, nullable=False)
    confianza_minima = Column(String(10), nullable=True)
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado_actual = Column(String(100), nullable=True)
    estado_siguiente_true = Column(String(100), nullable=True)
    estado_siguiente_false = Column(String(100), nullable=True)
    estado_siguiente_default = Column(String(100), nullable=True)