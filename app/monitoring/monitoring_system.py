import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor en tiempo real del sistema de 3 capas"""
    
    def __init__(self):
        self.metrics = {
            # Contadores por sistema
            'rule_hits': 0,
            'ml_hits': 0,
            'openai_hits': 0,
            'cache_hits': 0,
            'total_requests': 0,
            'errors': 0,
            
            # Tiempos de respuesta
            'response_times': {
                'rules': deque(maxlen=100),
                'ml': deque(maxlen=100),
                'openai': deque(maxlen=100),
                'total': deque(maxlen=100)
            },
            
            # Tasas de éxito
            'success_rates': {
                'rules': deque(maxlen=100),
                'ml': deque(maxlen=100),
                'openai': deque(maxlen=100)
            },
            
            # Cache statistics
            'cache_stats': {
                'hits': 0,
                'misses': 0,
                'size': 0,
                'evictions': 0
            }
        }
        
        # Alertas
        self.alerts = []
        self.alert_thresholds = {
            'avg_response_time': 2000,  # 2s
            'error_rate': 0.1,          # 10%
            'ml_confidence_drop': 0.5,   # 50%
            'cache_hit_rate': 0.3       # 30%
        }
        
        self.lock = threading.Lock()
        logger.info("✅ SystemMonitor inicializado")
    
    def record_request(self, method: str, response_time_ms: float, 
                      success: bool, confidence: float = 0.0):
        """Registrar una request del sistema"""
        with self.lock:
            self.metrics['total_requests'] += 1
            
            # Incrementar contador por método
            if method == 'REGLA_CRITICA':
                self.metrics['rule_hits'] += 1
                self.metrics['response_times']['rules'].append(response_time_ms)
                self.metrics['success_rates']['rules'].append(1.0 if success else 0.0)
                
            elif method == 'ML':
                self.metrics['ml_hits'] += 1
                self.metrics['response_times']['ml'].append(response_time_ms)
                self.metrics['success_rates']['ml'].append(confidence)
                
            elif method == 'OPENAI':
                self.metrics['openai_hits'] += 1
                self.metrics['response_times']['openai'].append(response_time_ms)
                self.metrics['success_rates']['openai'].append(confidence)
                
            elif method == 'CACHE':
                self.metrics['cache_hits'] += 1
            
            # Error tracking
            if not success:
                self.metrics['errors'] += 1
            
            # Tiempo total
            self.metrics['response_times']['total'].append(response_time_ms)
            
            # Verificar alertas
            self._check_alerts()
    
    def record_cache_event(self, event_type: str):
        """Registrar eventos de cache"""
        with self.lock:
            if event_type == 'hit':
                self.metrics['cache_stats']['hits'] += 1
            elif event_type == 'miss':
                self.metrics['cache_stats']['misses'] += 1
            elif event_type == 'eviction':
                self.metrics['cache_stats']['evictions'] += 1
    
    def update_cache_size(self, size: int):
        """Actualizar tamaño del cache"""
        with self.lock:
            self.metrics['cache_stats']['size'] = size
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtener resumen de métricas"""
        with self.lock:
            total = max(self.metrics['total_requests'], 1)
            
            # Calcular promedios
            avg_times = {}
            for system, times in self.metrics['response_times'].items():
                avg_times[system] = sum(times) / len(times) if times else 0
            
            # Tasas de éxito
            success_rates = {}
            for system, rates in self.metrics['success_rates'].items():
                success_rates[system] = sum(rates) / len(rates) if rates else 0
            
            # Cache hit rate
            cache_total = self.metrics['cache_stats']['hits'] + self.metrics['cache_stats']['misses']
            cache_hit_rate = self.metrics['cache_stats']['hits'] / max(cache_total, 1)
            
            return {
                'summary': {
                    'total_requests': total,
                    'error_rate': self.metrics['errors'] / total,
                    'avg_response_time_ms': avg_times.get('total', 0),
                    'cache_hit_rate': cache_hit_rate
                },
                'system_usage': {
                    'rules': f"{(self.metrics['rule_hits'] / total) * 100:.1f}%",
                    'ml': f"{(self.metrics['ml_hits'] / total) * 100:.1f}%",
                    'openai': f"{(self.metrics['openai_hits'] / total) * 100:.1f}%",
                    'cache': f"{(self.metrics['cache_hits'] / total) * 100:.1f}%"
                },
                'performance': {
                    'avg_response_times_ms': avg_times,
                    'success_rates': success_rates
                },
                'cache': self.metrics['cache_stats'],
                'alerts': self.alerts[-10:],  # Últimas 10 alertas
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_alerts(self):
        """Verificar condiciones de alerta"""
        # Verificar tiempo de respuesta promedio
        if self.metrics['response_times']['total']:
            avg_time = sum(self.metrics['response_times']['total']) / len(self.metrics['response_times']['total'])
            if avg_time > self.alert_thresholds['avg_response_time']:
                self._add_alert('HIGH_RESPONSE_TIME', f'Tiempo promedio: {avg_time:.1f}ms')
        
        # Verificar tasa de error
        if self.metrics['total_requests'] > 10:
            error_rate = self.metrics['errors'] / self.metrics['total_requests']
            if error_rate > self.alert_thresholds['error_rate']:
                self._add_alert('HIGH_ERROR_RATE', f'Tasa de error: {error_rate:.1%}')
        
        # Verificar confianza ML
        if self.metrics['success_rates']['ml']:
            avg_confidence = sum(self.metrics['success_rates']['ml']) / len(self.metrics['success_rates']['ml'])
            if avg_confidence < self.alert_thresholds['ml_confidence_drop']:
                self._add_alert('LOW_ML_CONFIDENCE', f'Confianza ML: {avg_confidence:.2f}')
        
        # Verificar cache hit rate
        cache_total = self.metrics['cache_stats']['hits'] + self.metrics['cache_stats']['misses']
        if cache_total > 20:
            hit_rate = self.metrics['cache_stats']['hits'] / cache_total
            if hit_rate < self.alert_thresholds['cache_hit_rate']:
                self._add_alert('LOW_CACHE_HIT_RATE', f'Cache hit rate: {hit_rate:.1%}')
    
    def _add_alert(self, alert_type: str, message: str):
        """Agregar alerta"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Evitar alertas duplicadas recientes
        recent_alerts = [a for a in self.alerts[-5:] if a['type'] == alert_type]
        if not recent_alerts:
            self.alerts.append(alert)
            logger.warning(f"🚨 ALERTA {alert_type}: {message}")
    
    def reset_metrics(self):
        """Reset de métricas (para testing)"""
        with self.lock:
            self.__init__()

# ==========================================
# MONITOR GLOBAL
# ==========================================

# Instancia global del monitor
system_monitor = SystemMonitor()

# ==========================================
# DECORADOR PARA MONITOREO AUTOMÁTICO
# ==========================================

def monitor_execution(method_name: str = "UNKNOWN"):
    """Decorador para monitorear automáticamente las funciones"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            confidence = 0.0
            
            try:
                result = func(*args, **kwargs)
                
                # Extraer confianza si está en el resultado
                if isinstance(result, dict):
                    confidence = result.get('confianza', result.get('confidence', 0.0))
                
                return result
                
            except Exception as e:
                success = False
                logger.error(f"❌ Error en {func.__name__}: {e}")
                raise
                
            finally:
                execution_time = (time.time() - start_time) * 1000
                system_monitor.record_request(method_name, execution_time, success, confidence)
        
        return wrapper
    return decorator

# ==========================================
# FUNCIONES DE UTILIDAD PARA BD
# ==========================================

def save_metrics_to_db(db: Session, metrics: Dict[str, Any]):
    """Guardar métricas en base de datos"""
    try:
        # Guardar en tabla performance_metrics (si existe)
        query = text("""
            INSERT INTO performance_metrics (
                metric_date, total_requests, error_rate, 
                avg_response_time, cache_hit_rate, 
                rule_usage, ml_usage, openai_usage,
                metric_data
            ) VALUES (
                GETDATE(), :total_requests, :error_rate,
                :avg_response_time, :cache_hit_rate,
                :rule_usage, :ml_usage, :openai_usage,
                :metric_data
            )
        """)
        
        summary = metrics['summary']
        usage = metrics['system_usage']
        
        db.execute(query, {
            'total_requests': summary['total_requests'],
            'error_rate': summary['error_rate'],
            'avg_response_time': summary['avg_response_time_ms'],
            'cache_hit_rate': summary['cache_hit_rate'],
            'rule_usage': float(usage['rules'].strip('%')),
            'ml_usage': float(usage['ml'].strip('%')),
            'openai_usage': float(usage['openai'].strip('%')),
            'metric_data': json.dumps(metrics)
        })
        
        db.commit()
        logger.info("✅ Métricas guardadas en BD")
        
    except Exception as e:
        logger.error(f"❌ Error guardando métricas en BD: {e}")
        db.rollback()

def get_performance_trends(db: Session, days: int = 7) -> Dict[str, Any]:
    """Obtener tendencias de performance"""
    try:
        query = text("""
            SELECT 
                CAST(metric_date AS DATE) as date,
                AVG(avg_response_time) as avg_response_time,
                AVG(error_rate) as error_rate,
                AVG(cache_hit_rate) as cache_hit_rate,
                SUM(total_requests) as total_requests
            FROM performance_metrics 
            WHERE metric_date >= DATEADD(DAY, -:days, GETDATE())
            GROUP BY CAST(metric_date AS DATE)
            ORDER BY date
        """)
        
        results = []
        for row in db.execute(query, {'days': days}):
            results.append({
                'date': row[0].isoformat(),
                'avg_response_time': row[1],
                'error_rate': row[2],
                'cache_hit_rate': row[3],
                'total_requests': row[4]
            })
        
        return {
            'trends': results,
            'period_days': days,
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo tendencias: {e}")
        return {'trends': [], 'error': str(e)}

# ==========================================
# HEALTH CHECK
# ==========================================

def system_health_check(db: Session) -> Dict[str, Any]:
    """Health check completo del sistema"""
    
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {},
        'metrics': system_monitor.get_summary()
    }
    
    try:
        # Check BD
        db.execute(text("SELECT 1"))
        health['components']['database'] = {'status': 'healthy'}
        
        # Check tablas críticas
        tables_to_check = ['conversations', 'Estados_Conversacion', 'datos_entrenamiento']
        for table in tables_to_check:
            count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            health['components'][f'table_{table}'] = {
                'status': 'healthy',
                'count': count
            }
        
        # Check modelos ML
        import os
        models_dir = "models"
        if os.path.exists(models_dir):
            model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib')]
            health['components']['ml_models'] = {
                'status': 'healthy' if model_files else 'warning',
                'count': len(model_files)
            }
        else:
            health['components']['ml_models'] = {'status': 'error', 'message': 'Models directory not found'}
        
        # Check OpenAI
        from app.core.config import settings
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith('sk-'):
            health['components']['openai'] = {'status': 'healthy'}
        else:
            health['components']['openai'] = {'status': 'warning', 'message': 'API key not configured'}
        
    except Exception as e:
        health['status'] = 'error'
        health['error'] = str(e)
        logger.error(f"❌ Error en health check: {e}")
    
    return health

# ==========================================
# EJEMPLO DE USO EN FLOW MANAGER
# ==========================================

"""
# En flow_manager.py, agregar estas líneas:

from app.utils.monitoring import system_monitor, monitor_execution

class OptimizedFlowManager:
    
    @monitor_execution("REGLA_CRITICA")
    def _apply_critical_rules(self, mensaje: str, estado: str, contexto: Dict):
        # ... código existente ...
        
    @monitor_execution("ML")
    def _classify_with_ml(self, mensaje: str, estado: str, contexto: Dict):
        # ... código existente ...
        
    @monitor_execution("OPENAI")
    def _classify_with_openai(self, mensaje: str, estado: str, contexto: Dict):
        # ... código existente ...
"""