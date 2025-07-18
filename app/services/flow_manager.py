"""
FLOW_MANAGER.PY COMPLETAMENTE CORREGIDO
- Elimina código hardcodeado problemático
- Sin dependencias de tablas que no existen
- Compatible con el nuevo chat.py
- Funciona solo como fallback si es necesario
"""

import json
import re
import logging
import time
import os
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import hashlib
from decimal import Decimal

logger = logging.getLogger(__name__)

class CurrencyFormatter:
    """Formateador de moneda simple y efectivo"""
    
    def format_cop(self, amount):
        """Formatear como pesos colombianos"""
        if amount is None:
            return "$0"
        
        try:
            if isinstance(amount, str):
                import re
                clean_amount = re.sub(r'[^\d.,]', '', amount)
                if not clean_amount:
                    return "$0"
                
                # Manejar diferentes formatos
                if ',' in clean_amount and '.' in clean_amount:
                    parts = clean_amount.split(',')
                    if len(parts) == 2 and len(parts[1]) <= 2:
                        integer_part = parts[0].replace('.', '')
                        decimal_part = parts[1]
                        clean_amount = f"{integer_part}.{decimal_part}"
                    else:
                        clean_amount = clean_amount.replace(',', '')
                elif ',' in clean_amount:
                    parts = clean_amount.split(',')
                    if len(parts) == 2 and len(parts[1]) <= 2:
                        clean_amount = clean_amount.replace(',', '.')
                    else:
                        clean_amount = clean_amount.replace(',', '')
                
                amount = float(clean_amount)
            
            amount = float(amount)
            
            if amount >= 1000:
                formatted = f"${amount:,.0f}".replace(',', '.')
            else:
                formatted = f"${amount:.0f}"
            
            return formatted
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error formateando moneda {amount}: {e}")
            return "$0"

class SimplifiedFlowManager:
    """
    ✅ FLOW MANAGER SIMPLIFICADO Y CORREGIDO
    - Sin dependencias problemáticas
    - Solo funcionalidad esencial
    - Compatible con chat.py corregido
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.currency_formatter = CurrencyFormatter()
        self.ml_service = self._init_ml_service()
        
        # Cache simple
        self.cache = {}
        self.cache_ttl = {}
        self.cache_max_size = 100
        
        # Métricas básicas
        self.metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'ml_hits': 0,
            'fallback_hits': 0
        }
        
        logger.info("✅ SimplifiedFlowManager inicializado")
    
    def _init_ml_service(self):
        """Inicializar ML de forma segura"""
        try:
            from app.services.nlp_service import nlp_service
            return nlp_service
        except Exception as e:
            logger.warning(f"ML no disponible: {e}")
            return None
    
    def process_user_message(self, conversation_id: int, user_message: str, 
                            current_state: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ MÉTODO PRINCIPAL SIMPLIFICADO
        Solo procesa si chat.py lo requiere como fallback
        """
        try:
            self.metrics['total_requests'] += 1
            
            logger.info(f"🔄 FlowManager fallback para: '{user_message[:30]}...'")
            
            # 1. DETECCIÓN DE CÉDULA (PRIORIDAD MÁXIMA)
            cedula = self._detect_cedula_simple(user_message)
            if cedula:
                return self._process_cedula_fallback(cedula, context)
            
            # 2. ML FALLBACK
            if self.ml_service:
                ml_result = self._classify_ml_fallback(user_message, context, current_state)
                if ml_result.get('confidence', 0) >= 0.6:
                    return ml_result
            
            # 3. REGLAS SIMPLES
            return self._apply_simple_rules_fallback(user_message, current_state, context)
            
        except Exception as e:
            logger.error(f"❌ Error en FlowManager: {e}")
            return self._error_fallback(current_state, context)
    
    def _detect_cedula_simple(self, mensaje: str) -> Optional[str]:
        """Detección simple de cédula"""
        patterns = [
            r'\b(\d{7,12})\b',
            r'cedula\s*:?\s*(\d{7,12})',
            r'documento\s*:?\s*(\d{7,12})',
            r'cc\s*:?\s*(\d{7,12})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, mensaje, re.IGNORECASE)
            for match in matches:
                if 7 <= len(match) <= 12 and len(set(match)) > 1:
                    return match
        return None
    
    def _process_cedula_fallback(self, cedula: str, context: Dict) -> Dict[str, Any]:
        """Procesar cédula como fallback"""
        try:
            logger.info(f"🎯 FlowManager: procesando cédula {cedula}")
            
            # Consulta básica
            cliente_data = self._query_client_fallback(cedula)
            
            if cliente_data.get('encontrado'):
                return {
                    'message': f"Cliente {cliente_data['nombre']} encontrado. Saldo: {self.currency_formatter.format_cop(cliente_data['saldo'])}",
                    'next_state': 'informar_deuda',
                    'context': {**context, **cliente_data},
                    'buttons': [
                        {'id': 'ver_opciones', 'texto': 'Ver opciones'},
                        {'id': 'mas_info', 'texto': 'Más información'}
                    ],
                    'exito': True,
                    'metodo': 'flowmanager_cedula_fallback'
                }
            else:
                return {
                    'message': f'No encontré información para la cédula {cedula}.',
                    'next_state': 'cliente_no_encontrado',
                    'context': context,
                    'buttons': [{'id': 'retry', 'texto': 'Intentar de nuevo'}],
                    'exito': False,
                    'metodo': 'flowmanager_cedula_fallback'
                }
                
        except Exception as e:
            logger.error(f"❌ Error procesando cédula: {e}")
            return self._error_fallback('validar_documento', context)
    
    def _query_client_fallback(self, cedula: str) -> Dict[str, Any]:
        """Consulta básica de cliente"""
        try:
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Saldo_total, banco
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                return {
                    'encontrado': True,
                    'nombre': result[0] or "Cliente",
                    'saldo': int(float(result[1])) if result[1] else 0,
                    'banco': result[2] or "Entidad",
                    'cliente_encontrado': True,
                    'cedula_detectada': cedula
                }
            
            return {'encontrado': False}
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente: {e}")
            return {'encontrado': False}
    
    def _classify_ml_fallback(self, mensaje: str, context: Dict, estado: str) -> Dict[str, Any]:
        """Clasificación ML como fallback"""
        try:
            ml_result = self.ml_service.predict(mensaje)
            intencion = ml_result.get('intention', 'DESCONOCIDA')
            confianza = ml_result.get('confidence', 0.0)
            
            logger.info(f"🤖 FlowManager ML: {intencion} ({confianza:.2f})")
            
            if confianza >= 0.6:
                next_state = self._map_intention_fallback(intencion, estado, context)
                message = self._generate_message_fallback(intencion, context, estado)
                
                return {
                    'message': message,
                    'next_state': next_state,
                    'context': context,
                    'buttons': self._get_buttons_fallback(next_state, context),
                    'exito': True,
                    'confianza': confianza,
                    'intencion_detectada': intencion,
                    'metodo': 'flowmanager_ml_fallback'
                }
            
            return {'confidence': confianza}
            
        except Exception as e:
            logger.error(f"❌ Error en ML fallback: {e}")
            return {'confidence': 0.0}
    
    def _map_intention_fallback(self, intencion: str, estado: str, context: Dict) -> str:
        """Mapeo simple de intención a estado"""
        tiene_cliente = context.get('cliente_encontrado', False)
        
        mapeo = {
            'IDENTIFICACION': 'validar_documento',
            'CONSULTA_DEUDA': 'informar_deuda' if tiene_cliente else 'validar_documento',
            'INTENCION_PAGO': 'proponer_planes_pago' if tiene_cliente else 'validar_documento',
            'CONFIRMACION': 'proponer_planes_pago' if estado == 'informar_deuda' else 'generar_acuerdo',
            'RECHAZO': 'gestionar_objecion',
            'SALUDO': estado if tiene_cliente else 'validar_documento'
        }
        
        return mapeo.get(intencion, estado)
    
    def _generate_message_fallback(self, intencion: str, context: Dict, estado: str) -> str:
        """Generar mensaje simple según intención"""
        nombre = context.get('Nombre_del_cliente', 'Cliente')
        tiene_cliente = context.get('cliente_encontrado', False)
        
        if intencion == 'SALUDO':
            if tiene_cliente:
                return f"¡Hola {nombre}! ¿En qué puedo ayudarte?"
            else:
                return "¡Hola! Para ayudarte, necesito tu cédula."
        
        elif intencion == 'CONSULTA_DEUDA':
            if tiene_cliente:
                saldo = context.get('saldo_total', 0)
                return f"Tu saldo actual es {self.currency_formatter.format_cop(saldo)}, {nombre}."
            else:
                return "Para consultar tu deuda, necesito tu cédula."
        
        elif intencion == 'INTENCION_PAGO':
            if tiene_cliente:
                return f"Perfecto {nombre}, te muestro las opciones de pago."
            else:
                return "Para ver opciones de pago, necesito tu cédula."
        
        elif intencion == 'CONFIRMACION':
            return f"Excelente {nombre}, procedo con tu solicitud."
        
        elif intencion == 'RECHAZO':
            return f"Entiendo {nombre}, ¿hay algo que te preocupe?"
        
        return f"¿En qué puedo ayudarte{', ' + nombre if tiene_cliente else ''}?"
    
    def _apply_simple_rules_fallback(self, mensaje: str, estado: str, context: Dict) -> Dict[str, Any]:
        """Reglas simples como último fallback"""
        mensaje_lower = mensaje.lower()
        tiene_cliente = context.get('cliente_encontrado', False)
        nombre = context.get('Nombre_del_cliente', 'Cliente')
        
        logger.info(f"🔧 Aplicando reglas fallback simples")
        
        # Confirmaciones
        if any(word in mensaje_lower for word in ['si', 'sí', 'acepto', 'ok']):
            if tiene_cliente and estado == 'informar_deuda':
                return {
                    'message': f"Perfecto {nombre}, te muestro las opciones de pago disponibles.",
                    'next_state': 'proponer_planes_pago',
                    'context': context,
                    'buttons': [
                        {'id': 'pago_unico', 'texto': 'Pago único'},
                        {'id': 'cuotas', 'texto': 'Plan cuotas'}
                    ],
                    'exito': True,
                    'metodo': 'flowmanager_reglas_fallback'
                }
        
        # Rechazos
        elif any(word in mensaje_lower for word in ['no', 'imposible', 'no puedo']):
            return {
                'message': f"Entiendo {nombre if tiene_cliente else ''}. ¿Hay algo específico que te preocupa?",
                'next_state': 'gestionar_objecion',
                'context': context,
                'buttons': [
                    {'id': 'plan_flexible', 'texto': 'Plan flexible'},
                    {'id': 'asesor', 'texto': 'Hablar con asesor'}
                ],
                'exito': True,
                'metodo': 'flowmanager_reglas_fallback'
            }
        
        # Solicitud de información
        elif any(word in mensaje_lower for word in ['opciones', 'planes', 'información']):
            if tiene_cliente:
                return {
                    'message': f"Claro {nombre}, te explico las opciones disponibles para ti.",
                    'next_state': 'proponer_planes_pago',
                    'context': context,
                    'buttons': [
                        {'id': 'ver_todas', 'texto': 'Ver todas las opciones'},
                        {'id': 'asesor', 'texto': 'Hablar con asesor'}
                    ],
                    'exito': True,
                    'metodo': 'flowmanager_reglas_fallback'
                }
        
        # Fallback genérico
        if tiene_cliente:
            return {
                'message': f"No estoy seguro de entender, {nombre}. ¿Podrías ser más específico?",
                'next_state': estado,
                'context': context,
                'buttons': [
                    {'id': 'opciones', 'texto': 'Ver opciones'},
                    {'id': 'asesor', 'texto': 'Hablar con asesor'}
                ],
                'exito': True,
                'metodo': 'flowmanager_fallback_generico'
            }
        else:
            return {
                'message': "Para ayudarte mejor, necesito tu número de cédula.",
                'next_state': 'validar_documento',
                'context': context,
                'buttons': [
                    {'id': 'proporcionar_cedula', 'texto': 'Proporcionar cédula'}
                ],
                'exito': True,
                'metodo': 'flowmanager_fallback_generico'
            }
    
    def _get_buttons_fallback(self, estado: str, context: Dict) -> List[Dict[str, str]]:
        """Botones simples para fallback"""
        tiene_cliente = context.get('cliente_encontrado', False)
        
        if estado == 'informar_deuda' and tiene_cliente:
            return [
                {'id': 'ver_opciones', 'texto': 'Ver opciones'},
                {'id': 'mas_info', 'texto': 'Más información'}
            ]
        elif estado == 'proponer_planes_pago' and tiene_cliente:
            return [
                {'id': 'pago_unico', 'texto': 'Pago único'},
                {'id': 'cuotas', 'texto': 'Plan cuotas'},
                {'id': 'asesor', 'texto': 'Hablar con asesor'}
            ]
        elif estado == 'gestionar_objecion':
            return [
                {'id': 'plan_flexible', 'texto': 'Plan flexible'},
                {'id': 'asesor', 'texto': 'Hablar con asesor'}
            ]
        
        return [{'id': 'ayuda', 'texto': 'Necesito ayuda'}]
    
    def _error_fallback(self, estado: str, context: Dict) -> Dict[str, Any]:
        """Respuesta de error para fallback"""
        return {
            'message': 'Hubo un problema técnico. ¿Podrías intentar de nuevo?',
            'next_state': 'inicial',
            'context': context,
            'buttons': [{'id': 'reiniciar', 'texto': 'Reiniciar'}],
            'exito': False,
            'metodo': 'flowmanager_error_fallback'
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtener métricas básicas"""
        total = max(self.metrics['total_requests'], 1)
        
        return {
            'total_requests': total,
            'cache_hit_rate': f"{(self.metrics['cache_hits'] / total) * 100:.1f}%",
            'ml_usage': f"{(self.metrics['ml_hits'] / total) * 100:.1f}%",
            'fallback_usage': f"{(self.metrics['fallback_hits'] / total) * 100:.1f}%",
            'ml_available': self.ml_service is not None,
            'status': 'simplified_fallback_only'
        }


def create_optimized_flow_manager(db: Session) -> SimplifiedFlowManager:
    """Factory para crear flow manager simplificado"""
    return SimplifiedFlowManager(db)


# ==========================================
# COMPATIBILIDAD CON VERSIÓN ANTERIOR
# ==========================================

class OptimizedFlowManager(SimplifiedFlowManager):
    """Alias para compatibilidad"""
    pass


def crear_flow_manager_optimizado(db: Session) -> SimplifiedFlowManager:
    """Alias para compatibilidad"""
    return SimplifiedFlowManager(db)


if __name__ == "__main__":
    print("""
    ✅ FLOW MANAGER SIMPLIFICADO CARGADO
    
    Características:
    - ✅ Sin código hardcodeado problemático
    - ✅ Sin dependencias de tablas que no existen
    - ✅ Solo funciona como fallback
    - ✅ Compatible con chat.py corregido
    - ✅ ML opcional
    - ✅ Reglas simples efectivas
    
    Uso:
    - El nuevo chat.py tiene su propio procesador inteligente
    - Este FlowManager solo se usa como fallback si es necesario
    """)