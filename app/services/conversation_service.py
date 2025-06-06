import json
import re
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.conversation import Conversation
from app.services.variable_service import crear_variable_service
from app.services.flow_manager import ConfigurableFlowManagerAdaptado
from app.services.nlp_service import SimpleNLPService
import time

# ==========================================
# CACHE GLOBAL PARA CONTEXTOS
# ==========================================
CONTEXT_CACHE = {}
CACHE_TIMEOUT = 3600  # 1 hora

logger = logging.getLogger(__name__)

def guardar_contexto_con_cache(conversation_id: int, contexto: Dict[str, Any], db: Session):
    """Guardar contexto en cache Y en BD"""
    global CONTEXT_CACHE
    
    # 1. Cache en memoria PRIMERO
    CONTEXT_CACHE[conversation_id] = {
        'contexto': contexto,
        'timestamp': time.time()
    }
    
    print(f"💾 Contexto guardado en cache: {conversation_id}")
    
    # 2. También guardar en BD como backup
    try:
        # Buscar conversación existente
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            # Convertir contexto a JSON string
            contexto_json = json.dumps(contexto) if isinstance(contexto, dict) else str(contexto)
            conversation.context = contexto_json
            db.commit()
            print(f"💾 Contexto también guardado en BD")
        
    except Exception as e:
        print(f"⚠️ Error guardando en BD: {e}")

def recuperar_contexto_con_cache(conversation_id: int, db: Session = None) -> Dict[str, Any]:
    """Recuperar contexto desde cache PRIMERO, luego BD"""
    global CONTEXT_CACHE
    
    # 1. Intentar desde cache (más rápido)
    if conversation_id in CONTEXT_CACHE:
        cached = CONTEXT_CACHE[conversation_id]
        if time.time() - cached['timestamp'] < CACHE_TIMEOUT:
            print(f"✅ Contexto recuperado desde CACHE")
            return cached['contexto']
        else:
            # Cache expirado, eliminar
            del CONTEXT_CACHE[conversation_id]
    
    # 2. Intentar desde BD si hay db disponible
    if db:
        try:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if conversation and conversation.context:
                # Convertir de JSON string a dict
                if isinstance(conversation.context, str):
                    contexto = json.loads(conversation.context)
                else:
                    contexto = conversation.context or {}
                
                # Actualizar cache
                CONTEXT_CACHE[conversation_id] = {
                    'contexto': contexto,
                    'timestamp': time.time()
                }
                print(f"✅ Contexto recuperado desde BD y cacheado")
                return contexto
                
        except Exception as e:
            print(f"⚠️ Error recuperando desde BD: {e}")
    
    print(f"📋 No hay contexto para conversación {conversation_id}")
    return {}

class ConversationService:
    """Servicio principal para manejar conversaciones del chatbot"""
    
    def __init__(self, db: Session):
        self.db = db
        self.variable_service = crear_variable_service(db)
        self.flow_manager = ConfigurableFlowManagerAdaptado(db)
        self.intention_classifier = SimpleNLPService()
        
        logger.info("✅ ConversationService inicializado")
    
    async def process_message(self, conversation_id: int, user_message: str, user_id: int) -> Dict:
        """
        Procesa un mensaje del usuario y genera respuesta
        """
        try:
            logger.info(f"📩 Procesando mensaje: '{user_message}' para conversación {conversation_id}")
            
            # Obtener o crear conversación
            conversation = self.get_or_create_conversation(conversation_id, user_id)
            
            # ✅ USAR CACHE PARA RECUPERAR CONTEXTO
            contexto_cache = recuperar_contexto_con_cache(conversation_id, self.db)
            if contexto_cache:
                print(f"🔧 Contexto desde cache aplicado")
                # Aplicar contexto del cache a la conversación
                conversation.context = json.dumps(contexto_cache)
            
            logger.info(f"💬 Conversación {conversation_id} - Estado actual: {conversation.current_state}")
            logger.info(f"📋 Contexto actual: {conversation.context}")
            
            # Crear contexto para variables
            contexto_variables = self._crear_contexto_variables(conversation, user_message)
            
            # Procesar mensaje y determinar siguiente estado
            transition_result = await self._process_message_flow(conversation, user_message)
            
            # Generar respuesta
            response = self._generate_response(
                conversation.current_state, 
                transition_result.get("trigger", ""),
                contexto_variables
            )
            
            # Resolver variables en la respuesta
            response_con_variables = self.variable_service.resolver_variables(
                response, 
                contexto_variables
            )
            
            # Actualizar conversación
            conversation.current_state = transition_result.get("new_state", conversation.current_state)
            conversation.last_message = user_message
            conversation.response = response_con_variables
            
            # ✅ ACTUALIZAR CONTEXTO CON CACHE
            if transition_result.get("context_updates"):
                self._update_conversation_context_with_cache(conversation, transition_result["context_updates"])
            
            self.db.commit()
            
            logger.info(f"✅ Respuesta generada - Estado: {conversation.current_state}")
            
            return {
                "response": response_con_variables,
                "conversation_id": conversation_id,
                "state": conversation.current_state,
                "context": conversation.context,
                "buttons": self._get_buttons_for_state(conversation.current_state, contexto_variables)
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return {
                "response": "Lo siento, ha ocurrido un error. ¿Podrías intentar de nuevo?",
                "conversation_id": conversation_id,
                "state": "error",
                "context": None,
                "buttons": []
            }
    
    async def process_message_with_intention(self, conversation_id: int, user_message: str, user_id: int, intention: str) -> Dict:
        """Procesar mensaje con intención específica del botón"""
        try:
            conversation = self.get_or_create_conversation(conversation_id, user_id)
            
            # ✅ USAR CACHE PARA CONTEXTO
            contexto_cache = recuperar_contexto_con_cache(conversation_id, self.db)
            if contexto_cache:
                conversation.context = json.dumps(contexto_cache)
            
            logger.info(f"🎯 Procesando con intención específica: {intention}")
            
            # Crear contexto para variables
            contexto_variables = self._crear_contexto_variables(conversation, user_message)
            
            # Determinar nueva transición basada en la intención
            new_state, response = self._handle_button_intention(intention, conversation.current_state)
            
            # Resolver variables en la respuesta
            response_con_variables = self.variable_service.resolver_variables(response, contexto_variables)
            
            # Actualizar conversación
            conversation.current_state = new_state
            conversation.last_message = user_message
            conversation.response = response_con_variables
            self.db.commit()
            
            logger.info(f"✅ Transición por botón: {intention} → {new_state}")
            
            return {
                "response": response_con_variables,
                "conversation_id": conversation_id,
                "state": new_state,
                "context": conversation.context,
                "buttons": self._get_buttons_for_state(new_state, contexto_variables)
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje con intención: {e}")
            return {
                "response": "Lo siento, ha ocurrido un error.",
                "conversation_id": conversation_id,
                "state": "error",
                "context": None,
                "buttons": []
            }
    
    def get_or_create_conversation(self, conversation_id: int, user_id: int) -> Conversation:
        """Obtiene conversación existente o crea una nueva"""
        try:
            # Buscar conversación existente
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                # Crear nueva conversación
                conversation = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    current_state="inicial",
                    context="{}",  # JSON vacío válido
                    last_message="",
                    response=""
                )
                self.db.add(conversation)
                self.db.commit()
                logger.info(f"🆕 Nueva conversación creada: {conversation_id}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversación: {e}")
            raise
    
    def _crear_contexto_variables(self, conversation: Conversation, user_message: str) -> Dict[str, Any]:
        """Crear contexto para resolver variables"""
        contexto = {}
        
        try:
            # Obtener cédula del contexto de la conversación
            if hasattr(conversation, 'context') and conversation.context:
                context_data = json.loads(conversation.context) if isinstance(conversation.context, str) else conversation.context
                
                # Buscar cédula en diferentes lugares
                cedula = (
                    context_data.get("cedula_detectada") or 
                    context_data.get("cedula") or
                    self._extraer_cedula_del_mensaje(user_message)
                )
                
                if cedula:
                    contexto["cedula_detectada"] = str(cedula)
                    logger.info(f"📋 Cédula detectada para variables: {cedula}")
                    
                # Agregar otros datos del contexto
                if "cliente" in context_data:
                    contexto["cliente"] = context_data["cliente"]
                    
        except Exception as e:
            logger.error(f"❌ Error creando contexto de variables: {e}")
        
        return contexto
    
    def _extraer_cedula_del_mensaje(self, mensaje: str) -> Optional[str]:
        """Extrae cédula del mensaje si es un número válido"""
        # Buscar números de 7-12 dígitos (cédulas típicas)
        patron = r'\b\d{7,12}\b'
        matches = re.findall(patron, mensaje)
        return matches[0] if matches else None
    
    async def _process_message_flow(self, conversation: Conversation, user_message: str) -> Dict:
        """Procesa el flujo de la conversación"""
        try:
            # Detectar cédula si es un número
            cedula_detectada = self._extraer_cedula_del_mensaje(user_message)
            
            if cedula_detectada:
                logger.info(f"🎯 Cédula válida detectada: {cedula_detectada}")
                
                # Consultar cliente en BD
                cliente_info = await self._consultar_cliente(cedula_detectada)
                
                if cliente_info:
                    logger.info(f"✅ Cliente encontrado: {cliente_info['nombre']} - Saldo: ${cliente_info['saldo']:,.0f}")
                    
                    # Actualizar contexto
                    context_updates = {
                        "cedula_detectada": cedula_detectada,
                        "cliente": cliente_info,
                        "documento_cliente": True,
                        "cliente_encontrado": True
                    }
                    
                    return {
                        "new_state": "informar_deuda",
                        "trigger": "cedula_detectada",
                        "context_updates": context_updates
                    }
                else:
                    logger.warning(f"❌ Cliente no encontrado para cédula: {cedula_detectada}")
                    return {
                        "new_state": "cliente_no_encontrado",
                        "trigger": "cedula_no_encontrada",
                        "context_updates": {"cedula_detectada": cedula_detectada}
                    }
            
            # Si no es cédula, usar clasificador de intenciones
            ml_result = self.intention_classifier.predict(user_message)
            intention = ml_result.get("intention", "DESCONOCIDA")
            confidence = ml_result.get("confidence", 0.0)
            
            logger.info(f"🤖 ML Analysis: {intention} (confianza: {confidence:.2f})")
            
            # ✅ USAR UMBRALES MÁS BAJOS TEMPORALMENTE
            if intention == "SOLICITUD_PLAN" and confidence > 0.25:  # Bajado de 0.7 a 0.25
                return {
                    "new_state": "proponer_planes_pago",
                    "trigger": "solicitar_opciones",
                    "context_updates": {}
                }
            elif intention == "INTENCION_PAGO" and confidence > 0.25:  # Bajado de 0.7 a 0.25
                return {
                    "new_state": "proponer_planes_pago",
                    "trigger": "solicitar_opciones",
                    "context_updates": {}
                }
            elif intention == "CONFIRMACION" and confidence > 0.25:  # Bajado de 0.7 a 0.25
                return {
                    "new_state": "generar_acuerdo",
                    "trigger": "confirmar_plan",
                    "context_updates": {}
                }
            else:
                # Mantener estado actual por defecto
                logger.info(f"📋 Procesando con flujo normal")
                return {
                    "new_state": conversation.current_state,
                    "trigger": "continuar",
                    "context_updates": {}
                }
                
        except Exception as e:
            logger.error(f"❌ Error en flujo de mensaje: {e}")
            return {
                "new_state": conversation.current_state,
                "trigger": "error",
                "context_updates": {}
            }
    
    async def _consultar_cliente(self, cedula: str) -> Optional[Dict]:
        """Consulta información del cliente en la BD"""
        try:
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente,
                    Saldo_total,
                    banco,
                    Campaña,
                    Capital,
                    Intereses
                FROM ConsolidadoCampañasNatalia 
                WHERE Cedula = :cedula
            """)
            
            result = self.db.execute(query, {"cedula": cedula})
            row = result.fetchone()
            
            if row:
                return {
                    "nombre": row[0] or "Cliente",
                    "saldo": float(row[1]) if row[1] else 0.0,
                    "banco": row[2] or "Entidad Financiera",
                    "campana": row[3] or "General",
                    "capital": float(row[4]) if row[4] else 0.0,
                    "intereses": float(row[5]) if row[5] else 0.0
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente {cedula}: {e}")
            return None
    
    def _update_conversation_context_with_cache(self, conversation: Conversation, updates: Dict):
        """✅ NUEVA - Actualiza contexto usando cache"""
        try:
            # Cargar contexto actual (desde cache o BD)
            current_context = recuperar_contexto_con_cache(conversation.id, self.db)
            
            # Aplicar actualizaciones
            current_context.update(updates)
            
            # Guardar en cache Y BD
            guardar_contexto_con_cache(conversation.id, current_context, self.db)
            
            # También actualizar el objeto conversation
            conversation.context = json.dumps(current_context)
            
            logger.info(f"📋 Contexto actualizado con cache: {list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando contexto con cache: {e}")
    
    def _update_conversation_context(self, conversation: Conversation, updates: Dict):
        """Actualiza el contexto de la conversación - MÉTODO ORIGINAL"""
        try:
            # Cargar contexto actual
            current_context = json.loads(conversation.context) if conversation.context else {}
            
            # Aplicar actualizaciones
            current_context.update(updates)
            
            # Guardar contexto actualizado
            conversation.context = json.dumps(current_context)
            
            logger.info(f"📋 Contexto actualizado: {list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando contexto: {e}")
    
    def _generate_response(self, state: str, trigger: str, contexto: Dict) -> str:
        """Genera respuesta según el estado y trigger"""
        
        responses = {
            ("inicial", "cedula_detectada"): "¡Hola! Estoy procesando tu información...",
            
            ("informar_deuda", "cedula_detectada"): """¡Perfecto, {{nombre_cliente}}! Encontré tu información en nuestro sistema. 🏦

**Entidad:** {{banco}}
**Saldo actual:** {{saldo_total}}

Para continuar, necesito confirmarte tu identidad. ¿Podrías darme tu número de cédula?""",
            
            ("informar_deuda", "continuar"): """¡Perfecto, {{nombre_cliente}}! Encontré tu información en nuestro sistema. 🏦

**Entidad:** {{banco}}  
**Saldo actual:** {{saldo_total}}

¿Te gustaría que te proponga un acuerdo de pago? Tenemos excelentes opciones disponibles para ti.""",
            
            ("proponer_planes_pago", "solicitar_opciones"): """Te propongo estas opciones de pago especiales que tenemos disponibles para ti:

💰 **PAGO ÚNICO CON DESCUENTO:**
• Oferta especial: {{oferta_1}} (¡Excelente descuento!)

📅 **PLANES DE CUOTAS:**
• Plan 3 cuotas: {{hasta_3_cuotas}} cada una
• Plan 6 cuotas: {{hasta_6_cuotas}} cada una  
• Plan 12 cuotas: {{hasta_12_cuotas}} cada una

¿Cuál opción te parece más conveniente?""",
            
            ("generar_acuerdo", "confirmar_plan"): """¡Excelente elección! 

Voy a generar tu acuerdo de pago personalizado. Te enviaré los detalles completos a tu correo electrónico.

¿Confirmas que proceda con la generación del acuerdo?""",
            
            ("cliente_no_encontrado", "cedula_no_encontrada"): """No encontré información asociada a esa cédula en nuestro sistema.

Por favor, verifica que el número esté correcto o comunícate con nuestro equipo de atención al cliente al 123-456-7890."""
        }
        
        # Buscar respuesta específica
        response_key = (state, trigger)
        if response_key in responses:
            return responses[response_key]
        
        # Respuestas por defecto según estado
        default_responses = {
            "inicial": "¡Hola! Soy tu asistente de negociación. Por favor, proporciona tu número de cédula para comenzar.",
            "informar_deuda": "¿En qué más puedo ayudarte con tu proceso de negociación?",
            "proponer_planes_pago": "¿Te interesa alguna de las opciones que te propuse?",
            "generar_acuerdo": "¿Estás listo para proceder con el acuerdo?",
            "error": "Ha ocurrido un error. Por favor, intenta nuevamente."
        }
        
        return default_responses.get(state, "¿En qué puedo ayudarte?")
    
    def _handle_button_intention(self, intention: str, current_state: str) -> tuple[str, str]:
        """Maneja intenciones específicas de botones"""
        
        if intention == "proponer_planes_pago":
            return "proponer_planes_pago", """Te propongo estas opciones de pago especiales:

💰 **PAGO ÚNICO:**
• Oferta especial: {{oferta_1}}

📅 **PLANES DE CUOTAS:**
• Plan 3 cuotas: {{hasta_3_cuotas}} cada una
• Plan 6 cuotas: {{hasta_6_cuotas}} cada una
• Plan 12 cuotas: {{hasta_12_cuotas}} cada una

¿Cuál opción prefieres?"""
            
        elif intention.startswith("seleccionar_plan"):
            if "3_cuotas" in intention:
                return "generar_acuerdo", "¡Perfecto! Has elegido el plan de 3 cuotas de {{hasta_3_cuotas}} cada una. ¿Confirmas este plan?"
            elif "6_cuotas" in intention:  
                return "generar_acuerdo", "¡Excelente! Has elegido el plan de 6 cuotas de {{hasta_6_cuotas}} cada una. ¿Confirmas este plan?"
            elif "pago_unico" in intention:
                return "generar_acuerdo", "¡Excelente elección! Pago único de {{oferta_1}}. ¿Confirmas este acuerdo?"
                
        elif intention == "confirmar_acuerdo":
            return "confirmar_contacto", "¡Perfecto! Acuerdo confirmado. Te enviaremos los detalles al correo. ¿Es correcto el correo registrado?"
            
        elif intention == "finalizar_conversacion":
            return "finalizada", "Entiendo. Si cambias de opinión, estaré aquí para ayudarte. ¡Que tengas un buen día!"
        
        # Por defecto, mantener estado actual
        return current_state, "¿En qué más puedo ayudarte?"
    
    def _get_buttons_for_state(self, state: str, contexto: Dict[str, Any] = None) -> List[Dict]:
        """Generar botones según el estado actual con intenciones específicas"""
        
        if state == "informar_deuda":
            return [
                {
                    "text": "Sí, quiero conocer las opciones",
                    "action": "send_message",
                    "payload": {
                        "message": "Quiero conocer las opciones de pago",
                        "intention": "proponer_planes_pago"
                    }
                },
                {
                    "text": "No por ahora",
                    "action": "send_message", 
                    "payload": {
                        "message": "No estoy interesado ahora",
                        "intention": "finalizar_conversacion"
                    }
                }
            ]
            
        elif state == "proponer_planes_pago":
            return [
                {
                    "text": "Plan 3 cuotas", 
                    "action": "send_message",
                    "payload": {
                        "message": "Me interesa el plan de 3 cuotas",
                        "intention": "seleccionar_plan_3_cuotas"
                    }
                },
                {
                    "text": "Plan 6 cuotas",
                    "action": "send_message", 
                    "payload": {
                        "message": "Me interesa el plan de 6 cuotas", 
                        "intention": "seleccionar_plan_6_cuotas"
                    }
                },
                {
                    "text": "Pago único",
                    "action": "send_message",
                    "payload": {
                        "message": "Prefiero pago único",
                        "intention": "seleccionar_plan_pago_unico" 
                    }
                },
                {
                    "text": "Necesito más información",
                    "action": "send_message",
                    "payload": {
                        "message": "Necesito más detalles sobre las opciones",
                        "intention": "solicitar_informacion"
                    }
                }
            ]
            
        elif state == "generar_acuerdo":
            return [
                {
                    "text": "Acepto el acuerdo",
                    "action": "send_message",
                    "payload": {
                        "message": "Acepto los términos del acuerdo",
                        "intention": "confirmar_acuerdo"
                    }
                },
                {
                    "text": "Quiero modificar algo",
                    "action": "send_message",
                    "payload": {
                        "message": "Me gustaría modificar algunos términos",
                        "intention": "modificar_acuerdo"
                    }
                }
            ]
        
        return []

def crear_conversation_service(db: Session) -> ConversationService:
    """Factory para crear instancia del servicio de conversación"""
    return ConversationService(db)