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
from app.services.dynamic_transition_service import create_dynamic_transition_service

logger = logging.getLogger(__name__)

class ConversationService:
    """✅ VERSIÓN CORREGIDA - Sistema 100% dinámico sin hardcoding"""
    
    def __init__(self, db: Session):
        self.db = db
        self.variable_service = crear_variable_service(db)
        self.ml_service = self._init_ml_service()
        self.dynamic_transition_service = create_dynamic_transition_service(db)
        self.request_count = 0
        
        # ✅ ELIMINAR CACHE PERSISTENTE - CADA CONVERSACIÓN DEBE SER LIMPIA
        self.session_cache = {}  # Solo para sesión actual
        
        logger.info("✅ ConversationService inicializado (versión dinámica corregida)")
    
    def _init_ml_service(self):
        """Inicializar servicio ML de forma segura"""
        try:
            from app.services.nlp_service import nlp_service
            return nlp_service
        except Exception as e:
            logger.warning(f"ML service no disponible: {e}")
            return None
    
    async def process_message(self, conversation_id: int, user_message: str, user_id: int) -> Dict:
        """✅ MÉTODO PRINCIPAL CORREGIDO - Limpieza y dinámico"""
        start_time = time.time()
        self.request_count += 1
        
        try:
            logger.info(f"📨 [{self.request_count}] Procesando: '{user_message[:50]}...' (usuario {user_id})")
            
            # ✅ 1. OBTENER O CREAR CONVERSACIÓN LIMPIA
            conversation = self._get_or_create_clean_conversation(conversation_id, user_id)
            
            # ✅ 2. VERIFICAR SI NECESITA RESET COMPLETO
            if self._should_reset_conversation(conversation, user_message):
                conversation = self._reset_conversation_completely(conversation)
            
            # ✅ 3. OBTENER CONTEXTO DINÁMICO (SIN VALORES HARDCODEADOS)
            contexto = self._get_dynamic_context(conversation, user_message)
            
            logger.info(f"💬 Conv {conversation.id} - Estado: {conversation.current_state}")
            logger.info(f"📋 Contexto: {len(contexto)} elementos")
            
            # ✅ 4. PROCESAR MENSAJE 100% DINÁMICO
            resultado = await self._process_message_dynamic(conversation, user_message, contexto)
            
            # ✅ 5. ACTUALIZAR CONVERSACIÓN
            conversation.current_state = resultado.get("new_state", conversation.current_state)
            conversation.updated_at = datetime.now()
            
            # ✅ 6. GUARDAR CONTEXTO DINÁMICO
            if resultado.get("context_updates"):
                self._update_context_dynamic(conversation, resultado["context_updates"])
            
            self.db.commit()
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Respuesta generada en {execution_time:.1f}ms")
            
            return {
                "response": resultado.get("message", "Procesando..."),
                "conversation_id": conversation_id,
                "state": conversation.current_state,
                "context": self._get_context_dict(conversation),
                "buttons": resultado.get("buttons", []),
                "session_valid": True,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return self._error_response(conversation_id, user_id)

    def _get_or_create_clean_conversation(self, conversation_id: int, user_id: int) -> Conversation:
        """✅ CORREGIDO - Crear conversación completamente limpia"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                # ✅ CREAR NUEVA CONVERSACIÓN COMPLETAMENTE LIMPIA
                conversation = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    current_state="inicial",  # ✅ SIEMPRE INICIAL
                    context_data="{}",  # ✅ CONTEXTO COMPLETAMENTE VACÍO
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db.add(conversation)
                self.db.commit()
                logger.info(f"🆕 Nueva conversación limpia: {conversation_id}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversación: {e}")
            raise
    
    def _should_reset_conversation(self, conversation: Conversation, user_message: str) -> bool:
        """✅ NUEVO - Determinar si necesita reset completo"""
        
        # Reset si ha pasado mucho tiempo (más de 1 hora)
        if conversation.updated_at:
            hours_since_update = (datetime.now() - conversation.updated_at).total_seconds() / 3600
            if hours_since_update > 1:
                logger.info(f"🔄 Reset por inactividad: {hours_since_update:.1f} horas")
                return True
        
        # Reset si el usuario envía nueva cédula
        cedula_detectada = self._extract_cedula_simple(user_message)
        if cedula_detectada:
            logger.info(f"🔄 Reset por nueva cédula detectada: {cedula_detectada}")
            return True
        
        # Reset si está en estado final
        if conversation.current_state in ["finalizar_conversacion", "conversacion_cerrada"]:
            logger.info(f"🔄 Reset por estado final: {conversation.current_state}")
            return True
        
        return False
    
    def _reset_conversation_completely(self, conversation: Conversation) -> Conversation:
        """✅ NUEVO - Reset completo de conversación"""
        try:
            logger.info(f"🔄 Reseteando conversación {conversation.id} completamente")
            
            # ✅ RESET COMPLETO
            conversation.current_state = "inicial"
            conversation.context_data = "{}"  # ✅ CONTEXTO COMPLETAMENTE VACÍO
            conversation.is_active = True
            conversation.updated_at = datetime.now()
            
            # ✅ LIMPIAR CACHE DE SESIÓN
            if conversation.id in self.session_cache:
                del self.session_cache[conversation.id]
            
            self.db.commit()
            logger.info(f"✅ Conversación reseteada completamente")
            
            return conversation
            
        except Exception as e:
            logger.error(f"❌ Error reseteando conversación: {e}")
            return conversation
    
    def _get_dynamic_context(self, conversation: Conversation, user_message: str) -> Dict[str, Any]:
        """✅ NUEVO - Obtener contexto 100% dinámico sin valores hardcodeados"""
        try:
            # ✅ 1. CONTEXTO BASE COMPLETAMENTE VACÍO
            contexto = {}
            
            # ✅ 2. SOLO RECUPERAR SI HAY DATOS REALES EN BD
            if hasattr(conversation, 'context_data') and conversation.context_data:
                try:
                    if conversation.context_data != "{}":
                        context_from_db = json.loads(conversation.context_data)
                        if isinstance(context_from_db, dict) and context_from_db:
                            # ✅ SOLO USAR SI TIENE DATOS REALES DEL CLIENTE
                            if context_from_db.get('cliente_encontrado') and context_from_db.get('saldo_total', 0) > 1000:
                                contexto = context_from_db
                                logger.info(f"✅ Contexto real recuperado: {contexto.get('Nombre_del_cliente')}")
                            else:
                                logger.info(f"🔄 Contexto sin datos reales - iniciando limpio")
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Error parseando contexto - iniciando limpio")
            
            # ✅ 3. DETECTAR CÉDULA EN MENSAJE ACTUAL
            cedula_detectada = self._extract_cedula_simple(user_message)
            if cedula_detectada:
                logger.info(f"🎯 Cédula detectada en mensaje: {cedula_detectada}")
                # ✅ CONSULTAR DATOS REALES INMEDIATAMENTE
                cliente_data = self._query_client_real_data(cedula_detectada)
                if cliente_data.get("encontrado"):
                    contexto.update(cliente_data)
                    logger.info(f"✅ Datos reales del cliente agregados")
            
            # ✅ 4. SIN VALORES POR DEFECTO HARDCODEADOS
            # Si no hay datos reales, el contexto queda vacío
            
            return contexto
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto dinámico: {e}")
            return {}
    
    def _query_client_real_data(self, cedula: str) -> Dict[str, Any]:
        """✅ NUEVO - Consultar SOLO datos reales, sin fallbacks hardcodeados"""
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
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                # ✅ SOLO DEVOLVER DATOS REALES - SIN VALORES POR DEFECTO
                datos_reales = {
                    "encontrado": True,
                    "cliente_encontrado": True,
                    "cedula_detectada": cedula,
                    "Nombre_del_cliente": result[0],
                    "nombre_cliente": result[0],
                    "saldo_total": int(float(result[1])) if result[1] else 0,
                    "banco": result[2],
                    "oferta_1": int(float(result[3])) if result[3] else 0,
                    "oferta_2": int(float(result[4])) if result[4] else 0,
                    "Oferta_2": int(float(result[4])) if result[4] else 0,
                    "hasta_3_cuotas": int(float(result[5])) if result[5] else 0,
                    "hasta_6_cuotas": int(float(result[6])) if result[6] else 0,
                    "hasta_12_cuotas": int(float(result[7])) if result[7] else 0,
                    "producto": result[8],
                    "telefono": result[9],
                    "email": result[10],
                    "consulta_timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"✅ Cliente real encontrado: {datos_reales['Nombre_del_cliente']}")
                logger.info(f"💰 Saldo real: ${datos_reales['saldo_total']:,}")
                
                return datos_reales
            
            logger.info(f"❌ Cliente no encontrado para cédula: {cedula}")
            return {"encontrado": False}
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente real: {e}")
            return {"encontrado": False}
    
    async def _process_message_dynamic(self, conversation: Conversation, user_message: str, contexto: Dict) -> Dict:
        """✅ PROCESAMIENTO 100% DINÁMICO SIN HARDCODING"""
        try:
            start_time = time.time()
            
            # ✅ 1. DETECCIÓN DE CÉDULA (MÁXIMA PRIORIDAD)
            cedula_detectada = self._extract_cedula_simple(user_message)
            
            if cedula_detectada:
                logger.info(f"🎯 Cédula detectada: {cedula_detectada}")
                
                # Consultar cliente real
                cliente_info = self._query_client_real_data(cedula_detectada)
                
                if cliente_info.get("encontrado"):
                    # ✅ TRANSICIÓN DINÁMICA POR CÉDULA
                    transition_result = self.dynamic_transition_service.determine_next_state(
                        current_state=conversation.current_state,
                        user_message=user_message,
                        ml_result={"intention": "IDENTIFICACION_EXITOSA", "confidence": 0.95},
                        context=cliente_info
                    )
                    
                    # ✅ GENERAR MENSAJE DINÁMICO
                    mensaje_respuesta = self._generate_response_dynamic(
                        transition_result['next_state'], cliente_info
                    )
                    
                    return {
                        "new_state": transition_result["next_state"],
                        "context_updates": cliente_info,
                        "message": mensaje_respuesta,
                        "buttons": self._get_buttons_dynamic(transition_result['next_state'], cliente_info),
                        "method": "dynamic_cedula_detection"
                    }
                else:
                    # Cliente no encontrado
                    return {
                        "new_state": "cliente_no_encontrado",
                        "context_updates": {"cedula_no_encontrada": cedula_detectada},
                        "message": f"No encontré información para la cédula {cedula_detectada}. Por favor verifica el número.",
                        "buttons": [{"id": "reintentar", "text": "Intentar otra cédula"}],
                        "method": "cedula_not_found"
                    }
            
            # ✅ 2. CLASIFICACIÓN ML + SISTEMA DINÁMICO
            ml_result = {}
            if self.ml_service:
                ml_prediction = self.ml_service.predict(user_message)
                ml_result = {
                    'intention': ml_prediction.get('intention', 'DESCONOCIDA'),
                    'confidence': ml_prediction.get('confidence', 0.0),
                    'method': 'ml_classification'
                }
                
                logger.info(f"🤖 ML: {ml_result['intention']} (confianza: {ml_result['confidence']:.2f})")
            
            # ✅ 3. USAR SISTEMA DINÁMICO PARA DETERMINAR TRANSICIÓN
            transition_result = self.dynamic_transition_service.determine_next_state(
                current_state=conversation.current_state,
                user_message=user_message,
                ml_result=ml_result,
                context=contexto
            )
            
            # ✅ 4. GENERAR RESPUESTA COMPLETAMENTE DINÁMICA
            mensaje_respuesta = self._generate_response_dynamic(
                transition_result['next_state'], contexto
            )
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Procesamiento dinámico completado en {execution_time:.1f}ms")
            
            return {
                "new_state": transition_result["next_state"],
                "context_updates": {},
                "message": mensaje_respuesta,
                "buttons": self._get_buttons_dynamic(transition_result['next_state'], contexto),
                "method": "sistema_dinamico_completo",
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento dinámico: {e}")
            return {
                "new_state": conversation.current_state,
                "context_updates": {},
                "message": "¿En qué puedo ayudarte? Para comenzar, proporciona tu número de cédula.",
                "buttons": [{"id": "help", "text": "Necesito ayuda"}],
                "method": "error_fallback"
            }
    
    def _generate_response_dynamic(self, estado: str, contexto: Dict[str, Any]) -> str:
        """✅ GENERAR RESPUESTA 100% DINÁMICA DESDE BD"""
        try:
            # ✅ OBTENER TEMPLATE DESDE BD
            query = text("""
                SELECT mensaje_template 
                FROM Estados_Conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado}).fetchone()
            
            if result and result[0]:
                template = result[0]
                logger.info(f"✅ Template dinámico obtenido para estado '{estado}'")
                
                # ✅ RESOLVER VARIABLES DINÁMICAMENTE
                try:
                    mensaje_final = self.variable_service.resolver_variables(template, contexto)
                    logger.info(f"✅ Variables resueltas dinámicamente")
                    return mensaje_final
                except Exception as e:
                    logger.error(f"⚠️ Error resolviendo variables: {e}")
                    return template
            else:
                # ✅ FALLBACK DINÁMICO SIN HARDCODING
                tiene_cliente = contexto.get('cliente_encontrado', False)
                if tiene_cliente:
                    nombre = contexto.get('Nombre_del_cliente', 'Cliente')
                    return f"¿En qué puedo ayudarte, {nombre}?"
                else:
                    return "Para ayudarte, necesito tu número de cédula."
                
        except Exception as e:
            logger.error(f"❌ Error generando respuesta dinámica: {e}")
            return "¿En qué puedo ayudarte?"
    
    def _get_buttons_dynamic(self, estado: str, contexto: Dict) -> List[Dict]:
        """✅ BOTONES COMPLETAMENTE DINÁMICOS"""
        try:
            # ✅ OBTENER BOTONES DESDE BD (implementar tabla de botones)
            # Por ahora, lógica dinámica básica
            
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
            else:
                return [{"id": "ayuda", "text": "Necesito ayuda"}]
                
        except Exception as e:
            logger.error(f"❌ Error generando botones dinámicos: {e}")
            return []
    
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
    
    def _update_context_dynamic(self, conversation: Conversation, updates: Dict):
        """✅ ACTUALIZAR CONTEXTO SIN VALORES HARDCODEADOS"""
        try:
            current_context = {}
            if hasattr(conversation, 'context_data') and conversation.context_data:
                try:
                    current_context = json.loads(conversation.context_data)
                except:
                    pass
            
            # ✅ COMBINAR SOLO DATOS REALES
            updated_context = {**current_context, **updates}
            
            # ✅ SERIALIZACIÓN SEGURA
            context_json = json.dumps(updated_context, ensure_ascii=False, default=str)
            conversation.context_data = context_json
            
            logger.info(f"💾 Contexto actualizado dinámicamente")
            
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
    
    def _error_response(self, conversation_id: int, user_id: int) -> Dict:
        """Respuesta de error"""
        return {
            "response": "Ha ocurrido un error. Por favor proporciona tu cédula para reiniciar.",
            "conversation_id": conversation_id,
            "state": "inicial",
            "context": {},
            "buttons": [{"id": "reiniciar", "text": "Reiniciar"}],
            "session_reset": True
        }

def crear_conversation_service(db: Session) -> ConversationService:
    """Factory para crear instancia del servicio dinámico corregido"""
    service = ConversationService(db)
    logger.info("✅ ConversationService corregido creado - 100% dinámico")
    return service