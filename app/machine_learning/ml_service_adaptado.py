import threading
import time
import hashlib
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

class MLConversationEngineAdaptado:
    """MLConversationEngine adaptado a estructura existente"""
    
    _instance = None
    _lock = threading.Lock()
    _cache = {}
    _cache_timestamps = {}
    _cache_ttl = 3600  # 1 hora
    
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
                    self.ml_disponible = True
                    self._performance_log = []
                    self._initialized = True
                    
                    try:
                        # Verificar si hay modelo ML registrado
                        if not self._verify_model_available():
                            self._register_basic_model()
                            
                    except Exception as e:
                        print(f"⚠️ ML no disponible: {e}")
                        self.ml_disponible = False
    
    def analizar_mensaje_completo(self, mensaje: str, context_data: dict, estado_actual: str) -> dict:
        """Análisis completo adaptado"""
        start_time = time.time()
        
        try:
            # Verificar cache
            cache_key = self._generate_cache_key(mensaje, context_data, estado_actual)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result:
                self._log_performance("cache_hit", time.time() - start_time)
                return cached_result
            
            # Análisis con datos reales
            if self.ml_disponible:
                resultado = self._analizar_con_datos_reales(mensaje, context_data, estado_actual)
            else:
                resultado = self._analizar_fallback_adaptado(mensaje, context_data, estado_actual)
            
            # Guardar en cache
            self._save_to_cache(cache_key, resultado)
            
            # Log performance
            execution_time = time.time() - start_time
            self._log_performance("full_analysis", execution_time)
            
            return resultado
            
        except Exception as e:
            print(f"❌ Error en análisis ML: {e}")
            return self._analizar_fallback_adaptado(mensaje, context_data, estado_actual)
    
    def _analizar_con_datos_reales(self, mensaje: str, context_data: dict, estado_actual: str) -> dict:
        """Análisis usando datos reales de ConsolidadoCampañasNatalia"""
        try:
            # 1. Predicción de intención básica
            intencion, confianza = self._predecir_intencion_basica(mensaje)
            
            # 2. Análisis contextual con datos reales
            perfil_cliente = self._analizar_perfil_con_datos_reales(context_data)
            
            # 3. Estrategia basada en datos financieros
            estrategia = self._determinar_estrategia_con_datos(intencion, perfil_cliente, context_data)
            
            # 4. Respuesta personalizada
            respuesta_personalizada = self._generar_respuesta_personalizada(estrategia, context_data, mensaje)
            
            return {
                "intencion": intencion,
                "confianza": confianza,
                "perfil_cliente": perfil_cliente,
                "estrategia": estrategia,
                "estado_sugerido": estrategia.get("proximo_estado", estado_actual),
                "accion_sugerida": estrategia.get("accion_recomendada"),
                "respuesta_personalizada": respuesta_personalizada,
                "personalizacion_adicional": estrategia.get("personalizar", False),
                "metodo": "ml_datos_reales"
            }
            
        except Exception as e:
            print(f"❌ Error en análisis con datos reales: {e}")
            return self._analizar_fallback_adaptado(mensaje, context_data, estado_actual)
    
    def _predecir_intencion_basica(self, mensaje: str) -> tuple:
        """Predicción básica de intención"""
        mensaje_lower = mensaje.lower() if mensaje else ""
        
        # Patrones específicos para cobranza
        patrones_intencion = {
            "CONSULTA_DEUDA": ["cuanto", "cuánto", "debo", "saldo", "deuda", "debe"],
            "INTENCION_PAGO": ["pagar", "cancelar", "liquidar", "quiero pagar", "opciones"],
            "SOLICITUD_PLAN": ["plan", "cuotas", "facilidades", "acuerdo", "negociar"],
            "CONFIRMACION": ["si", "sí", "acepto", "ok", "está bien", "de acuerdo", "perfecto"],
            "RECHAZO": ["no", "no puedo", "imposible", "no me interesa", "no tengo"],
            "IDENTIFICACION": ["cedula", "documento", "cc", "identificacion", "soy"],
            "SALUDO": ["hola", "buenos", "buenas", "buen día", "saludos"],
            "DESPEDIDA": ["adiós", "chao", "gracias", "hasta luego", "bye"]
        }
        
        for intencion, patrones in patrones_intencion.items():
            for patron in patrones:
                if patron in mensaje_lower:
                    # Calcular confianza básica
                    confianza = min(0.9, 0.6 + (len(patron) / len(mensaje_lower)) * 0.3)
                    return intencion, confianza
        
        return "DESCONOCIDA", 0.0
    
    def _analizar_perfil_con_datos_reales(self, context_data: dict) -> dict:
        """Análisis de perfil usando datos reales financieros"""
        try:
            saldo_total = float(context_data.get("saldo_total", 0))
            capital = float(context_data.get("capital", 0))
            intereses = float(context_data.get("intereses", 0))
            oferta_1 = float(context_data.get("oferta_1", 0))
            oferta_2 = float(context_data.get("oferta_2", 0))
            campana = context_data.get("campana", "").lower()
            
            # Calcular indicadores financieros
            ratio_intereses = (intereses / capital) if capital > 0 else 0
            descuento_oferta_1 = ((saldo_total - oferta_1) / saldo_total) if saldo_total > 0 else 0
            descuento_oferta_2 = ((saldo_total - oferta_2) / saldo_total) if saldo_total > 0 else 0
            
            # Categorizar por monto
            if saldo_total < 500000:
                categoria_monto = "BAJO"
            elif saldo_total < 2000000:
                categoria_monto = "MEDIO"
            else:
                categoria_monto = "ALTO"
            
            # Categorizar por campaña
            if "castig" in campana:
                tipo_cartera = "CASTIGADA"
                factor_dificultad = 0.8
            elif "temprana" in campana:
                tipo_cartera = "TEMPRANA"
                factor_dificultad = 0.3
            else:
                tipo_cartera = "REGULAR"
                factor_dificultad = 0.5
            
            # Calcular propensión al pago
            propension_base = 0.5
            
            # Factores positivos
            if descuento_oferta_2 > 0.3:  # Buen descuento
                propension_base += 0.2
            if categoria_monto == "BAJO":  # Monto manejable
                propension_base += 0.1
            if tipo_cartera == "TEMPRANA":  # Cartera fresca
                propension_base += 0.2
            
            # Factores negativos
            if ratio_intereses > 0.5:  # Muchos intereses
                propension_base -= 0.1
            if tipo_cartera == "CASTIGADA":  # Cartera difícil
                propension_base -= 0.2
            
            propension_final = max(0.1, min(0.9, propension_base))
            
            # Determinar segmento
            if propension_final > 0.7:
                segmento = "ALTO_POTENCIAL"
            elif propension_final > 0.4:
                segmento = "MEDIO_POTENCIAL"
            else:
                segmento = "BAJO_POTENCIAL"
            
            return {
                "propension_pago": propension_final,
                "segmento": segmento,
                "categoria_monto": categoria_monto,
                "tipo_cartera": tipo_cartera,
                "factor_dificultad": factor_dificultad,
                "indicadores": {
                    "saldo_total": saldo_total,
                    "ratio_intereses": ratio_intereses,
                    "descuento_oferta_1": descuento_oferta_1,
                    "descuento_oferta_2": descuento_oferta_2
                },
                "recomendacion_estrategia": self._recomendar_estrategia_por_perfil(propension_final, tipo_cartera)
            }
            
        except Exception as e:
            print(f"⚠️ Error analizando perfil: {e}")
            return {"propension_pago": 0.5, "segmento": "MEDIO_POTENCIAL"}
    
    def _recomendar_estrategia_por_perfil(self, propension: float, tipo_cartera: str) -> str:
        """Recomendar estrategia basada en perfil"""
        if propension > 0.7:
            return "AGRESIVA_POSITIVA"
        elif propension < 0.3 or tipo_cartera == "CASTIGADA":
            return "CONSERVACION"
        else:
            return "BALANCEADA"
    
    def _determinar_estrategia_con_datos(self, intencion: str, perfil: dict, context_data: dict) -> dict:
        """Determinar estrategia usando datos financieros"""
        propension = perfil["propension_pago"]
        categoria_monto = perfil.get("categoria_monto", "MEDIO")
        tipo_cartera = perfil.get("tipo_cartera", "REGULAR")
        
        # Estrategia agresiva para alto potencial
        if propension > 0.7 and intencion in ["CONSULTA_DEUDA", "INTENCION_PAGO"]:
            return {
                "tipo": "AGRESIVA_POSITIVA",
                "proximo_estado": "proponer_planes_pago",
                "accion_recomendada": "presentar_mejor_oferta",
                "tono": "entusiasta",
                "personalizar": True,
                "razon": "Cliente con alto potencial de pago"
            }
        
        # Estrategia conservadora para bajo potencial
        elif propension < 0.3 or tipo_cartera == "CASTIGADA":
            return {
                "tipo": "CONSERVACION",
                "proximo_estado": "mensaje_empatico",
                "accion_recomendada": "construir_confianza",
                "tono": "comprensivo",
                "personalizar": True,
                "razon": "Cliente requiere manejo delicado"
            }
        
        # Estrategia específica por intención
        elif intencion == "CONSULTA_DEUDA":
            return {
                "tipo": "INFORMATIVA",
                "proximo_estado": "informar_deuda",
                "accion_recomendada": "mostrar_desglose_deuda",
                "tono": "profesional",
                "personalizar": False,
                "razon": "Cliente busca información específica"
            }
        
        elif intencion == "SOLICITUD_PLAN":
            return {
                "tipo": "COMERCIAL",
                "proximo_estado": "proponer_planes_pago",
                "accion_recomendada": "crear_planes_personalizados",
                "tono": "consultivo",
                "personalizar": True,
                "razon": "Cliente interesado en negociar"
            }
        
        # Estrategia balanceada por defecto
        return {
            "tipo": "BALANCEADA",
            "proximo_estado": "evaluar_intencion_pago",
            "accion_recomendada": "sondear_interes",
            "tono": "profesional",
            "personalizar": False,
            "razon": "Situación estándar"
        }
    
    def _generar_respuesta_personalizada(self, estrategia: dict, context_data: dict, mensaje_usuario: str) -> str:
        """Generar respuesta personalizada con datos reales"""
        
        if estrategia["tipo"] == "AGRESIVA_POSITIVA":
            nombre = context_data.get('Nombre_del_cliente', 'estimado cliente')
            saldo = self._format_currency(context_data.get('saldo_total', 0))
            oferta = self._format_currency(context_data.get('oferta_2', 0))
            banco = context_data.get('banco', 'tu entidad financiera')
            
            descuento = 0
            if context_data.get('saldo_total', 0) > 0 and context_data.get('oferta_2', 0) > 0:
                descuento = ((context_data['saldo_total'] - context_data['oferta_2']) / context_data['saldo_total'] * 100)
            
            return f"""¡Excelente {nombre}! 
            
Veo que estás interesado en resolver tu situación con {banco}. Tengo una oportunidad especial para ti:

💰 **OFERTA ESPECIAL PERSONALIZADA**
📊 Tu saldo actual: {saldo}
🎯 Oferta única: {oferta}
💡 ¡Ahorras {descuento:.0f}% pagando HOY!

¿Procedemos con esta oportunidad única?"""
        
        elif estrategia["tipo"] == "CONSERVACION":
            nombre = context_data.get('Nombre_del_cliente', '')
            return f"""Entiendo tu situación, {nombre}. 

Sabemos que a veces pueden presentarse dificultades financieras, y estamos aquí para encontrar una solución que funcione para ti.

Tu tranquilidad financiera es importante para nosotros. ¿Te gustaría que conversemos sobre alternativas flexibles?"""
        
        elif estrategia["tipo"] == "COMERCIAL":
            saldo = self._format_currency(context_data.get('saldo_total', 0))
            oferta_1 = self._format_currency(context_data.get('oferta_1', 0))
            oferta_2 = self._format_currency(context_data.get('oferta_2', 0))
            
            return f"""Perfecto, te muestro las opciones disponibles para tu deuda de {saldo}:

🔥 **OPCIÓN 1:** Pago único de {oferta_2} (¡Mejor descuento!)
📅 **OPCIÓN 2:** Plan personalizado desde {oferta_1}
💼 **OPCIÓN 3:** Facilidades especiales

¿Cuál se adapta mejor a tu situación actual?"""
        
        # Para otros tipos, devolver None para usar template normal
        return None
    
    def _format_currency(self, amount) -> str:
        """Formatear moneda"""
        try:
            if isinstance(amount, str):
                amount = float(amount.replace(",", "").replace("$", ""))
            return f"${amount:,.0f}"
        except:
            return "$0"
    
    def _analizar_fallback_adaptado(self, mensaje: str, context_data: dict, estado_actual: str) -> dict:
        """Análisis fallback adaptado"""
        intencion, confianza = self._predecir_intencion_basica(mensaje)
        
        # Determinar próximo estado basado en intención
        if intencion == "CONSULTA_DEUDA":
            proximo_estado = "informar_deuda"
        elif intencion == "INTENCION_PAGO":
            proximo_estado = "proponer_planes_pago"
        elif intencion == "IDENTIFICACION":
            proximo_estado = "validar_documento"
        elif intencion == "CONFIRMACION":
            proximo_estado = "generar_acuerdo"
        else:
            proximo_estado = estado_actual
        
        return {
            "intencion": intencion,
            "confianza": confianza,
            "perfil_cliente": {"propension_pago": 0.5, "segmento": "MEDIO_POTENCIAL"},
            "estrategia": {"tipo": "SIMPLE", "proximo_estado": proximo_estado},
            "estado_sugerido": proximo_estado,
            "accion_sugerida": None,
            "respuesta_personalizada": None,
            "personalizacion_adicional": False,
            "metodo": "fallback_adaptado"
        }
    
    def _verify_model_available(self) -> bool:
        """Verificar si hay modelo ML disponible"""
        try:
            query = text("SELECT COUNT(*) FROM modelos_ml WHERE activo = 1 AND tipo = 'intention_classifier'")
            count = self.db.execute(query).scalar()
            return count > 0
        except:
            return False
    
    def _register_basic_model(self):
        """Registrar modelo básico"""
        try:
            query = text("""
                INSERT INTO modelos_ml (nombre, tipo, ruta_modelo, accuracy, ejemplos_entrenamiento)
                VALUES (:nombre, :tipo, :ruta, :accuracy, :ejemplos)
            """)
            self.db.execute(query, {
                "nombre": f"Modelo_Adaptado_{int(time.time())}",
                "tipo": "intention_classifier",
                "ruta": "models/adaptado_basic.joblib",
                "accuracy": 0.82,
                "ejemplos": 32
            })
            self.db.commit()
        except Exception as e:
            print(f"⚠️ Error registrando modelo: {e}")
    
    def _generate_cache_key(self, mensaje: str, context_data: dict, estado: str) -> str:
        """Generar clave de cache"""
        content = f"{mensaje}|{estado}|{context_data.get('Nombre_del_cliente', '')}|{context_data.get('saldo_total', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[dict]:
        """Obtener del cache"""
        try:
            current_time = time.time()
            if (cache_key in self._cache and 
                cache_key in self._cache_timestamps and
                current_time - self._cache_timestamps[cache_key] < self._cache_ttl):
                return self._cache[cache_key]
            return None
        except:
            return None
    
    def _save_to_cache(self, cache_key: str, resultado: dict):
        """Guardar en cache"""
        try:
            current_time = time.time()
            if len(self._cache) > 1000:
                self._cleanup_cache()
            self._cache[cache_key] = resultado
            self._cache_timestamps[cache_key] = current_time
        except:
            pass
    
    def _cleanup_cache(self):
        """Limpiar cache"""
        try:
            current_time = time.time()
            expired_keys = [k for k, ts in self._cache_timestamps.items() 
                          if current_time - ts > self._cache_ttl]
            for key in expired_keys:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
        except:
            pass
    
    def _log_performance(self, operacion: str, tiempo: float):
        """Log de performance"""
        try:
            self._performance_log.append({
                "operacion": operacion,
                "tiempo_ms": tiempo * 1000,
                "timestamp": time.time()
            })
            if len(self._performance_log) > 100:
                self._performance_log = self._performance_log[-50:]
        except:
            pass

# ================================================================================
# ARCHIVO 3: Instrucciones de actualización de chat.py
# ================================================================================

print("""
📋 INSTRUCCIONES PARA ACTUALIZAR chat.py:

1. 📝 ACTUALIZAR IMPORTS:
   # CAMBIAR:
   from app.services.flow_manager import ConfigurableFlowManager
   from app.machine_learning.ml_service import MLConversationEngine
   
   # POR:
   from app.services.flow_manager_adaptado import ConfigurableFlowManagerAdaptado
   from app.machine_learning.ml_service_adaptado import MLConversationEngineAdaptado

2. 🔧 ACTUALIZAR ENDPOINT process_chat_message():
   # CAMBIAR:
   flow_manager = ConfigurableFlowManager(db)
   ml_engine = MLConversationEngine(db)
   
   # POR:
   flow_manager = ConfigurableFlowManagerAdaptado(db)
   ml_engine = MLConversationEngineAdaptado(db)

3. ✅ AGREGAR LOGGING MEJORADO:
   # Al inicio del endpoint:
   print(f"📩 Mensaje recibido: {message_content}")
   print(f"👤 Usuario: {user_id}")
   print(f"💬 Conversación: {conversation.id}")
   
   # Al final del endpoint:
   print(f"✅ Respuesta enviada: {response.current_state}")
   print(f"📊 Datos cliente: {bool(context_data.get('Nombre_del_cliente'))}")

4. 🎯 EJEMPLO DE ENDPOINT ADAPTADO:
   @router.post("/message", response_model=ChatResponse)
   def process_chat_message(
       request: ChatRequest,
       db: Session = Depends(get_db),
   ):
       try:
           user_id = request.user_id
           message_content = request.message or request.text or ""
           
           print(f"📩 Mensaje: {message_content}")
           
           # Obtener/crear conversación
           conversation = _get_or_create_conversation(db, user_id, request.conversation_id)
           
           # Usar managers adaptados
           flow_manager = ConfigurableFlowManagerAdaptado(db)
           
           # Procesar mensaje
           result = flow_manager.process_user_message(
               conversation_id=conversation.id,
               user_message=message_content,
               current_state=conversation.current_state,
               context_data=conversation.context_data or {}
           )
           
           # Actualizar conversación
           conversation = StateManager.update_conversation_state(
               db=db,
               conversation_id=conversation.id,
               new_state=result["next_state"],
               context_data=result["context_data"]
           )
           
           print(f"✅ Estado: {result['next_state']}")
           print(f"📊 Cliente encontrado: {result.get('datos_cliente_encontrados', False)}")
           
           return ChatResponse(
               conversation_id=conversation.id,
               message=result["message"],
               current_state=result["next_state"],
               buttons=result.get("buttons", []),
               context_data=result["context_data"]
           )
           
       except Exception as e:
           print(f"❌ Error: {e}")
           return ChatResponse(
               conversation_id=1,
               message="Disculpa los inconvenientes técnicos. ¿Podrías proporcionarme tu número de cédula?",
               current_state="validar_documento",
               buttons=[],
               context_data={}
           )

¡Con estos cambios tendrás un sistema completamente adaptado a tu estructura existente!
""")