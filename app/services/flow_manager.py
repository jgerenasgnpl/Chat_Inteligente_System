# ================================================================================
# app/services/flow_manager.py - VERSIÓN CORREGIDA Y LIMPIA
# ================================================================================

import yaml
import json
import logging
import re
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from functools import lru_cache

# ✅ IMPORTS CORREGIDOS PARA ML
try:
    from app.machine_learning.ml_service_adaptado import MLConversationEngineAdaptado
    ML_DISPONIBLE = True
except ImportError:
    ML_DISPONIBLE = False
    print("⚠️ ML Service no disponible, usando fallbacks")

try:
    from app.services.variable_service import VariableService
except ImportError:
    print("⚠️ VariableService no disponible")
    VariableService = None

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def load_knowledge_base():
    """Carga y cachea la base de conocimiento YAML una sola vez."""
    try:
        with open("app/core/base_conocimiento.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("Base de conocimiento YAML no encontrada")
        return {}

class ConfigurableFlowManagerAdaptado:
    """FlowManager adaptado a la estructura de BD existente - VERSIÓN LIMPIA"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db: Session = None):
        """Singleton thread-safe"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db: Session):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.db = db
                    self.variable_service = VariableService(db) if VariableService else None
                    self.ml_engine = None
                    self.cache = {}
                    self.cache_timestamp = 0
                    self.cache_ttl = 300  # 5 minutos
                    self._initialized = True
                    
                    # ✅ INICIALIZAR ML SI ESTÁ DISPONIBLE
                    self._initialize_ml_engine()
                    
                    logger.info("✅ FlowManager adaptado inicializado correctamente")
    
    def _initialize_ml_engine(self):
        """Inicializar ML Engine si está disponible"""
        try:
            if ML_DISPONIBLE:
                self.ml_engine = MLConversationEngineAdaptado(self.db)
                logger.info("✅ ML Engine inicializado")
            else:
                logger.warning("⚠️ ML Engine no disponible")
        except Exception as e:
            logger.error(f"❌ Error inicializando ML Engine: {e}")
            self.ml_engine = None

    # ================================================================================
    # MÉTODOS PRINCIPALES
    # ================================================================================
    
    def process_user_message(self, conversation_id: int, user_message: str, 
                           current_state: str, context_data: dict) -> dict:
        """Procesar mensaje con detección automática de cédula y ML"""
        try:
            print(f"🔍 Procesando mensaje: '{user_message}' en estado: {current_state}")
            
            # ✅ 1. DETECCIÓN AUTOMÁTICA DE CÉDULA (PRIORIDAD)
            cedula_detectada = self._detectar_cedula(user_message)
            
            if cedula_detectada:
                return self._procesar_mensaje_con_cedula(cedula_detectada, context_data, current_state)
            
            # ✅ 2. ANÁLISIS ML SI ESTÁ DISPONIBLE
            if self.ml_engine:
                ml_result = self._procesar_con_ml(user_message, context_data, current_state)
                if ml_result and ml_result.get("confianza", 0) > 0.7:
                    print(f"🤖 ML procesó mensaje con alta confianza: {ml_result.get('intencion')}")
                    return self._crear_respuesta_desde_ml(ml_result, context_data, current_state)
            
            # ✅ 3. FLUJO NORMAL SIN CÉDULA NI ML
            return self._procesar_flujo_normal(user_message, context_data, current_state)
            
        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()
            return self._create_emergency_fallback(context_data)

    def _procesar_mensaje_con_cedula(self, cedula: str, context_data: dict, current_state: str) -> dict:
        """Procesar cuando se detecta cédula en el mensaje"""
        try:
            print(f"📋 Cédula detectada: {cedula}")
            
            # Buscar cliente en BD
            datos_cliente = self._consultar_cliente_por_cedula(cedula)
            
            if datos_cliente and datos_cliente.get("cliente_encontrado", False):
                print(f"✅ Cliente encontrado: {datos_cliente.get('Nombre_del_cliente')}")
                
                # Actualizar contexto completo
                context_data.update(datos_cliente)
                context_data["documento_cliente"] = cedula
                context_data["cliente_encontrado"] = True
                
                # Transición a informar_deuda
                next_state = "informar_deuda"
                
                # Respuesta personalizada
                nombre = datos_cliente.get('Nombre_del_cliente', 'Cliente')
                saldo = self._format_currency(datos_cliente.get('saldo_total', 0))
                banco = datos_cliente.get('banco', 'tu entidad financiera')
                
                response_message = f"""¡Perfecto, {nombre}! 
                
Encontré tu información en nuestro sistema:

💼 **Entidad:** {banco}
💰 **Saldo actual:** {saldo}
📋 **Estado:** Activo para negociación

¿Te gustaría conocer las opciones especiales que tenemos disponibles para ti?"""
                
                buttons = [
                    {"id": "si", "text": "Sí, quiero conocer las opciones", "value": "acepta"},
                    {"id": "info", "text": "Primero quiero más información", "value": "mas_info"}
                ]
                
            else:
                print(f"❌ Cliente con cédula {cedula} NO encontrado")
                
                # Cliente no encontrado
                context_data["documento_cliente"] = cedula
                context_data["cliente_encontrado"] = False
                
                next_state = "cliente_no_encontrado"
                response_message = f"""He revisado nuestros registros para la cédula {cedula}.

❌ **No encontré información activa** en nuestro sistema para este documento.

Esto puede ocurrir si:
• El número de cédula tiene algún error
• La deuda ya fue pagada o transferida  
• Pertenece a otra entidad

¿Podrías verificar el número de cédula?"""
                
                buttons = [
                    {"id": "verificar", "text": "Verificar cédula", "value": "nueva_cedula"},
                    {"id": "contacto", "text": "Solicitar contacto", "value": "solicitar_contacto"}
                ]
            
            print(f"✅ Transición: cédula_detectada → {next_state}")
            
            return {
                "next_state": next_state,
                "message": response_message,
                "buttons": buttons,
                "context_data": context_data,
                "success": True,
                "datos_cliente_encontrados": context_data.get("cliente_encontrado", False)
            }
            
        except Exception as e:
            print(f"❌ Error procesando cédula {cedula}: {e}")
            return self._create_emergency_fallback(context_data)

    def _procesar_con_ml(self, mensaje: str, context_data: dict, estado_actual: str) -> dict:
        """Procesar mensaje con ML si está disponible"""
        try:
            if not self.ml_engine:
                return None
            
            resultado_ml = self.ml_engine.analizar_mensaje_completo(
                mensaje, context_data, estado_actual
            )
            
            print(f"🤖 ML Analysis: {resultado_ml.get('intencion')} (confianza: {resultado_ml.get('confianza', 0):.2f})")
            
            return resultado_ml
            
        except Exception as e:
            print(f"❌ Error en análisis ML: {e}")
            return None

    def _crear_respuesta_desde_ml(self, ml_result: dict, context_data: dict, current_state: str) -> dict:
        """Crear respuesta basada en resultado ML"""
        try:
            intencion = ml_result.get("intencion", "DESCONOCIDA")
            next_state = ml_result.get("estado_sugerido", current_state)
            respuesta_personalizada = ml_result.get("respuesta_personalizada")
            
            # Si ML tiene respuesta personalizada, usarla
            if respuesta_personalizada:
                response_message = respuesta_personalizada
            else:
                # Generar respuesta basada en intención
                response_message = self._generar_respuesta_por_intencion(intencion, context_data)
            
            # Obtener botones apropiados
            buttons = self._get_buttons_for_ml_state(next_state, intencion, context_data)
            
            return {
                "next_state": next_state,
                "message": response_message,
                "buttons": buttons,
                "context_data": context_data,
                "success": True,
                "ml_used": True,
                "intencion_detectada": intencion,
                "confianza_ml": ml_result.get("confianza", 0)
            }
            
        except Exception as e:
            print(f"❌ Error creando respuesta ML: {e}")
            return self._procesar_flujo_normal("", context_data, current_state)

    def _procesar_flujo_normal(self, user_message: str, context_data: dict, current_state: str) -> dict:
        """Procesar con flujo normal cuando no hay cédula ni ML"""
        try:
            print("📋 Procesando con flujo normal")
            
            # Cargar configuración
            config = self._load_configuration_adaptada()
            current_state_config = self._get_state_safe(config, current_state)
            
            if not current_state_config:
                print(f"⚠️ Estado {current_state} no encontrado, redirigiendo a validar_documento")
                return self._redirect_to_validate_document(context_data)
            
            # Evaluar transiciones
            next_state = self._evaluate_transitions_adaptadas(
                config, current_state, user_message, context_data
            )
            
            # Ejecutar acciones si existen
            if current_state_config.get('accion'):
                context_data = self._execute_actions_adaptadas(
                    config, current_state_config, context_data
                )
            
            # Generar respuesta usando template
            mensaje_template = current_state_config.get('mensaje_template', 'Procesando tu solicitud...')
            response_message = self._resolve_variables_adaptadas(mensaje_template, context_data)
            
            # Obtener botones
            buttons = self._get_buttons_for_state(current_state_config, context_data)
            
            print(f"✅ Transición normal: {current_state} → {next_state}")
            
            return {
                "next_state": next_state,
                "message": response_message,
                "buttons": buttons,
                "context_data": context_data,
                "success": True,
                "flujo_usado": "normal"
            }
            
        except Exception as e:
            print(f"❌ Error en flujo normal: {e}")
            return self._create_emergency_fallback(context_data)

    # ================================================================================
    # DETECCIÓN Y CONSULTAS
    # ================================================================================
    
    def _detectar_cedula(self, mensaje: str) -> Optional[str]:
        """Detectar cédula con patrones mejorados"""
        if not mensaje:
            return None
        
        mensaje = mensaje.strip()
        
        # Patrones para detectar cédulas colombianas
        patrones = [
            r'\b(\d{6,12})\b',  # Números de 6 a 12 dígitos
            r'cedula\s*:?\s*(\d{6,12})',  # "cedula: 12345678"
            r'cédula\s*:?\s*(\d{6,12})',  # "cédula: 12345678"
            r'documento\s*:?\s*(\d{6,12})',  # "documento: 12345678"
            r'cc\s*:?\s*(\d{6,12})',  # "cc: 12345678"
            r'mi\s+cedula\s+es\s+(\d{6,12})',  # "mi cedula es 12345678"
            r'mi\s+documento\s+es\s+(\d{6,12})',  # "mi documento es 12345678"
        ]
        
        for patron in patrones:
            match = re.search(patron, mensaje.lower())
            if match:
                cedula = match.group(1) if len(match.groups()) > 0 else match.group(0)
                
                # Validar longitud típica de cédula colombiana
                if 6 <= len(cedula) <= 12:
                    if not self._es_cedula_sospechosa(cedula):
                        print(f"🎯 Cédula válida detectada: {cedula}")
                        return cedula
                    else:
                        print(f"⚠️ Cédula sospechosa descartada: {cedula}")
        
        return None

    def _es_cedula_sospechosa(self, cedula: str) -> bool:
        """Verificar si una cédula parece sospechosa"""
        casos_sospechosos = [
            len(set(cedula)) == 1,  # Todos los dígitos iguales
            cedula == "123456789",   # Secuencial común
            cedula == "987654321",   # Secuencial inverso
            len(cedula) < 7,         # Muy corta para Colombia
            len(cedula) > 11,        # Muy larga para Colombia
        ]
        
        return any(casos_sospechosos)

    def _consultar_cliente_por_cedula(self, cedula: str) -> dict:
        """Consultar cliente en ConsolidadoCampañasNatalia"""
        try:
            print(f"🔍 Consultando cliente con cédula: {cedula}")
            
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Cedula, Telefono, Email,
                    Saldo_total, Capital, Intereses, 
                    Oferta_1, Oferta_2, Oferta_3, Oferta_4,
                    banco, Producto, NumerodeObligacion, Campaña
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                AND Saldo_total > 0
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                datos = {
                    "Nombre_del_cliente": result[0] or "Cliente",
                    "documento_cliente": result[1] or cedula,
                    "telefono": result[2] or "No registrado",
                    "email": result[3] or "No registrado",
                    "saldo_total": float(result[4]) if result[4] else 0,
                    "capital": float(result[5]) if result[5] else 0,
                    "intereses": float(result[6]) if result[6] else 0,
                    "oferta_1": float(result[7]) if result[7] else 0,
                    "oferta_2": float(result[8]) if result[8] else 0,
                    "oferta_3": float(result[9]) if result[9] else 0,
                    "oferta_4": float(result[10]) if result[10] else 0,
                    "banco": result[11] or "Entidad Financiera",
                    "producto": result[12] or "Producto Financiero",
                    "numero_obligacion": result[13] or "N/A",
                    "campana": result[14] or "General",
                    "cliente_encontrado": True
                }
                
                print(f"✅ Cliente encontrado: {datos['Nombre_del_cliente']} - Saldo: ${datos['saldo_total']:,.0f}")
                return datos
            else:
                print(f"❌ Cliente con cédula {cedula} no encontrado")
                return {"cliente_encontrado": False, "documento_cliente": cedula}
                
        except Exception as e:
            print(f"❌ Error consultando cliente {cedula}: {e}")
            import traceback
            traceback.print_exc()
            return {"cliente_encontrado": False, "error": str(e), "documento_cliente": cedula}

    # ================================================================================
    # CONFIGURACIÓN Y TRANSICIONES
    # ================================================================================
    
    def _load_configuration_adaptada(self) -> dict:
        """Cargar configuración usando tablas existentes"""
        try:
            current_time = time.time()
            
            # Verificar cache
            if (self.cache and 
                current_time - self.cache_timestamp < self.cache_ttl):
                return self.cache
            
            config = {
                "estados": {},
                "condiciones": {},
                "acciones": {}
            }
            
            # Cargar estados desde Estados_Conversacion
            estados_query = text("""
                SELECT nombre, mensaje_template, accion, condicion,
                       estado_siguiente_true, estado_siguiente_false, estado_siguiente_default
                FROM Estados_Conversacion 
                WHERE activo = 1
            """)
            
            estados_result = self.db.execute(estados_query).fetchall()
            
            for row in estados_result:
                config["estados"][row[0]] = {
                    "nombre": row[0],
                    "mensaje_template": row[1] or f"Estado {row[0]} procesado correctamente.",
                    "accion": row[2],
                    "condicion": row[3],
                    "estado_siguiente_true": row[4],
                    "estado_siguiente_false": row[5],
                    "estado_siguiente_default": row[6]
                }
            
            # Actualizar cache
            self.cache = config
            self.cache_timestamp = current_time
            
            logger.info(f"✅ Configuración cargada: {len(config['estados'])} estados")
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            return self._load_emergency_config()

    def _evaluate_transitions_adaptadas(self, config: dict, current_state: str, 
                                      user_message: str, context_data: dict) -> str:
        """Evaluar transiciones adaptadas"""
        try:
            # Lógica específica para estados conocidos
            if current_state == "validar_documento":
                cedula = self._detectar_cedula(user_message)
                if cedula:
                    return "informar_deuda" if context_data.get("cliente_encontrado") else "cliente_no_encontrado"
                return current_state
            
            elif current_state == "informar_deuda":
                message_lower = user_message.lower()
                if any(word in message_lower for word in ["si", "sí", "acepto", "ok", "quiero", "opciones"]):
                    return "proponer_planes_pago"
                elif any(word in message_lower for word in ["no", "despues", "luego", "más tarde"]):
                    return "gestionar_objecion"
                return current_state
            
            elif current_state == "proponer_planes_pago":
                message_lower = user_message.lower()
                if any(word in message_lower for word in ["1", "uno", "primer", "único", "pago único"]):
                    context_data["plan_seleccionado"] = "pago_unico"
                    return "generar_acuerdo"
                elif any(word in message_lower for word in ["2", "dos", "segundo", "cuotas", "plan"]):
                    context_data["plan_seleccionado"] = "plan_cuotas"
                    return "generar_acuerdo"
                elif any(word in message_lower for word in ["si", "sí", "acepto", "me interesa"]):
                    return "seleccionar_plan"
                return current_state
            
            return current_state
            
        except Exception as e:
            logger.error(f"❌ Error evaluando transiciones: {e}")
            return current_state

    def _execute_actions_adaptadas(self, config: dict, state_config: dict, context_data: dict) -> dict:
        """Ejecutar acciones adaptadas"""
        try:
            accion = state_config.get("accion")
            if not accion:
                return context_data
            
            if accion == "consultar_base_datos":
                cedula = context_data.get("documento_cliente")
                if cedula:
                    datos = self._consultar_cliente_por_cedula(cedula)
                    context_data.update(datos)
            
            elif accion == "crear_planes_pago":
                self._crear_planes_desde_ofertas(context_data)
            
            elif accion == "validar_documento":
                cedula = self._detectar_cedula(context_data.get("ultimo_mensaje", ""))
                if cedula:
                    context_data["documento_cliente"] = cedula
            
            return context_data
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando acciones: {e}")
            return context_data

    # ================================================================================
    # UTILIDADES Y HELPERS
    # ================================================================================
    
    def _generar_respuesta_por_intencion(self, intencion: str, context_data: dict) -> str:
        """Generar respuesta basada en intención ML"""
        try:
            if intencion == "CONSULTA_DEUDA":
                if context_data.get("cliente_encontrado"):
                    saldo = self._format_currency(context_data.get("saldo_total", 0))
                    banco = context_data.get("banco", "tu entidad")
                    return f"Tu saldo actual con {banco} es de {saldo}. ¿Te gustaría conocer las opciones de pago?"
                else:
                    return "Para consultar tu deuda, necesito que me proporciones tu número de cédula."
            
            elif intencion == "INTENCION_PAGO":
                return "¡Excelente! Te voy a mostrar las mejores opciones de pago disponibles para ti."
            
            elif intencion == "SOLICITUD_PLAN":
                return "Perfecto, puedo ofrecerte planes de pago personalizados. Déjame mostrarte las opciones."
            
            elif intencion == "CONFIRMACION":
                return "Perfecto, procedo con la información."
            
            elif intencion == "RECHAZO":
                return "Entiendo tu posición. ¿Te gustaría que exploremos otras alternativas?"
            
            else:
                return "Estoy aquí para ayudarte con tu situación financiera. ¿En qué puedo asistirte?"
                
        except Exception as e:
            logger.error(f"Error generando respuesta para {intencion}: {e}")
            return "¿En qué puedo ayudarte hoy?"

    def _get_buttons_for_ml_state(self, state: str, intencion: str, context_data: dict) -> list:
        """Obtener botones apropiados para estado ML"""
        try:
            if state == "proponer_planes_pago":
                return [
                    {"id": "1", "text": "Pago único con descuento", "value": "pago_unico"},
                    {"id": "2", "text": "Plan en cuotas", "value": "plan_cuotas"},
                    {"id": "info", "text": "Más información", "value": "mas_info"}
                ]
            
            elif state == "informar_deuda":
                return [
                    {"id": "si", "text": "Sí, quiero opciones", "value": "acepta"},
                    {"id": "no", "text": "No por ahora", "value": "rechaza"}
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error obteniendo botones ML: {e}")
            return []

    def _crear_planes_desde_ofertas(self, context_data: dict) -> dict:
        """Crear planes usando ofertas de ConsolidadoCampañasNatalia"""
        try:
            saldo_total = context_data.get("saldo_total", 0)
            oferta_1 = context_data.get("oferta_1", 0)
            oferta_2 = context_data.get("oferta_2", 0)
            oferta_3 = context_data.get("oferta_3", 0)
            
            planes = []
            
            # Plan 1: Pago único con descuento
            if oferta_2 > 0:
                descuento = ((saldo_total - oferta_2) / saldo_total * 100) if saldo_total > 0 else 0
                planes.append({
                    "id": "pago_unico",
                    "nombre": "Pago único con descuento",
                    "monto": oferta_2,
                    "descuento_porcentaje": round(descuento),
                    "descripcion": f"Paga ${oferta_2:,.0f} hoy y liquida con {descuento:.0f}% de descuento"
                })
            
            # Plan 2: Plan en cuotas
            if oferta_3 > 0:
                cuota_mensual = oferta_3 / 2
                planes.append({
                    "id": "plan_cuotas",
                    "nombre": "Plan en 2 cuotas",
                    "monto_total": oferta_3,
                    "cuota_mensual": cuota_mensual,
                    "num_cuotas": 2,
                    "descripcion": f"${cuota_mensual:,.0f} mensuales por 2 meses"
                })
            
            context_data["planes_disponibles"] = planes
            
            return {"success": True, "planes_generados": len(planes)}
            
        except Exception as e:
            logger.error(f"Error creando planes: {e}")
            return {"success": False, "error": str(e)}

    def _resolve_variables_adaptadas(self, template: str, context_data: dict) -> str:
        """Resolver variables con datos reales"""
        try:
            if not template:
                return "Estoy aquí para ayudarte."
            
            resolved = template
            
            # Mapeo de variables
            variable_mapping = {
                "nombre_cliente": context_data.get("Nombre_del_cliente", ""),
                "saldo_total": self._format_currency(context_data.get("saldo_total", 0)),
                "capital": self._format_currency(context_data.get("capital", 0)),
                "intereses": self._format_currency(context_data.get("intereses", 0)),
                "oferta_1": self._format_currency(context_data.get("oferta_1", 0)),
                "oferta_2": self._format_currency(context_data.get("oferta_2", 0)),
                "banco": context_data.get("banco", "tu entidad financiera"),
                "fecha_hoy": datetime.now().strftime("%d/%m/%Y"),
                "agente_nombre": "Asistente Virtual Systemgroup"
            }
            
            # Resolver variables con formato {{variable}}
            for var_name, var_value in variable_mapping.items():
                placeholder = f"{{{{{var_name}}}}}"
                if placeholder in resolved:
                    resolved = resolved.replace(placeholder, str(var_value))
            
            return resolved
            
        except Exception as e:
            logger.error(f"Error resolviendo variables: {e}")
            return template

    def _format_currency(self, amount) -> str:
        """Formatear cantidad como moneda colombiana"""
        try:
            if amount is None:
                return "$0"
            
            if isinstance(amount, str):
                amount = float(amount.replace(",", "").replace("$", ""))
            
            return f"${amount:,.0f}"
            
        except Exception:
            return "$0"

    def _get_buttons_for_state(self, state_config: dict, context_data: dict) -> list:
        """Obtener botones para un estado"""
        try:
            estado_nombre = state_config.get("nombre")
            if not estado_nombre:
                return []
            
            query = text("""
                SELECT opcion_id, texto_boton, estado_destino, orden_visualizacion
                FROM Opciones_Estado 
                WHERE estado_nombre = :estado_nombre 
                AND activo = 1
                ORDER BY orden_visualizacion
            """)
            
            result = self.db.execute(query, {"estado_nombre": estado_nombre}).fetchall()
            
            buttons = []
            for row in result:
                buttons.append({
                    "id": row[0],
                    "text": row[1],
                    "next_state": row[2],
                    "order": row[3]
                })
            
            return buttons
            
        except Exception as e:
            logger.warning(f"Error obteniendo botones: {e}")
            return []

    def _get_state_safe(self, config: dict, state_name: str) -> dict:
        """Obtener estado con validación"""
        try:
            estados = config.get("estados", {})
            
            if state_name in estados:
                return estados[state_name]
            
            if "validar_documento" in estados:
                logger.warning(f"Estado {state_name} no encontrado, usando validar_documento")
                return estados["validar_documento"]
            
            return {
                "nombre": "validar_documento",
                "mensaje_template": "¡Hola! Para ayudarte mejor, ¿podrías proporcionarme tu número de cédula?",
                "estado_siguiente_default": "informar_deuda"
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado {state_name}: {e}")
            return None

    def _redirect_to_validate_document(self, context_data: dict) -> dict:
        """Redirigir a validación de documento"""
        return {
            "next_state": "validar_documento",
            "message": "¡Hola! Para ayudarte mejor, ¿podrías proporcionarme tu número de cédula?",
            "buttons": [],
            "context_data": context_data,
            "success": True,
            "redirect_reason": "estado_no_encontrado"
        }

    def _load_emergency_config(self) -> dict:
        """Configuración de emergencia"""
        return {
            "estados": {
                "validar_documento": {
                    "nombre": "validar_documento",
                    "mensaje_template": "¡Hola! Soy tu asistente de Systemgroup. Para ayudarte mejor, ¿podrías proporcionarme tu número de cédula?",
                    "estado_siguiente_default": "informar_deuda"
                },
                "informar_deuda": {
                    "nombre": "informar_deuda",
                    "mensaje_template": "Hola {nombre_cliente}, encontré tu información. Tu saldo actual es de {saldo_total} con {banco}. ¿Te gustaría conocer las opciones de pago disponibles?",
                    "estado_siguiente_default": "proponer_planes_pago"
                },
                "proponer_planes_pago": {
                    "nombre": "proponer_planes_pago",
                    "mensaje_template": "Te ofrezco estas opciones: 1️⃣ Pago único de {oferta_2} 2️⃣ Plan en cuotas. ¿Cuál te interesa?",
                    "estado_siguiente_default": "generar_acuerdo"
                }
            }
        }

    def _create_emergency_fallback(self, context_data: dict) -> dict:
        """Respuesta de emergencia"""
        return {
            "next_state": "validar_documento",
            "message": "Hola, soy tu asistente de Systemgroup. Para ayudarte con tu situación financiera, ¿podrías proporcionarme tu número de cédula?",
            "buttons": [],
            "context_data": context_data,
            "success": False,
            "emergency_fallback": True
        }

    # ================================================================================
    # MÉTODOS PÚBLICOS DE COMPATIBILIDAD
    # ================================================================================
    
    def obtener_estado(self, state_name: str) -> dict:
        """Método público para obtener configuración de estado"""
        config = self._load_configuration_adaptada()
        return self._get_state_safe(config, state_name)
    
    def reemplazar_variables_inteligente(self, template: str, context_data: dict) -> str:
        """Método público para reemplazar variables"""
        return self._resolve_variables_adaptadas(template, context_data)

    def ejecutar_accion_configurable(self, accion: str, context_data: dict, mensaje: str, user_id: int) -> dict:
        """Ejecutar acciones configurables"""
        try:
            if accion == "consultar_base_datos":
                cedula = self._detectar_cedula(mensaje) or context_data.get("documento_cliente")
                if cedula:
                    datos = self._consultar_cliente_por_cedula(cedula)
                    context_data.update(datos)
            
            elif accion == "crear_planes_pago":
                self._crear_planes_desde_ofertas(context_data)
            
            return context_data
            
        except Exception as e:
            logger.error(f"Error ejecutando acción {accion}: {e}")
            return context_data

    def evaluar_condicion_inteligente(self, condicion: str, mensaje: str, context_data: dict) -> bool:
        """Evaluar condiciones inteligentes"""
        try:
            mensaje_lower = mensaje.lower()
            
            if condicion == "cliente_acepta":
                return any(palabra in mensaje_lower for palabra in ["si", "sí", "acepto", "ok", "está bien"])
            elif condicion == "cliente_rechaza":
                return any(palabra in mensaje_lower for palabra in ["no", "no puedo", "imposible"])
            elif condicion == "tiene_documento":
                return bool(context_data.get("documento_cliente") or self._detectar_cedula(mensaje))
            elif condicion == "cliente_encontrado":
                return context_data.get("cliente_encontrado", False)
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluando condición {condicion}: {e}")
            return False

    def obtener_opciones_estado(self, estado_nombre: str) -> list:
        """Obtener opciones/botones para un estado"""
        try:
            state_config = {"nombre": estado_nombre}
            return self._get_buttons_for_state(state_config, {})
        except Exception as e:
            logger.error(f"Error obteniendo opciones para {estado_nombre}: {e}")
            return []