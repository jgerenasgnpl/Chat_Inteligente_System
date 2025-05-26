from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from datetime import datetime, timedelta
import logging

class MonitoringSystem:
    """
    Sistema de monitoreo para el chatbot de cobranza
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def registrar_metrica_conversacion(self, conversation_id: int, metrica: str, valor: float):
        """Registra una métrica de conversación"""
        try:
            query = text("""
                INSERT INTO metricas_conversacion 
                (conversation_id, metrica, valor, timestamp)
                VALUES (:conv_id, :metrica, :valor, GETDATE())
            """)
            
            self.db.execute(query, {
                "conv_id": conversation_id,
                "metrica": metrica,
                "valor": valor
            })
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Error registrando métrica: {e}")
    
    def obtener_metricas_tiempo_real(self) -> Dict:
        """Obtiene métricas en tiempo real del sistema"""
        try:
            # Conversaciones activas
            conversaciones_activas = text("""
                SELECT COUNT(*) FROM conversation 
                WHERE is_active = 1 AND created_at >= DATEADD(hour, -1, GETDATE())
            """)
            
            # Tasa de conversión
            tasa_conversion = text("""
                SELECT 
                    COUNT(CASE WHEN current_state LIKE '%acuerdo%' THEN 1 END) * 100.0 / COUNT(*) as tasa
                FROM conversation 
                WHERE created_at >= DATEADD(day, -1, GETDATE())
            """)
            
            # Intenciones más comunes
            intenciones_comunes = text("""
                SELECT TOP 5 
                    JSON_VALUE(context_data, '$.ultima_intencion') as intencion,
                    COUNT(*) as cantidad
                FROM conversation 
                WHERE context_data IS NOT NULL
                AND created_at >= DATEADD(day, -1, GETDATE())
                GROUP BY JSON_VALUE(context_data, '$.ultima_intencion')
                ORDER BY COUNT(*) DESC
            """)
            
            activas = self.db.execute(conversaciones_activas).scalar() or 0
            conversion = self.db.execute(tasa_conversion).scalar() or 0
            intenciones = self.db.execute(intenciones_comunes).fetchall()
            
            return {
                "conversaciones_activas": activas,
                "tasa_conversion_24h": round(conversion, 2),
                "intenciones_top": [{"intencion": row[0], "cantidad": row[1]} for row in intenciones],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {e}")
            return {"error": str(e)}
    
    def detectar_anomalias(self) -> List[Dict]:
        """Detecta anomalías en el comportamiento del sistema"""
        anomalias = []
        
        try:
            # Detectar picos de errores
            errores_recientes = text("""
                SELECT COUNT(*) FROM message 
                WHERE text_content LIKE '%error%' 
                AND timestamp >= DATEADD(hour, -1, GETDATE())
            """)
            
            errores = self.db.execute(errores_recientes).scalar() or 0
            
            if errores > 10:  # Threshold configurable
                anomalias.append({
                    "tipo": "error_spike",
                    "severidad": "alta",
                    "descripcion": f"Pico de errores detectado: {errores} en la última hora",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Detectar conversaciones estancadas
            conversaciones_estancadas = text("""
                SELECT COUNT(*) FROM conversation 
                WHERE is_active = 1 
                AND created_at < DATEADD(hour, -2, GETDATE())
                AND current_state NOT IN ('fin', 'despedida_final')
            """)
            
            estancadas = self.db.execute(conversaciones_estancadas).scalar() or 0
            
            if estancadas > 5:
                anomalias.append({
                    "tipo": "conversaciones_estancadas",
                    "severidad": "media",
                    "descripcion": f"{estancadas} conversaciones estancadas detectadas",
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            self.logger.error(f"Error detectando anomalías: {e}")
        
        return anomalias
    
    def generar_reporte_rendimiento(self, dias: int = 7) -> Dict:
        """Genera reporte de rendimiento del sistema"""
        try:
            fecha_inicio = datetime.now() - timedelta(days=dias)
            
            # Métricas de volumen
            query_volumen = text("""
                SELECT 
                    COUNT(DISTINCT conversation_id) as total_conversaciones,
                    COUNT(*) as total_mensajes,
                    AVG(CAST(DATEDIFF(minute, c.created_at, COALESCE(c.ended_at, GETDATE())) AS FLOAT)) as duracion_promedio
                FROM message m
                JOIN conversation c ON m.conversation_id = c.id
                WHERE m.timestamp >= :fecha_inicio
            """)
            
            # Métricas de eficiencia
            query_eficiencia = text("""
                SELECT 
                    AVG(CASE WHEN current_state LIKE '%acuerdo%' OR current_state = 'generar_acuerdo' THEN 1.0 ELSE 0.0 END) * 100 as tasa_exito,
                    AVG(CASE WHEN current_state = 'cerrar_sin_pago' THEN 1.0 ELSE 0.0 END) * 100 as tasa_abandono
                FROM conversation 
                WHERE created_at >= :fecha_inicio
            """)
            
            volumen = self.db.execute(query_volumen, {"fecha_inicio": fecha_inicio}).fetchone()
            eficiencia = self.db.execute(query_eficiencia, {"fecha_inicio": fecha_inicio}).fetchone()
            
            return {
                "periodo": f"Últimos {dias} días",
                "volumen": {
                    "conversaciones": volumen[0] if volumen else 0,
                    "mensajes": volumen[1] if volumen else 0,
                    "duracion_promedio_min": round(volumen[2], 2) if volumen and volumen[2] else 0
                },
                "eficiencia": {
                    "tasa_exito": round(eficiencia[0], 2) if eficiencia and eficiencia[0] else 0,
                    "tasa_abandono": round(eficiencia[1], 2) if eficiencia and eficiencia[1] else 0
                },
                "generado_en": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generando reporte: {e}")
            return {"error": str(e)}

# Clase para métricas ML
class MLMetrics:
    """Métricas específicas para el sistema ML"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def registrar_prediccion_ml(self, mensaje: str, intencion_predicha: str, confianza: float, conversation_id: int):
        """Registra una predicción del modelo ML"""
        try:
            query = text("""
                INSERT INTO predicciones_ml 
                (conversation_id, mensaje, intencion_predicha, confianza, timestamp)
                VALUES (:conv_id, :mensaje, :intencion, :confianza, GETDATE())
            """)
            
            self.db.execute(query, {
                "conv_id": conversation_id,
                "mensaje": mensaje[:500],  # Truncar mensaje largo
                "intencion": intencion_predicha,
                "confianza": confianza
            })
            self.db.commit()
            
        except Exception as e:
            print(f"Error registrando predicción ML: {e}")
    
    def obtener_accuracy_ml(self, dias: int = 7) -> float:
        """Calcula la accuracy del modelo ML basada en feedback"""
        try:
            query = text("""
                SELECT 
                    AVG(CASE WHEN feedback_correcto = 1 THEN 1.0 ELSE 0.0 END) * 100 as accuracy
                FROM predicciones_ml 
                WHERE timestamp >= DATEADD(day, -:dias, GETDATE())
                AND feedback_correcto IS NOT NULL
            """)
            
            result = self.db.execute(query, {"dias": dias}).scalar()
            return round(result, 2) if result else 0.0
            
        except Exception as e:
            print(f"Error calculando accuracy ML: {e}")
            return 0.0