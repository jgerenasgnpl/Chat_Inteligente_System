import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

logger = logging.getLogger(__name__)

class StateConditionBridge:
    """
    🌉 BRIDGE ENTRE ML Y ESTADOS BD
    - Mapea intenciones ML a condiciones BD
    - Ejecuta transiciones correctas según tabla Estados_Conversacion
    - Valida condiciones y acciones
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # 🎯 MAPEO CRÍTICO: ML Intenciones → BD Condiciones
        self.intencion_to_condicion = {
            # === IDENTIFICACIÓN ===
            'IDENTIFICACION': 'cedula_detectada',
            'IDENTIFICACION_EXITOSA': 'cedula_detectada',
            
            # === CONFIRMACIONES Y SELECCIONES ===
            'CONFIRMACION': 'cliente_confirma_interes',
            'CONFIRMACION_EXITOSA': 'cliente_selecciona_plan',  # ✅ CRÍTICO
            'INTENCION_PAGO': 'cliente_muestra_intencion',
            'SOLICITUD_PLAN': 'cliente_confirma_interes',
            
            # === SELECCIÓN DE PLANES ===
            'ACEPTAR_PLAN': 'cliente_selecciona_plan',
            'ELEGIR_OPCION': 'cliente_selecciona_plan',
            'PLAN_SELECCIONADO': 'cliente_selecciona_plan',
            
            # === RECHAZO Y OBJECIONES ===
            'RECHAZO': 'cliente_rechaza',
            'OBJECION': 'tipo_objecion',
            'NO_PUEDE_PAGAR': 'cliente_indica_motivo',
            
            # === CONTEXTUALES ===
            'SALUDO': 'cliente_responde',
            'CONSULTA_DEUDA': 'cliente_confirma_interes',
            'DESPEDIDA': 'cliente_finaliza',
            
            # === TIMEOUTS Y SEGUIMIENTOS ===
            'TIMEOUT_RESPONSE': 'cliente_responde_timeout',
            'SEGUIMIENTO_RESPONSE': 'cliente_responde',
            
            # === ESCALAMIENTOS ===
            'SOLICITAR_ASESOR': 'necesita_escalamiento',
            'EMERGENCIA_FINANCIERA': 'activar_protocolo_emergencia'
        }
        
        # 🎯 MAPEO ADICIONAL: Palabras clave → Condiciones
        self.keyword_to_condicion = {
            # Selección de planes
            'acepto': 'cliente_selecciona_plan',
            'aceptar': 'cliente_selecciona_plan', 
            'si quiero': 'cliente_selecciona_plan',
            'plan 1': 'cliente_selecciona_plan',
            'plan 2': 'cliente_selecciona_plan', 
            'plan 3': 'cliente_selecciona_plan',
            'pago unico': 'cliente_selecciona_plan',
            'cuotas': 'cliente_selecciona_plan',
            'primera opcion': 'cliente_selecciona_plan',
            'segunda opcion': 'cliente_selecciona_plan',
            'tercera opcion': 'cliente_selecciona_plan',
            
            # Confirmaciones
            'confirmo': 'cliente_confirma_acuerdo',
            'de acuerdo': 'cliente_confirma_interes',
            'está bien': 'cliente_confirma_interes',
            'perfecto': 'cliente_confirma_interes',
            
            # Rechazos
            'no puedo': 'cliente_indica_motivo',
            'imposible': 'cliente_rechaza',
            'no me interesa': 'cliente_rechaza',
            'muy caro': 'tipo_objecion',
            
            # Solicitudes
            'opciones': 'cliente_confirma_interes',
            'información': 'cliente_confirma_interes',
            'asesor': 'necesita_escalamiento',
            'supervisor': 'necesita_escalamiento'
        }
        
        # 🎯 CACHE DE ESTADOS
        self.estados_cache = {}
        self._load_estados_from_db()
    
    def _load_estados_from_db(self):
        """Cargar estados desde BD"""
        try:
            query = text("""
                SELECT nombre, accion, condicion, 
                       estado_siguiente_true, estado_siguiente_false, estado_siguiente_default
                FROM Estados_Conversacion 
                WHERE activo = 1
            """)
            
            result = self.db.execute(query)
            
            for row in result:
                estado_nombre = row[0]
                self.estados_cache[estado_nombre] = {
                    'accion': row[1],
                    'condicion': row[2], 
                    'siguiente_true': row[3],
                    'siguiente_false': row[4],
                    'siguiente_default': row[5]
                }
            
            logger.info(f"✅ {len(self.estados_cache)} estados cargados desde BD")
            
        except Exception as e:
            logger.error(f"❌ Error cargando estados: {e}")
            self.estados_cache = {}
    
    def determinar_siguiente_estado(self, estado_actual: str, mensaje: str, 
                                  intencion_ml: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 MÉTODO PRINCIPAL: Determinar siguiente estado basado en BD
        """
        
        logger.info(f"🌉 Bridge: {estado_actual} + '{mensaje}' + {intencion_ml}")
        
        # 1. Obtener configuración del estado actual
        estado_config = self.estados_cache.get(estado_actual)
        if not estado_config:
            logger.warning(f"⚠️ Estado {estado_actual} no encontrado en cache")
            return self._fallback_transition(estado_actual, intencion_ml, contexto)
        
        # 2. Determinar condición que se cumple
        condicion_cumplida = self._evaluar_condicion(
            mensaje, intencion_ml, estado_config['condicion'], contexto
        )
        
        # 3. Determinar siguiente estado según condición
        if condicion_cumplida:
            siguiente_estado = estado_config['siguiente_true']
            razon = f"Condición '{estado_config['condicion']}' cumplida"
        else:
            # Verificar si hay estado por defecto o false
            if estado_config['siguiente_false']:
                siguiente_estado = estado_config['siguiente_false']
                razon = f"Condición '{estado_config['condicion']}' NO cumplida"
            else:
                siguiente_estado = estado_config['siguiente_default'] or estado_actual
                razon = "Usando estado por defecto"
        
        # 4. Ejecutar acción si existe
        accion_resultado = self._ejecutar_accion(estado_config['accion'], contexto)
        
        logger.info(f"🎯 Transición: {estado_actual} → {siguiente_estado} ({razon})")
        
        return {
            'siguiente_estado': siguiente_estado,
            'condicion_cumplida': condicion_cumplida,
            'condicion_evaluada': estado_config['condicion'],
            'razon_transicion': razon,
            'accion_ejecutada': estado_config['accion'],
            'accion_resultado': accion_resultado,
            'metodo': 'bridge_bd_estados'
        }
    
    def _evaluar_condicion(self, mensaje: str, intencion_ml: str, 
                          condicion_bd: str, contexto: Dict[str, Any]) -> bool:
        """
        🔍 EVALUAR SI SE CUMPLE LA CONDICIÓN
        """
        
        if not condicion_bd:
            return True  # Sin condición = siempre true
        
        mensaje_lower = mensaje.lower()
        
        # 1. MAPEO DIRECTO: Intención ML → Condición BD
        condicion_por_intencion = self.intencion_to_condicion.get(intencion_ml)
        if condicion_por_intencion == condicion_bd:
            logger.info(f"✅ Condición por intención: {intencion_ml} → {condicion_bd}")
            return True
        
        # 2. MAPEO POR PALABRAS CLAVE
        for keyword, condicion in self.keyword_to_condicion.items():
            if keyword in mensaje_lower and condicion == condicion_bd:
                logger.info(f"✅ Condición por keyword: '{keyword}' → {condicion_bd}")
                return True
        
        # 3. EVALUACIONES ESPECÍFICAS POR CONDICIÓN
        return self._evaluar_condicion_especifica(condicion_bd, mensaje, intencion_ml, contexto)
    
    def _evaluar_condicion_especifica(self, condicion: str, mensaje: str, 
                                    intencion: str, contexto: Dict[str, Any]) -> bool:
        """Evaluaciones específicas por tipo de condición"""
        
        mensaje_lower = mensaje.lower()
        
        # === IDENTIFICACIÓN ===
        if condicion == 'cedula_detectada':
            import re
            return bool(re.search(r'\b\d{7,12}\b', mensaje))
        
        # === SELECCIÓN DE PLANES ===
        elif condicion == 'cliente_selecciona_plan':
            seleccion_keywords = [
                'acepto', 'acepta', 'si', 'sí', 'plan', 'opcion', 'cuotas',
                'pago unico', 'primera', 'segunda', 'tercera', '1', '2', '3',
                'de acuerdo', 'está bien', 'perfecto', 'excelente'
            ]
            return any(kw in mensaje_lower for kw in seleccion_keywords)
        
        # === CONFIRMACIONES ===
        elif condicion == 'cliente_confirma_interes':
            confirmacion_keywords = [
                'si', 'sí', 'claro', 'perfecto', 'de acuerdo', 'está bien',
                'quiero', 'necesito', 'me interesa', 'opciones', 'información'
            ]
            return any(kw in mensaje_lower for kw in confirmacion_keywords)
        
        elif condicion == 'cliente_confirma_acuerdo':
            return any(kw in mensaje_lower for kw in ['confirmo', 'acepto', 'de acuerdo', 'si'])
        
        # === RECHAZOS ===
        elif condicion == 'cliente_rechaza':
            rechazo_keywords = ['no', 'imposible', 'no puedo', 'no me interesa']
            return any(kw in mensaje_lower for kw in rechazo_keywords)
        
        elif condicion == 'tipo_objecion':
            objecion_keywords = ['muy caro', 'no tengo', 'difícil', 'problema']
            return any(kw in mensaje_lower for kw in objecion_keywords)
        
        # === MOTIVOS ===
        elif condicion == 'cliente_indica_motivo':
            motivo_keywords = ['porque', 'no puedo', 'crisis', 'desempleo', 'problema']
            return any(kw in mensaje_lower for kw in motivo_keywords)
        
        # === ESCALAMIENTOS ===
        elif condicion == 'necesita_escalamiento':
            escalamiento_keywords = ['asesor', 'supervisor', 'ayuda', 'hablar con']
            return any(kw in mensaje_lower for kw in escalamiento_keywords)
        
        # === RESPUESTAS Y ACTIVIDAD ===
        elif condicion in ['cliente_responde', 'cliente_responde_timeout']:
            return len(mensaje.strip()) > 0
        
        # === INTENCIONES DE PAGO ===
        elif condicion == 'cliente_muestra_intencion':
            intencion_keywords = ['pagar', 'quiero', 'puedo', 'cuando', 'cómo']
            return any(kw in mensaje_lower for kw in intencion_keywords)
        
        # === DEFAULT ===
        else:
            logger.warning(f"⚠️ Condición no reconocida: {condicion}")
            return False
    
    def _ejecutar_accion(self, accion: str, contexto: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ejecutar acción si existe"""
        
        if not accion:
            return None
        
        try:
            # Importar servicios de acciones
            from app.services.acciones_service import crear_acciones_service
            acciones_service = crear_acciones_service(self.db)
            
            # Ejecutar acción
            resultado = acciones_service.ejecutar_accion(accion, contexto)
            logger.info(f"🔧 Acción ejecutada: {accion} → {resultado.get('exito', False)}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando acción {accion}: {e}")
            return {"error": str(e), "exito": False}
    
    def _fallback_transition(self, estado_actual: str, intencion: str, 
                           contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Transición de fallback cuando no hay estado en BD"""
        
        # Mapeo básico de fallback
        fallback_map = {
            'IDENTIFICACION': 'informar_deuda',
            'CONFIRMACION': 'proponer_planes_pago',
            'INTENCION_PAGO': 'proponer_planes_pago',
            'RECHAZO': 'gestionar_objecion',
            'SOLICITUD_PLAN': 'proponer_planes_pago',
            'DESPEDIDA': 'finalizar_conversacion'
        }
        
        siguiente = fallback_map.get(intencion, estado_actual)
        
        return {
            'siguiente_estado': siguiente,
            'condicion_cumplida': True,
            'razon_transicion': f'Fallback por intención {intencion}',
            'metodo': 'fallback_transition'
        }
    
    # ==========================================
    # MÉTODOS DE UTILIDAD Y DEBUGGING
    # ==========================================
    
    def test_condicion(self, condicion: str, mensaje: str, intencion: str) -> bool:
        """Test de condición específica"""
        return self._evaluar_condicion_especifica(condicion, mensaje, intencion, {})
    
    def get_posibles_transiciones(self, estado_actual: str) -> Dict[str, Any]:
        """Obtener posibles transiciones desde estado actual"""
        estado_config = self.estados_cache.get(estado_actual, {})
        
        return {
            'estado_actual': estado_actual,
            'condicion_requerida': estado_config.get('condicion'),
            'accion': estado_config.get('accion'),
            'posibles_destinos': {
                'si_cumple': estado_config.get('siguiente_true'),
                'si_no_cumple': estado_config.get('siguiente_false'),
                'por_defecto': estado_config.get('siguiente_default')
            }
        }
    
    def debug_evaluacion(self, estado_actual: str, mensaje: str, intencion: str) -> Dict[str, Any]:
        """Debug completo de evaluación"""
        
        estado_config = self.estados_cache.get(estado_actual, {})
        condicion_bd = estado_config.get('condicion')
        
        # Evaluaciones paso a paso
        evaluaciones = {
            'estado_actual': estado_actual,
            'mensaje': mensaje,
            'intencion_ml': intencion,
            'condicion_bd': condicion_bd,
            'mapeo_intencion': self.intencion_to_condicion.get(intencion),
            'keywords_detectadas': [],
            'condicion_cumplida': False
        }
        
        # Detectar keywords
        mensaje_lower = mensaje.lower()
        for keyword, condicion in self.keyword_to_condicion.items():
            if keyword in mensaje_lower:
                evaluaciones['keywords_detectadas'].append({
                    'keyword': keyword,
                    'condicion': condicion,
                    'coincide_bd': condicion == condicion_bd
                })
        
        # Evaluación final
        evaluaciones['condicion_cumplida'] = self._evaluar_condicion(
            mensaje, intencion, condicion_bd, {}
        )
        
        return evaluaciones

# ==========================================
# INTEGRACIÓN CON CONVERSATION SERVICE
# ==========================================

def integrar_bridge_en_conversation_service():
    """
    🔧 FUNCIÓN PARA INTEGRAR EN conversation_service.py
    
    Agregar esto al método _process_message_simple:
    """
    
    integration_code = '''
    # En conversation_service.py, método _process_message_simple
    
    # DESPUÉS de obtener resultado ML, ANTES de generar respuesta:
    
    # ✅ USAR BRIDGE PARA DETERMINAR TRANSICIÓN CORRECTA
    from app.services.state_condition_bridge import StateConditionBridge
    
    bridge = StateConditionBridge(self.db)
    
    # Determinar siguiente estado basado en BD
    transicion = bridge.determinar_siguiente_estado(
        estado_actual=conversation.current_state,
        mensaje=user_message,
        intencion_ml=resultado.get("trigger", ""),
        contexto=contexto
    )
    
    # Usar resultado del bridge
    return {
        "new_state": transicion["siguiente_estado"],
        "trigger": transicion["condicion_evaluada"],
        "context_updates": transicion.get("accion_resultado", {}),
        "success": True,
        "transicion_info": transicion,
        "metodo": "bridge_ml_bd_estados"
    }
    '''
    
    return integration_code

# ==========================================
# FACTORY Y UTILIDADES
# ==========================================

def crear_state_condition_bridge(db: Session) -> StateConditionBridge:
    """Factory para crear bridge"""
    return StateConditionBridge(db)

def test_bridge_functionality(db: Session):
    """Test del bridge con casos reales"""
    bridge = StateConditionBridge(db)
    
    test_cases = [
        {
            'estado': 'proponer_planes_pago',
            'mensaje': 'acepto la primera opción',
            'intencion': 'CONFIRMACION_EXITOSA',
            'esperado': 'confirmar_plan_elegido'
        },
        {
            'estado': 'validar_documento', 
            'mensaje': '12345678',
            'intencion': 'IDENTIFICACION',
            'esperado': 'informar_deuda'
        },
        {
            'estado': 'informar_deuda',
            'mensaje': 'si quiero ver opciones',
            'intencion': 'CONFIRMACION',
            'esperado': 'proponer_planes_pago'
        }
    ]
    
    results = []
    for test in test_cases:
        resultado = bridge.determinar_siguiente_estado(
            test['estado'], test['mensaje'], test['intencion'], {}
        )
        
        results.append({
            'test': test,
            'resultado': resultado,
            'correcto': resultado['siguiente_estado'] == test['esperado']
        })
    
    return results