import logging
import sys
import os
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, date

# Configurar logging básico de Python
def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Configuración básica
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log"),
        ]
    )
    
    # Configurar loggers específicos
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return logging.getLogger("app")

# Serializador JSON personalizado para manejar objetos datetime
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Clase para registrar eventos estructurados
class StructuredLogger:
    def __init__(self, logger_name: str = "app"):
        self.logger = logging.getLogger(logger_name)
        
    def _log(self, level: int, message: str, **kwargs):
        # Crear diccionario estructurado con los datos
        log_data = {
            "message": message,
            "timestamp": datetime.now(),
            **kwargs
        }
        
        # Convertir a JSON
        json_data = json.dumps(log_data, cls=CustomJSONEncoder)
        
        # Registrar con el nivel apropiado
        self.logger.log(level, json_data)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

# Instancia global del logger estructurado
logger = StructuredLogger()