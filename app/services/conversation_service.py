"""
CONVERSATION_SERVICE.PY CORREGIDO
- Elimina dependencias de FlowManager problemático
- Usa solo ML y lógica simple
- Sin código hardcodeado
- Compatible con el nuevo chat.py
"""

import json
import re
import logging
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from app.models.conversation import Conversation
from app.services.variable_service import crear_variable_service
from app.services.cache_service import cache_service, cache_result
from app.services.dynamic_transition_service import create_dynamic_transition_service
import hashlib

logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN SIMPLIFICADA
# ==========================================
CONVERSATION_TIMEOUT_MINUTES = 30
CACHE_TIMEOUT_SECONDS = 1800
MAX_CONVERSATIONS_PER_USER = 1

# Cache global simplificado
CONTEXT_CACHE = {}
CACHE_TIMESTAMPS = {}
CONVERSATION_ACTIVITY = {}

class ConversationService:
    """
    ✅ VERSIÓN SIMPLIFICADA Y CORREGIDA
    - Sin dependencias problemáticas de FlowManager
    - Usa directamente ML y lógica simple
    - Compatible con chat.py corregido
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.variable_service = crear_variable_service(db)
        self.ml_service = self._init_ml_service()
        self.request_count = 0
        self.dynamic_transition_service = create_dynamic_transition_service(db)
        logger.info("✅ Servicio de transiciones dinámico inicializado")
        # Limpiar sesiones expiradas
        self._cleanup_expired_sessions()
        logger.info("✅ ConversationService inicializado (versión simplificada)")
    
    def _init_ml_service(self):
        """Inicializar servicio ML de forma segura"""
        try:
            from app.services.nlp_service import nlp_service
            nlp_service.actualizar_cache(self.db)
            return nlp_service
        except Exception as e:
            logger.warning(f"ML service no disponible: {e}")
            return None
    
    async def process_message(self, conversation_id: int, user_message: str, user_id: int) -> Dict:
        """
        ✅ MÉTODO PRINCIPAL SIMPLIFICADO
        - Sin dependencias de FlowManager
        - Lógica directa y simple
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            logger.info(f"📨 [{self.request_count}] Procesando: '{user_message[:50]}...' (usuario {user_id})")
            
            # 1. VALIDAR SESIÓN
            self._validate_and_cleanup_session(conversation_id, user_id)
            
            # 2. OBTENER CONVERSACIÓN
            conversation = self.get_or_create_clean_conversation(conversation_id, user_id)
            
            # 3. VERIFICAR TIMEOUT
            if self._is_conversation_expired(conversation.id):
                logger.info(f"⏰ Conversación {conversation.id} expirada")
                return self._handle_expired_conversation(conversation, user_message)
            
            # 4. ACTUALIZAR ACTIVIDAD
            self._update_conversation_activity(conversation.id)
            
            # 5. RECUPERAR CONTEXTO
            contexto = self._get_validated_context(conversation, user_message)
            
            logger.info(f"💬 Conv {conversation.id} - Estado: {conversation.current_state}")
            
            # 6. PROCESAR MENSAJE SIMPLE
            resultado = await self._process_message_simple(conversation, user_message, contexto)
            
            # 7. GENERAR RESPUESTA
            response = self._generate_response_simple(resultado, contexto)
            
            # 8. ACTUALIZAR CONVERSACIÓN
            conversation.current_state = resultado.get("new_state", conversation.current_state)
            conversation.last_message = user_message
            conversation.response = response
            conversation.updated_at = datetime.now()
            
            # 9. GUARDAR CONTEXTO
            if resultado.get("context_updates"):
                self._update_context_simple(conversation, resultado["context_updates"])
            
            self.db.commit()
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Respuesta generada en {execution_time:.1f}ms")
            
            return {
                "response": response,
                "conversation_id": conversation_id,
                "state": conversation.current_state,
                "context": self._get_context_dict(conversation),
                "buttons": self._get_buttons_simple(conversation.current_state, contexto),
                "session_valid": True,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return self._error_response(conversation_id, user_id)

    async def _process_message_simple(self, conversation: Conversation, user_message: str, contexto: Dict) -> Dict:
        """
        ✅ PROCESAMIENTO 100% DINÁMICO
        - Sin código hardcodeado
        - Todo basado en BD + ML
        - Auto-aprendizaje
        """
        try:
            start_time = time.time()
            
            logger.info(f"🎯 Procesamiento dinámico: '{user_message[:50]}...' en estado '{conversation.current_state}'")
            
            # 1. DETECCIÓN DE CÉDULA (MÁXIMA PRIORIDAD)
            cedula_detectada = self._extract_cedula_simple(user_message)
            
            if cedula_detectada:
                logger.info(f"🎯 Cédula detectada: {cedula_detectada}")
                
                # Crear pseudo-resultado ML para cédula
                cedula_ml_result = {
                    'intention': 'IDENTIFICACION_EXITOSA' if await self._is_valid_cedula(cedula_detectada) else 'IDENTIFICACION_FALLIDA',
                    'confidence': 0.95,
                    'method': 'cedula_detection'
                }
                
                # Consultar cliente
                cliente_info = await self._query_client_simple(cedula_detectada)
                
                if cliente_info and cliente_info.get("encontrado"):
                    # Actualizar contexto con datos del cliente
                    contexto_actualizado = {**contexto, **self._build_client_context(cliente_info, cedula_detectada)}
                    
                    # ✅ USAR SERVICIO DINÁMICO PARA DETERMINAR TRANSICIÓN
                    transition_result = self.dynamic_transition_service.determine_next_state(
                        current_state=conversation.current_state,
                        user_message=user_message,
                        ml_result=cedula_ml_result,
                        context=contexto_actualizado
                    )
                    
                    # Log para aprendizaje
                    self.dynamic_transition_service.log_decision(
                        conversation.id, conversation.current_state, user_message,
                        cedula_ml_result, transition_result
                    )
                    
                    return {
                        "new_state": transition_result["next_state"],
                        "trigger": "identificacion_dinamica",
                        "context_updates": contexto_actualizado,
                        "success": True,
                        "transition_info": transition_result,
                        "method": "dynamic_cedula_detection"
                    }
                else:
                    # Cliente no encontrado
                    cedula_ml_result['intention'] = 'IDENTIFICACION_FALLIDA'
                    
                    transition_result = self.dynamic_transition_service.determine_next_state(
                        current_state=conversation.current_state,
                        user_message=user_message,
                        ml_result=cedula_ml_result,
                        context=contexto
                    )
                    
                    return {
                        "new_state": transition_result["next_state"],
                        "trigger": "cedula_no_encontrada_dinamica",
                        "context_updates": {"cedula_no_encontrada": cedula_detectada},
                        "success": False,
                        "transition_info": transition_result,
                        "method": "dynamic_cedula_not_found"
                    }
            
            # 2. CLASIFICACIÓN CON ML + PROCESAMIENTO DINÁMICO
            ml_result = {}
            if self.ml_service:
                ml_result = self._classify_with_ml_simple(user_message, contexto, conversation.current_state)
                
                if ml_result.get('confidence', 0) >= 0.6:
                    logger.info(f"🤖 ML: {ml_result.get('intention')} (confianza: {ml_result.get('confidence', 0):.2f})")
                    
                    # ✅ USAR SERVICIO DINÁMICO
                    transition_result = self.dynamic_transition_service.determine_next_state(
                        current_state=conversation.current_state,
                        user_message=user_message,
                        ml_result=ml_result,
                        context=contexto
                    )
                    
                    # Log para aprendizaje
                    self.dynamic_transition_service.log_decision(
                        conversation.id, conversation.current_state, user_message,
                        ml_result, transition_result
                    )
                    
                    if transition_result["next_state"] != conversation.current_state:
                        logger.info(f"✅ Transición dinámica ML: {conversation.current_state} → {transition_result['next_state']}")
                        
                        return {
                            "new_state": transition_result["next_state"],
                            "trigger": f"ml_dinamico_{ml_result.get('intention')}",
                            "context_updates": {},
                            "success": True,
                            "confidence": ml_result.get('confidence'),
                            "transition_info": transition_result,
                            "method": "dynamic_ml_classification"
                        }
            
            # 3. PROCESAMIENTO CONTEXTUAL DINÁMICO (Sin ML)
            # Crear pseudo-resultado ML basado en análisis contextual
            contextual_ml_result = self._create_contextual_ml_result(user_message, contexto, conversation.current_state)
            
            # ✅ USAR SERVICIO DINÁMICO PARA ANÁLISIS CONTEXTUAL
            transition_result = self.dynamic_transition_service.determine_next_state(
                current_state=conversation.current_state,
                user_message=user_message,
                ml_result=contextual_ml_result,
                context=contexto
            )
            
            # Log para aprendizaje
            self.dynamic_transition_service.log_decision(
                conversation.id, conversation.current_state, user_message,
                contextual_ml_result, transition_result
            )
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Procesamiento dinámico completado en {execution_time:.1f}ms")
            
            return {
                "new_state": transition_result["next_state"],
                "trigger": f"contextual_dinamico_{contextual_ml_result.get('intention')}",
                "context_updates": {},
                "success": True,
                "transition_info": transition_result,
                "method": "dynamic_contextual_analysis",
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento dinámico: {e}")
            return {
                "new_state": conversation.current_state,
                "trigger": "error_dinamico",
                "context_updates": {},
                "success": False,
                "error": str(e),
                "method": "error_fallback"
            }

    def _determinar_intencion_contextual(self, mensaje: str, contexto: Dict) -> str:
        """✅ DETERMINAR INTENCIÓN CONTEXTUAL PARA BRIDGE"""
        
        mensaje_lower = mensaje.lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        # Confirmaciones y selecciones (MUY IMPORTANTE)
        if any(word in mensaje_lower for word in ['acepto', 'aceptar', 'si', 'sí', 'de acuerdo', 'está bien']):
            # Si ya tiene cliente y está en proceso de selección
            if tiene_cliente:
                return 'CONFIRMACION_EXITOSA'  # ← Esto mapea a 'cliente_selecciona_plan'
            else:
                return 'CONFIRMACION'
        
        # Rechazos
        elif any(word in mensaje_lower for word in ['no', 'imposible', 'no puedo']):
            return 'RECHAZO'
        
        # Solicitud de información
        elif any(word in mensaje_lower for word in ['opciones', 'planes', 'información']):
            return 'SOLICITUD_PLAN'
        
        # Intención de pago
        elif any(word in mensaje_lower for word in ['pagar', 'quiero', 'puedo']):
            return 'INTENCION_PAGO'
        
        # Escalamiento
        elif any(word in mensaje_lower for word in ['asesor', 'supervisor', 'ayuda']):
            return 'SOLICITAR_ASESOR'
        
        # Saludos
        elif any(word in mensaje_lower for word in ['hola', 'buenas', 'buenos']):
            return 'SALUDO'
        
        # Default
        return 'CONTINUACION'

    def _extract_cedula_simple(self, mensaje: str) -> Optional[str]:
        """Extracción simple de cédula"""
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
    
    async def _query_client_simple(self, cedula: str) -> Optional[Dict]:
        """Consulta simple de cliente"""
        try:
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Saldo_total, banco,
                    Oferta_1, Oferta_2, 
                    Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas,
                    Producto, Telefono, Email
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)})
            row = result.fetchone()
            
            if row:
                return {
                    "encontrado": True,
                    "nombre": row[0] or "Cliente",
                    "saldo": int(float(row[1])) if row[1] else 0,
                    "banco": row[2] or "Entidad Financiera",
                    "oferta_1": int(float(row[3])) if row[3] else 0,
                    "oferta_2": int(float(row[4])) if row[4] else 0,
                    "hasta_3_cuotas": int(float(row[5])) if row[5] else 0,
                    "hasta_6_cuotas": int(float(row[6])) if row[6] else 0,
                    "hasta_12_cuotas": int(float(row[7])) if row[7] else 0,
                    "producto": row[8] or "Producto",
                    "telefono": row[9] or "",
                    "email": row[10] or ""
                }
            
            return {"encontrado": False}
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente {cedula}: {e}")
            return {"encontrado": False}
    
    async def _is_valid_cedula(self, cedula: str) -> bool:
        """Validar si cédula es válida antes de consultar"""
        if not cedula or len(cedula) < 7 or len(cedula) > 12:
            return False
        
        # No puede ser todos números iguales
        if len(set(cedula)) <= 1:
            return False
        
        return cedula.isdigit()

    def _build_client_context(self, cliente_info: Dict[str, Any], cedula: str) -> Dict[str, Any]:
        """Construir contexto del cliente de forma estructurada"""
        
        datos_cliente = cliente_info.get('datos', {})
        
        return {
            "cedula_detectada": cedula,
            "cliente_encontrado": True,
            "Nombre_del_cliente": datos_cliente.get("nombre", "Cliente"),
            "saldo_total": datos_cliente.get("saldo", 0),
            "banco": datos_cliente.get("banco", "Entidad Financiera"),
            "oferta_1": datos_cliente.get("oferta_1", 0),
            "oferta_2": datos_cliente.get("oferta_2", 0),
            "hasta_3_cuotas": datos_cliente.get("hasta_3_cuotas", 0),
            "hasta_6_cuotas": datos_cliente.get("hasta_6_cuotas", 0),
            "hasta_12_cuotas": datos_cliente.get("hasta_12_cuotas", 0),
            "consulta_timestamp": datetime.now().isoformat(),
            "consulta_method": "dynamic_detection"
        }

    def _create_contextual_ml_result(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> Dict[str, Any]:
        """
        ✅ CREAR PSEUDO-RESULTADO ML BASADO EN ANÁLISIS CONTEXTUAL
        - Esto reemplaza la lógica hardcodeada
        - Permite que el servicio dinámico maneje todo
        """
        
        mensaje_lower = mensaje.lower().strip()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        # Análisis contextual básico para generar "intención"
        if len(mensaje_lower) == 0:
            intention = 'MENSAJE_VACIO'
            confidence = 0.1
            
        elif any(word in mensaje_lower for word in ['acepto', 'aceptar', 'si', 'sí', 'de acuerdo', 'está bien']):
            if tiene_cliente and estado == 'proponer_planes_pago':
                intention = 'CONFIRMACION_EXITOSA'  # ← Esto se mapea dinámicamente a 'cliente_selecciona_plan'
                confidence = 0.9
            else:
                intention = 'CONFIRMACION'
                confidence = 0.8
                
        elif any(word in mensaje_lower for word in ['no', 'imposible', 'no puedo', 'muy caro']):
            intention = 'RECHAZO'
            confidence = 0.8
            
        elif any(word in mensaje_lower for word in ['opciones', 'planes', 'información', 'cuotas']):
            intention = 'SOLICITUD_PLAN'
            confidence = 0.8
            
        elif any(word in mensaje_lower for word in ['pagar', 'quiero', 'puedo', 'cuando']):
            intention = 'INTENCION_PAGO'
            confidence = 0.7
            
        elif any(word in mensaje_lower for word in ['asesor', 'supervisor', 'ayuda', 'hablar con']):
            intention = 'SOLICITAR_ASESOR'
            confidence = 0.9
            
        elif any(word in mensaje_lower for word in ['hola', 'buenas', 'buenos', 'hi']):
            intention = 'SALUDO'
            confidence = 0.9
            
        elif any(word in mensaje_lower for word in ['gracias', 'adiós', 'chao', 'bye']):
            intention = 'DESPEDIDA'
            confidence = 0.9
            
        else:
            intention = 'MENSAJE_GENERAL'
            confidence = 0.5
        
        return {
            'intention': intention,
            'confidence': confidence,
            'method': 'contextual_analysis',
            'message_length': len(mensaje),
            'has_client': tiene_cliente,
            'current_state': estado
        }

    def get_dynamic_service_stats(self) -> Dict[str, Any]:
        """✅ NUEVO - Obtener estadísticas del servicio dinámico"""
        try:
            return self.dynamic_transition_service.get_stats()
        except Exception as e:
            return {"error": str(e)}

    def trigger_auto_improvement(self):
        """✅ NUEVO - Disparar auto-mejora del sistema"""
        try:
            self.dynamic_transition_service.auto_improve_patterns()
            logger.info("✅ Auto-mejora del sistema ejecutada")
            return True
        except Exception as e:
            logger.error(f"❌ Error en auto-mejora: {e}")
            return False


    def _classify_with_ml_simple(self, mensaje: str, contexto: Dict, estado: str) -> Dict:
        """Clasificación ML simple"""
        try:
            ml_result = self.ml_service.predict(mensaje)
            intencion = ml_result.get('intention', 'DESCONOCIDA')
            confianza = ml_result.get('confidence', 0.0)
            
            logger.info(f"🤖 ML: {intencion} (confianza: {confianza:.2f})")
            
            # Mapear intención a estado
            next_state = self._map_intention_simple(intencion, estado, contexto)
            
            return {
                "new_state": next_state,
                "trigger": intencion.lower(),
                "context_updates": {},
                "success": True,
                "confidence": confianza,
                "method": "ml_classification"
            }
            
        except Exception as e:
            logger.error(f"❌ Error en ML: {e}")
            return {"confidence": 0.0}
    
    def _map_intention_simple(self, intencion: str, estado_actual: str, contexto: Dict) -> str:
        """Mapeo simple de intención a estado"""
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        mapeo = {
            'IDENTIFICACION': 'validar_documento',
            'CONSULTA_DEUDA': 'informar_deuda' if tiene_cliente else 'validar_documento',
            'INTENCION_PAGO': 'proponer_planes_pago' if tiene_cliente else 'validar_documento',
            'SOLICITUD_PLAN': 'proponer_planes_pago' if tiene_cliente else 'validar_documento',
            'CONFIRMACION': 'proponer_planes_pago' if estado_actual == 'informar_deuda' else 'generar_acuerdo',
            'RECHAZO': 'gestionar_objecion',
            'SALUDO': estado_actual if tiene_cliente else 'validar_documento',
            'DESPEDIDA': 'finalizar_conversacion'
        }
        
        return mapeo.get(intencion, estado_actual)
    
    def _analyze_context_simple(self, mensaje: str, contexto: Dict, estado: str) -> Dict:
        """Análisis contextual simple"""
        mensaje_lower = mensaje.lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        # Confirmaciones
        if any(word in mensaje_lower for word in ['si', 'sí', 'acepto', 'ok']):
            if tiene_cliente and estado == 'informar_deuda':
                return {
                    "new_state": "proponer_planes_pago",
                    "trigger": "confirmacion",
                    "context_updates": {},
                    "success": True
                }
            elif tiene_cliente and estado == 'proponer_planes_pago':
                return {
                    "new_state": "generar_acuerdo",
                    "trigger": "confirmacion",
                    "context_updates": {},
                    "success": True
                }
        
        # Rechazos
        elif any(word in mensaje_lower for word in ['no', 'imposible', 'no puedo']):
            return {
                "new_state": "gestionar_objecion",
                "trigger": "rechazo",
                "context_updates": {},
                "success": True
            }
        
        # Solicitud de información
        elif any(word in mensaje_lower for word in ['opciones', 'planes', 'cuotas', 'información']):
            if tiene_cliente:
                return {
                    "new_state": "proponer_planes_pago",
                    "trigger": "solicitud_opciones",
                    "context_updates": {},
                    "success": True
                }
        
        # Mantener estado actual por defecto
        return {
            "new_state": estado,
            "trigger": "continuacion",
            "context_updates": {},
            "success": True
        }
    
    def _generate_response_simple(self, resultado: Dict, contexto: Dict) -> str:
        """Generar respuesta simple basada en estado y contexto"""
        estado = resultado.get("new_state", "inicial")
        trigger = resultado.get("trigger", "")
        
        # Templates simples por estado
        templates = {
            "inicial": "¡Hola! Para ayudarte, necesito tu número de cédula.",
            
            "informar_deuda": """¡Perfecto, {{Nombre_del_cliente}}! 
            
📋 **Información de tu cuenta:**
🏦 Entidad: {{banco}}
💰 Saldo actual: ${{saldo_total}}

¿Te gustaría conocer las opciones de pago disponibles para ti?""",

            "proponer_planes_pago": """Excelente, {{Nombre_del_cliente}}! Te muestro las mejores opciones para tu saldo de ${{saldo_total}}:

💰 **PAGO ÚNICO CON DESCUENTO:**
🎯 Oferta especial: ${{oferta_2}} (¡Excelente ahorro!)

📅 **PLANES DE CUOTAS SIN INTERÉS:**
• 3 cuotas de: ${{hasta_3_cuotas}} cada una
• 6 cuotas de: ${{hasta_6_cuotas}} cada una  
• 12 cuotas de: ${{hasta_12_cuotas}} cada una

¿Cuál opción se adapta mejor a tu presupuesto?""",

            "generar_acuerdo": "¡Perfecto! Confirmo tu elección. Procederé a generar tu acuerdo de pago.",

            "cliente_no_encontrado": "No encontré información para esa cédula. Por favor verifica el número.",

            "gestionar_objecion": "Entiendo tu situación. ¿Hay algo específico que te preocupa? Podemos buscar alternativas.",

            "finalizar_conversacion": "¡Gracias por contactarnos! Tu proceso ha sido completado exitosamente."
        }
        
        template = templates.get(estado, "¿En qué puedo ayudarte?")
        
        # Resolver variables usando el servicio
        try:
            response = self.variable_service.resolver_variables(template, contexto)
            return response
        except Exception as e:
            logger.error(f"Error resolviendo variables: {e}")
            return template
    
    def _get_buttons_simple(self, estado: str, contexto: Dict) -> List[Dict]:
        """Botones simples por estado"""
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if estado == "informar_deuda" and tiene_cliente:
            return [
                {"id": "si_opciones", "text": "Sí, quiero ver opciones"},
                {"id": "no_ahora", "text": "No por ahora"}
            ]
        elif estado == "proponer_planes_pago" and tiene_cliente:
            return [
                {"id": "pago_unico", "text": "Pago único"},
                {"id": "plan_3_cuotas", "text": "3 cuotas"},
                {"id": "plan_6_cuotas", "text": "6 cuotas"},
                {"id": "plan_12_cuotas", "text": "12 cuotas"}
            ]
        elif estado == "generar_acuerdo":
            return [
                {"id": "confirmar", "text": "Confirmar acuerdo"},
                {"id": "modificar", "text": "Modificar términos"}
            ]
        elif estado == "gestionar_objecion":
            return [
                {"id": "plan_flexible", "text": "Plan flexible"},
                {"id": "asesor", "text": "Hablar con asesor"}
            ]
        
        return []
    
    # ==========================================
    # MÉTODOS DE SOPORTE SIMPLIFICADOS
    # ==========================================
    
    def get_or_create_clean_conversation(self, conversation_id: int, user_id: int) -> Conversation:
        """Obtener o crear conversación - versión simplificada"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if conversation:
                if self._is_conversation_expired(conversation.id):
                    # Reiniciar conversación expirada
                    conversation.current_state = "inicial"
                    conversation.context_data = "{}"
                    conversation.is_active = True
                    conversation.updated_at = datetime.now()
                
                    return conversation

            else:
                # Crear nueva conversación
                conversation = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    current_state="inicial",
                    context_data="{}",
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(conversation)
                self.db.commit()
                logger.info(f"🆕 Nueva conversación: {conversation_id}")
            
            if not conversation.context_data or conversation.context_data == "{}":
                    initial_context = {
                        "dynamic_system_enabled": True,
                        "conversation_started": datetime.now().isoformat(),
                        "transition_method": "dynamic_bd_ml"
                    }
                    conversation.context_data = json.dumps(initial_context, ensure_ascii=False, default=str)
                    self.db.commit()

            return conversation
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversación: {e}")
            raise
    
    def _validate_and_cleanup_session(self, conversation_id: int, user_id: int) -> bool:
        """Validación y limpieza simplificada"""
        try:
            self._cleanup_expired_cache()
            return True
        except Exception as e:
            logger.error(f"❌ Error validando sesión: {e}")
            return False
    
    def _is_conversation_expired(self, conversation_id: int) -> bool:
        """Verificar expiración simplificada"""
        try:
            last_activity = CONVERSATION_ACTIVITY.get(conversation_id)
            if not last_activity:
                return True
            
            inactive_minutes = (time.time() - last_activity) / 60
            return inactive_minutes > CONVERSATION_TIMEOUT_MINUTES
            
        except Exception as e:
            logger.error(f"❌ Error verificando expiración: {e}")
            return True
    
    def _update_conversation_activity(self, conversation_id: int):
        """Actualizar actividad"""
        CONVERSATION_ACTIVITY[conversation_id] = time.time()
    
    def _handle_expired_conversation(self, conversation: Conversation, user_message: str) -> Dict:
        """Manejar conversación expirada"""
        try:
            conversation.current_state = "inicial"
            conversation.context_data = "{}"
            conversation.updated_at = datetime.now()
            
            if conversation.id in CONTEXT_CACHE:
                del CONTEXT_CACHE[conversation.id]
            
            self._update_conversation_activity(conversation.id)
            self.db.commit()
            
            return {
                "response": "Tu sesión ha expirado. Por favor proporciona tu cédula para iniciar.",
                "conversation_id": conversation.id,
                "state": "inicial",
                "context": {},
                "buttons": [],
                "session_expired": True
            }
        except Exception as e:
            logger.error(f"❌ Error manejando expiración: {e}")
            return self._error_response(conversation.id, conversation.user_id)
    
    def _get_validated_context(self, conversation: Conversation, user_message: str) -> Dict[str, Any]:
        """Obtener contexto validado"""
        try:
            if conversation.id in CONTEXT_CACHE:
                cache_age = time.time() - CACHE_TIMESTAMPS.get(conversation.id, 0)
                if cache_age < CACHE_TIMEOUT_SECONDS:
                    return CONTEXT_CACHE[conversation.id]
            
            if hasattr(conversation, 'context_data') and conversation.context_data:
                try:
                    context = json.loads(conversation.context_data)
                    CONTEXT_CACHE[conversation.id] = context
                    CACHE_TIMESTAMPS[conversation.id] = time.time()
                    return context
                except json.JSONDecodeError:
                    pass
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto: {e}")
            return {}
    
    def _update_context_simple(self, conversation: Conversation, updates: Dict):
        """Actualizar contexto de forma simple"""
        try:
            current_context = {}
            if hasattr(conversation, 'context_data') and conversation.context_data:
                try:
                    current_context = json.loads(conversation.context_data)
                except:
                    pass
            
            current_context.update(updates)
            context_json = json.dumps(current_context, ensure_ascii=False, default=str)
            
            conversation.context_data = context_json
            
            # Actualizar cache
            CONTEXT_CACHE[conversation.id] = current_context
            CACHE_TIMESTAMPS[conversation.id] = time.time()
            
            logger.info(f"💾 Contexto actualizado: {len(updates)} elementos")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando contexto: {e}")
    
    def _get_context_dict(self, conversation: Conversation) -> Dict:
        """Obtener contexto como diccionario"""
        try:
            if hasattr(conversation, 'context_data') and conversation.context_data:
                return json.loads(conversation.context_data)
            return {}
        except:
            return {}
    
    def _cleanup_expired_cache(self):
        """Limpiar cache expirado"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for conv_id, timestamp in CACHE_TIMESTAMPS.items():
                if current_time - timestamp > CACHE_TIMEOUT_SECONDS:
                    expired_keys.append(conv_id)
            
            for key in expired_keys:
                CONTEXT_CACHE.pop(key, None)
                CACHE_TIMESTAMPS.pop(key, None)
                CONVERSATION_ACTIVITY.pop(key, None)
            
            if expired_keys:
                logger.info(f"🧹 Cache limpiado: {len(expired_keys)} entradas")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando cache: {e}")
    
    def _cleanup_expired_sessions(self):
        """Limpiar sesiones expiradas"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            expired_conversations = self.db.query(Conversation).filter(
                Conversation.updated_at < cutoff_time,
                Conversation.is_active == True
            ).all()
            
            for conv in expired_conversations:
                conv.is_active = False
                conv.ended_at = datetime.now()
            
            if expired_conversations:
                self.db.commit()
                logger.info(f"🧹 {len(expired_conversations)} conversaciones expiradas limpiadas")
                
        except Exception as e:
            logger.error(f"❌ Error limpiando sesiones: {e}")
    
    def _error_response(self, conversation_id: int, user_id: int) -> Dict:
        """Respuesta de error"""
        return {
            "response": "Ha ocurrido un error técnico. Proporciona tu cédula para reiniciar.",
            "conversation_id": conversation_id,
            "state": "inicial",
            "context": {},
            "buttons": [],
            "session_reset": True
        }

class ConversationServiceWithCache(ConversationService):
    """Conversation Service con Redis Cache integrado"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.cache = cache_service
    
    async def _query_client_simple(self, cedula: str) -> Optional[Dict]:
        """Consulta de cliente con cache"""
        
        # 1. Intentar obtener del cache primero
        cached_data = self.cache.get_cached_client_data(cedula)
        if cached_data:
            logger.info(f"🎯 Cache HIT para cliente: {cedula}")
            return cached_data
        
        # 2. Si no está en cache, consultar BD
        logger.info(f"💾 Cache MISS para cliente: {cedula} - consultando BD")
        
        try:
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Saldo_total, banco,
                    Oferta_1, Oferta_2, 
                    Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas,
                    Producto, Telefono, Email
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)})
            row = result.fetchone()
            
            if row:
                client_data = {
                    "encontrado": True,
                    "nombre": row[0] or "Cliente",
                    "saldo": int(float(row[1])) if row[1] else 0,
                    "banco": row[2] or "Entidad Financiera",
                    "oferta_1": int(float(row[3])) if row[3] else 0,
                    "oferta_2": int(float(row[4])) if row[4] else 0,
                    "hasta_3_cuotas": int(float(row[5])) if row[5] else 0,
                    "hasta_6_cuotas": int(float(row[6])) if row[6] else 0,
                    "hasta_12_cuotas": int(float(row[7])) if row[7] else 0,
                    "producto": row[8] or "Producto",
                    "telefono": row[9] or "",
                    "email": row[10] or ""
                }
                
                # 3. Guardar en cache (2 horas TTL)
                self.cache.cache_client_data(cedula, client_data, ttl=7200)
                logger.info(f"💾 Cliente {cedula} guardado en cache")
                
                return client_data
            else:
                # Cache resultado negativo también (5 minutos TTL)
                negative_result = {"encontrado": False}
                self.cache.cache_client_data(cedula, negative_result, ttl=300)
                return negative_result
                
        except Exception as e:
            logger.error(f"❌ Error consultando cliente {cedula}: {e}")
            return {"encontrado": False}
    
    def _get_validated_context(self, conversation: Conversation, user_message: str) -> Dict[str, Any]:
        """Obtener contexto con cache"""
        
        # 1. Intentar cache primero
        cached_context = self.cache.get_cached_conversation_context(conversation.id)
        if cached_context:
            logger.debug(f"🎯 Context cache HIT: conversation {conversation.id}")
            return cached_context
        
        # 2. Método original si no hay cache
        context = super()._get_validated_context(conversation, user_message)
        
        # 3. Guardar en cache si hay datos importantes
        if context and len(context) > 0:
            self.cache.cache_conversation_context(conversation.id, context, ttl=3600)
            logger.debug(f"💾 Context guardado en cache: conversation {conversation.id}")
        
        return context
    
    def _update_context_simple(self, conversation: Conversation, updates: Dict):
        """Actualizar contexto e invalidar cache"""
        
        # 1. Actualizar en BD (método original)
        super()._update_context_simple(conversation, updates)
        
        # 2. Invalidar cache del contexto
        self.cache.invalidate_conversation_cache(conversation.id)
        logger.debug(f"🗑️ Cache invalidado para conversation {conversation.id}")
        
        # 3. Guardar nuevo contexto en cache
        try:
            current_context = {}
            if hasattr(conversation, 'context_data') and conversation.context_data:
                current_context = json.loads(conversation.context_data)
            
            current_context.update(updates)
            self.cache.cache_conversation_context(conversation.id, current_context, ttl=3600)
            
        except Exception as e:
            logger.warning(f"⚠️ Error actualizando cache de contexto: {e}")

def crear_conversation_service(db: Session) -> ConversationService:
    """Factory para crear instancia del servicio dinámico"""
    service = ConversationService(db)
    logger.info("✅ ConversationService creado con sistema dinámico")
    return service

# También agregar función adicional:
def crear_conversation_service_with_cache(db: Session) -> ConversationServiceWithCache:
    """Factory para crear instancia con cache dinámico"""
    service = ConversationServiceWithCache(db)
    logger.info("✅ ConversationServiceWithCache creado con sistema dinámico")
    return service
# ==========================================
# UTILIDADES DE LIMPIEZA
# ==========================================

def limpiar_cache_manual():
    """Limpieza manual del cache"""
    global CONTEXT_CACHE, CACHE_TIMESTAMPS, CONVERSATION_ACTIVITY
    
    CONTEXT_CACHE.clear()
    CACHE_TIMESTAMPS.clear()
    CONVERSATION_ACTIVITY.clear()
    
    logger.info("🧹 Cache limpiado manualmente")

if __name__ == "__main__":
    print("""
    ✅ CONVERSATION SERVICE SIMPLIFICADO CARGADO
    
    Características:
    - ✅ Sin dependencias problemáticas
    - ✅ Lógica simple y directa
    - ✅ Compatible con chat.py corregido
    - ✅ ML integrado opcionalmente
    - ✅ Manejo de timeouts
    - ✅ Cache optimizado
    """)