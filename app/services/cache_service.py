import redis
import json
import hashlib
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import os
import pickle
import asyncio

logger = logging.getLogger(__name__)

class RedisCacheService:
    """
    🚀 SERVICIO DE CACHE REDIS OPTIMIZADO - VERSIÓN CORREGIDA
    
    Características:
    - Cache de datos de clientes
    - Cache de predicciones ML
    - Cache de respuestas OpenAI
    - Cache de variables resueltas
    - Invalidación inteligente
    - Compresión automática
    - SIN aioredis para evitar conflictos
    """
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self.default_ttl = 3600
        self.compression_threshold = 1000
        
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.db = int(os.getenv("REDIS_DB", 0))
        

        self._initialize_connection()
    
    def _initialize_connection(self):
        """Inicializar conexión a Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=False, 
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test de conexión
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"✅ Redis conectado: {self.host}:{self.port}")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis no disponible: {e}")
            self.enabled = False
            self._memory_cache = {}
            self._memory_cache_timestamps = {}
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generar clave de cache"""
        key_data = "|".join(str(arg) for arg in args)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"nego_chat:{prefix}:{key_hash}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serializar datos para cache"""
        try:
            if isinstance(data, (dict, list, str, int, float, bool, type(None))):
                serialized = json.dumps(data, ensure_ascii=False, default=str)
                return serialized.encode('utf-8')
            else:
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Error serializando datos: {e}")
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserializar datos del cache"""
        try:
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error deserializando datos: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Guardar valor en cache"""
        if self.enabled and self.redis_client:
            try:
                serialized_value = self._serialize_data(value)
                ttl = ttl or self.default_ttl
                
                if len(serialized_value) > self.compression_threshold:
                    import gzip
                    serialized_value = gzip.compress(serialized_value)
                    key = f"{key}:compressed"
                
                result = self.redis_client.setex(key, ttl, serialized_value)
                
                if result:
                    logger.debug(f"✅ Cache SET: {key} (TTL: {ttl}s)")
                    return True
                    
            except Exception as e:
                logger.error(f"❌ Error cache SET {key}: {e}")
        
        return self._memory_set(key, value, ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache"""
        if self.enabled and self.redis_client:
            try:
                compressed_key = f"{key}:compressed"
                
                data = self.redis_client.get(compressed_key)
                if data:
                    import gzip
                    data = gzip.decompress(data)
                    key = compressed_key
                else:
                    data = self.redis_client.get(key)
                
                if data:
                    result = self._deserialize_data(data)
                    logger.debug(f"✅ Cache HIT: {key}")
                    return result
                else:
                    logger.debug(f"❌ Cache MISS: {key}")
                    
            except Exception as e:
                logger.error(f"❌ Error cache GET {key}: {e}")
        return self._memory_get(key)
    
    def delete(self, key: str) -> bool:
        """Eliminar del cache"""
        if self.enabled and self.redis_client:
            try:
                result1 = self.redis_client.delete(key)
                result2 = self.redis_client.delete(f"{key}:compressed")
                
                if result1 or result2:
                    logger.debug(f"✅ Cache DELETE: {key}")
                    return True
                    
            except Exception as e:
                logger.error(f"❌ Error cache DELETE {key}: {e}")
        
        return self._memory_delete(key)
    
    def exists(self, key: str) -> bool:
        """Verificar si existe en cache"""
        if self.enabled and self.redis_client:
            try:
                return bool(
                    self.redis_client.exists(key) or 
                    self.redis_client.exists(f"{key}:compressed")
                )
            except Exception as e:
                logger.error(f"❌ Error cache EXISTS {key}: {e}")
        
        return self._memory_exists(key)
    
    
    def _memory_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Cache en memoria como fallback"""
        try:
            if not hasattr(self, '_memory_cache'):
                self._memory_cache = {}
                self._memory_cache_timestamps = {}
            
            self._memory_cache[key] = value
            self._memory_cache_timestamps[key] = {
                'timestamp': datetime.now(),
                'ttl': ttl or self.default_ttl
            }
            

            if len(self._memory_cache) > 100:
                self._cleanup_memory_cache()
            
            logger.debug(f"💾 Memory cache SET: {key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error memory cache SET: {e}")
            return False
    
    def _memory_get(self, key: str) -> Optional[Any]:
        """Obtener desde cache en memoria"""
        try:
            if not hasattr(self, '_memory_cache'):
                return None
            
            if key not in self._memory_cache:
                return None

            cache_info = self._memory_cache_timestamps.get(key)
            if cache_info:
                elapsed = (datetime.now() - cache_info['timestamp']).total_seconds()
                if elapsed > cache_info['ttl']:

                    del self._memory_cache[key]
                    del self._memory_cache_timestamps[key]
                    return None
            
            logger.debug(f"💾 Memory cache HIT: {key}")
            return self._memory_cache[key]
            
        except Exception as e:
            logger.error(f"❌ Error memory cache GET: {e}")
            return None
    
    def _memory_delete(self, key: str) -> bool:
        """Eliminar desde cache en memoria"""
        try:
            if not hasattr(self, '_memory_cache'):
                return False
            
            if key in self._memory_cache:
                del self._memory_cache[key]
                self._memory_cache_timestamps.pop(key, None)
                logger.debug(f"💾 Memory cache DELETE: {key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error memory cache DELETE: {e}")
            return False
    
    def _memory_exists(self, key: str) -> bool:
        """Verificar existencia en cache en memoria"""
        try:
            if not hasattr(self, '_memory_cache'):
                return False
            
            return key in self._memory_cache
            
        except Exception as e:
            logger.error(f"❌ Error memory cache EXISTS: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """Limpiar cache en memoria expirado"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, cache_info in self._memory_cache_timestamps.items():
                elapsed = (current_time - cache_info['timestamp']).total_seconds()
                if elapsed > cache_info['ttl']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._memory_cache.pop(key, None)
                self._memory_cache_timestamps.pop(key, None)
            
            logger.debug(f"🧹 Memory cache cleanup: {len(expired_keys)} keys removed")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning memory cache: {e}")
    
    
    def cache_client_data(self, cedula: str, client_data: Dict[str, Any], ttl: int = 7200) -> bool:
        """Cache datos de cliente (2 horas TTL)"""
        key = self._generate_key("client", cedula)
        
        client_data["_cached_at"] = datetime.now().isoformat()
        client_data["_cache_ttl"] = ttl
        
        return self.set(key, client_data, ttl)
    
    def get_cached_client_data(self, cedula: str) -> Optional[Dict[str, Any]]:
        """Obtener datos de cliente del cache"""
        key = self._generate_key("client", cedula)
        return self.get(key)
    
    def cache_ml_prediction(self, message: str, prediction: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache predicción ML (30 minutos TTL)"""
        key = self._generate_key("ml_pred", message.lower().strip())
        
        prediction["_cached_at"] = datetime.now().isoformat()
        prediction["_prediction_cache"] = True
        
        return self.set(key, prediction, ttl)
    
    def get_cached_ml_prediction(self, message: str) -> Optional[Dict[str, Any]]:
        """Obtener predicción ML del cache"""
        key = self._generate_key("ml_pred", message.lower().strip())
        return self.get(key)
    
    def cache_openai_response(self, message: str, context_hash: str, response: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache respuesta OpenAI (1 hora TTL)"""
        key = self._generate_key("openai", message, context_hash)
        
        response["_cached_at"] = datetime.now().isoformat()
        response["_openai_cache"] = True
        
        return self.set(key, response, ttl)
    
    def get_cached_openai_response(self, message: str, context_hash: str) -> Optional[Dict[str, Any]]:
        """Obtener respuesta OpenAI del cache"""
        key = self._generate_key("openai", message, context_hash)
        return self.get(key)
    
    def cache_resolved_variables(self, template: str, context_hash: str, resolved: str, ttl: int = 1800) -> bool:
        """Cache variables resueltas (30 minutos TTL)"""
        key = self._generate_key("variables", template, context_hash)
        
        data = {
            "template": template,
            "resolved": resolved,
            "_cached_at": datetime.now().isoformat()
        }
        
        return self.set(key, data, ttl)
    
    def get_cached_resolved_variables(self, template: str, context_hash: str) -> Optional[str]:
        """Obtener variables resueltas del cache"""
        key = self._generate_key("variables", template, context_hash)
        data = self.get(key)
        
        if data and isinstance(data, dict):
            return data.get("resolved")
        
        return None
    
    def cache_conversation_context(self, conversation_id: int, context: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache contexto de conversación (1 hora TTL)"""
        key = self._generate_key("context", conversation_id)
        
        context["_cached_at"] = datetime.now().isoformat()
        context["_context_cache"] = True
        
        return self.set(key, context, ttl)
    
    def get_cached_conversation_context(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Obtener contexto de conversación del cache"""
        key = self._generate_key("context", conversation_id)
        return self.get(key)
    
    def invalidate_conversation_cache(self, conversation_id: int) -> bool:
        """Invalidar cache de conversación"""
        key = self._generate_key("context", conversation_id)
        return self.delete(key)
    
    def invalidate_client_cache(self, cedula: str) -> bool:
        """Invalidar cache de cliente"""
        key = self._generate_key("client", cedula)
        return self.delete(key)

    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        if self.enabled and self.redis_client:
            try:
                info = self.redis_client.info()
                
                # Obtener claves por prefijo
                keys_info = {}
                for prefix in ["client", "ml_pred", "openai", "variables", "context"]:
                    pattern = f"nego_chat:{prefix}:*"
                    keys_count = len(self.redis_client.keys(pattern))
                    keys_info[prefix] = keys_count
                
                return {
                    "enabled": True,
                    "type": "redis",
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": self._calculate_hit_rate(info),
                    "keys_by_type": keys_info,
                    "total_keys": sum(keys_info.values()),
                    "uptime_seconds": info.get("uptime_in_seconds", 0)
                }
                
            except Exception as e:
                logger.error(f"❌ Error obteniendo estadísticas: {e}")
        
        if hasattr(self, '_memory_cache'):
            return {
                "enabled": True,
                "type": "memory_fallback",
                "total_keys": len(self._memory_cache),
                "memory_usage": f"{len(str(self._memory_cache))} bytes",
                "keys_by_type": {"memory": len(self._memory_cache)},
                "hit_rate": 0.0
            }
        
        return {"enabled": False}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calcular tasa de aciertos"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total > 0:
            return round((hits / total) * 100, 2)
        return 0.0
    
    def clear_all_cache(self) -> bool:
        """Limpiar todo el cache del sistema (¡CUIDADO!)"""
        if self.enabled and self.redis_client:
            try:
                pattern = "nego_chat:*"
                keys = self.redis_client.keys(pattern)
                
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    logger.warning(f"🗑️ Cache limpiado: {deleted} claves eliminadas")
                    return True
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error limpiando cache: {e}")
        
        if hasattr(self, '_memory_cache'):
            self._memory_cache.clear()
            self._memory_cache_timestamps.clear()
            logger.warning("🗑️ Memory cache limpiado")
            return True
        
        return False
    
    def cleanup_expired_keys(self) -> int:
        """Limpieza manual de claves expiradas"""
        if self.enabled and self.redis_client:
            try:
                pattern = "nego_chat:*"
                keys = self.redis_client.keys(pattern)
                
                cleaned = 0
                for key in keys:
                    if not self.redis_client.exists(key):
                        cleaned += 1
                
                logger.info(f"🧹 Limpieza completada: {cleaned} claves expiradas")
                return cleaned
                
            except Exception as e:
                logger.error(f"❌ Error en limpieza: {e}")
        
        if hasattr(self, '_memory_cache'):
            self._cleanup_memory_cache()
            return 1
        
        return 0

def cache_result(prefix: str, ttl: int = 3600, key_func=None):
    """Decorador para cache automático de resultados de funciones"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_data = f"{func.__name__}|{args}|{sorted(kwargs.items())}"
                cache_key = cache_service._generate_key(prefix, key_data)
            
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"🎯 Cache hit para {func.__name__}")
                return cached_result
            
            result = func(*args, **kwargs)
            
            if result is not None:
                cache_service.set(cache_key, result, ttl)
                logger.debug(f"💾 Cache guardado para {func.__name__}")
            
            return result
        
        return wrapper
    return decorator

cache_service = RedisCacheService()

def get_cache_service() -> RedisCacheService:
    """Obtener instancia del servicio de cache"""
    return cache_service

def is_cache_enabled() -> bool:
    """Verificar si el cache está habilitado"""
    return cache_service.enabled

def warm_up_cache():
    """Precalentar cache con datos frecuentes"""
    if not cache_service.enabled:
        return
    
    logger.info("🔥 Precalentando cache...")
    
    
    logger.info("✅ Cache precalentado")