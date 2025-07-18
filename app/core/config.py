from pydantic_settings import BaseSettings
from typing import Optional
import os
from pydantic import validator

class Settings(BaseSettings):
    """
    ✅ CONFIGURACIÓN CORREGIDA - Acepta todas las variables nuevas
    """
    PROJECT_NAME: str = "NegotiationChat"
    API_V1_STR: str = "/api/v1"
    
    # ===== VARIABLES EXISTENTES =====
    SECRET_KEY: str = "your-secret-key-here-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    
    # ===== BASE DE DATOS =====
    SQLSERVER_SERVER: str = "172.18.79.20,1433"
    SQLSERVER_DB: str = "turnosvirtuales_dev"
    DATABASE_URL: Optional[str] = None
    
    # ===== MACHINE LEARNING =====
    ML_MODEL_PATH: str = "models/"
    ML_CONFIDENCE_THRESHOLD: float = 0.7
    ML_AUTO_RETRAIN: bool = True
    ML_ENABLE_HYBRID_DETECTION: bool = True
    ML_SAVE_INTERACTIONS: bool = True
    ML_AUTO_IMPROVE: bool = True
    
    # ===== OPENAI CONFIGURATION =====
    OPENAI_API_KEY: str = "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"
    ENABLE_OPENAI: bool = True
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_MAX_TOKENS: int = 400
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_CONFIDENCE_THRESHOLD: float = 0.8
    OPENAI_ONLY_FOR_COMPLEX: bool = True  

    # ====== SISTEMA REGLAS (Críticas y Fallback) ======
    RULES_ENABLED: bool = True
    RULES_PRIORITY_MODE: bool = True  
    
    # ===== LOGGING =====
    LOG_LEVEL: str = "INFO"

    # ===== JERARQUÍA Y PERFORMANCE =====

    TIMEOUT_RULES: int = 10      
    TIMEOUT_ML: int = 100 
    TIMEOUT_OPENAI: int = 5000 
    
    # Umbrales de confianza
    CONFIDENCE_CRITICAL: float = 1.0 
    CONFIDENCE_HIGH: float = 0.8  
    CONFIDENCE_MEDIUM: float = 0.6  
    CONFIDENCE_LOW: float = 0.4     
    
    # Control de escalamiento
    USE_OPENAI_WHEN_ML_FAILS: bool = True
    USE_RULES_WHEN_ALL_FAIL: bool = True
    MAX_RETRIES_PER_SYSTEM: int = 1
    
    # ===== LOGGING Y DEBUGGING =====
    LOG_LEVEL: str = "INFO"
    LOG_PERFORMANCE_METRICS: bool = True
    LOG_CACHE_STATISTICS: bool = True
    LOG_SYSTEM_DECISIONS: bool = True
    DEBUG_MODE: bool = False
    
    ML_ENABLE_HYBRID_DETECTION: bool = True
    ML_SAVE_INTERACTIONS: bool = True
    ML_AUTO_IMPROVE: bool = True
    
    # ===== CARACTERÍSTICAS DEL SISTEMA =====
    COMPANY_NAME: str = "Systemgroup"
    COMPANY_PHONE: str = "+57 3214929276"
    COMPANY_EMAIL: str = "j.gerena@sgnpl.com"
    
    # ===== CONFIGURACIÓN DEL CHAT =====
    CHAT_ENABLE_AI_HUMANIZATION: bool = True
    CHAT_ENABLE_EMPATHY_MODE: bool = True
    CHAT_MAX_CONTEXT_SIZE: int = 100
    
    class Config:
        # ✅ IMPORTANTE: Permitir variables adicionales
        extra = "allow"  # Esto permite variables adicionales sin error
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Crear instancia global
settings = Settings()

# ===== VALIDACIONES Y CONFIGURACIONES ADICIONALES =====

def validate_settings():
    """Validar configuraciones críticas"""
    
    # Validar OpenAI
    if settings.OPENAI_API_KEY:
        print(f"✅ OpenAI configurado: {settings.OPENAI_API_KEY[:20]}...")
    else:
        print("⚠️ OpenAI no configurado")
    
    # Validar BD
    if settings.SQLSERVER_SERVER and settings.SQLSERVER_DB:
        print(f"✅ Base de datos: {settings.SQLSERVER_SERVER}/{settings.SQLSERVER_DB}")
    else:
        print("⚠️ Base de datos no configurada completamente")
    
    return True

# Ejecutar validaciones al importar
try:
    validate_settings()
except Exception as e:
    print(f"⚠️ Error en validación de configuración: {e}")

# ===== UTILIDADES =====
def get_database_url():
    """Generar URL de base de datos"""
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # Construir URL por defecto
    return f"mssql+pyodbc:///?odbc_connect=DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={settings.SQLSERVER_SERVER};DATABASE={settings.SQLSERVER_DB};Trusted_Connection=yes"

def is_openai_enabled():
    """Verificar si OpenAI está habilitado"""
    return bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 20)