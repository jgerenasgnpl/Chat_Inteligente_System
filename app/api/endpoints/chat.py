from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi import status
from sqlalchemy.orm import Session
from datetime import datetime
from app.api.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.flow_manager import ConfigurableFlowManagerAdaptado
from app.services.variable_service import VariableService
from app.machine_learning.ml import MLIntentionClassifier
from app.services.state_manager import StateManager
from app.services.log_service import LogService
from app.monitoring.monitoring_system import MLMetrics
from app.models.conversation import Conversation
from app.models.user import User
import logging

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger("uvicorn.error")

@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Procesador PRINCIPAL CORREGIDO - Prioriza búsqueda de cédula
    """
    user_id = request.user_id
    message_content = request.message or request.text or ""
    
    print(f"📩 Mensaje recibido: '{message_content}' de usuario {user_id}")
    
    try:
        # 1. OBTENER/CREAR CONVERSACIÓN
        conversation = _get_or_create_conversation(db, user_id, request.conversation_id)
        context_data = conversation.context_data or {}
        
        print(f"💬 Conversación {conversation.id} - Estado actual: {conversation.current_state}")
        print(f"📋 Contexto actual: {list(context_data.keys())}")
        
        # 2. INICIALIZAR FLOW MANAGER
        flow_manager = ConfigurableFlowManagerAdaptado(db)
        
        # 3. PROCESO PRINCIPAL - PRIORIZAR DETECCIÓN DE CÉDULA
        resultado = flow_manager.process_user_message(
            conversation_id=conversation.id,
            user_message=message_content,
            current_state=conversation.current_state,
            context_data=context_data
        )
        
        # 4. VERIFICAR SI ENCONTRÓ CLIENTE
        if resultado.get('datos_cliente_encontrados', False):
            print(f"🎉 Cliente encontrado y cargado en contexto!")
            print(f"👤 Cliente: {resultado['context_data'].get('Nombre_del_cliente')}")
            print(f"💰 Saldo: {resultado['context_data'].get('saldo_total')}")
        
        # 5. ACTUALIZAR ESTADO Y CONTEXTO
        conversation = StateManager.update_conversation_state(
            db=db,
            conversation_id=conversation.id,
            new_state=resultado['next_state'],
            context_data=resultado['context_data']
        )
        
        # 6. LOG INTERACCIÓN
        _log_interaction_simple(db, conversation, message_content, resultado, request.button_selected)
        
        print(f"✅ Respuesta generada - Estado: {resultado['next_state']}")
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=resultado['message'],
            current_state=resultado['next_state'],
            buttons=resultado.get('buttons', []),
            context_data=resultado['context_data']
        )
        
    except Exception as e:
        print(f"❌ Error procesando mensaje: {e}")
        import traceback
        traceback.print_exc()
        
        # Respuesta de emergencia
        return ChatResponse(
            conversation_id=conversation.id if 'conversation' in locals() else 1,
            message="Disculpa los inconvenientes técnicos. Para ayudarte mejor, ¿podrías proporcionarme tu número de cédula?",
            current_state="validar_documento",
            buttons=[],
            context_data={}
        )
def _log_interaction_simple(db, conversation, mensaje, resultado, button_selected):
    """Log simplificado de interacciones"""
    try:
        # Log mensaje usuario
        LogService.log_message(
            db=db,
            conversation_id=conversation.id,
            sender_type="user",
            text_content=mensaje,
            button_selected=button_selected,
            previous_state=conversation.current_state
        )
        
        # Log respuesta sistema
        LogService.log_message(
            db=db,
            conversation_id=conversation.id,
            sender_type="system",
            text_content=resultado['message'],
            previous_state=conversation.current_state,
            next_state=resultado['next_state']
        )
        
    except Exception as e:
        print(f"⚠️ Error en logging: {e}")

@router.post("/test-cedula")
async def test_cedula(
    cedula: str,
    db: Session = Depends(get_db)
):
    """Endpoint para probar búsqueda de cédulas"""
    try:
        flow_manager = ConfigurableFlowManagerAdaptado(db)
        
        # Detectar cédula
        cedula_detectada = flow_manager._detectar_cedula(cedula)
        print(f"Cédula detectada: {cedula_detectada}")
        
        if cedula_detectada:
            # Buscar en BD
            datos = flow_manager._consultar_cliente_por_cedula(cedula_detectada)
            return {
                "cedula_detectada": cedula_detectada,
                "cliente_encontrado": datos.get("cliente_encontrado", False),
                "datos": datos
            }
        else:
            return {
                "cedula_detectada": None,
                "error": "Cédula no detectada en el texto"
            }
            
    except Exception as e:
        return {"error": str(e)}

def _get_or_create_conversation(db: Session, user_id: int, conversation_id: Optional[int] = None) -> Conversation:
    """
    FUNCIÓN FALTANTE: Obtiene o crea conversación
    """
    # Verificar si el usuario existe
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=f"user{user_id}@example.com",
            hashed_password="temppassword", 
            full_name=f"Usuario {user_id}", 
            is_active=True
        )
        db.add(user)
        db.commit()
    
    # Si se especifica conversation_id, buscarla
    if conversation_id:
        conversation = (
            db.query(Conversation)
              .filter(
                  Conversation.id == conversation_id,
                  Conversation.user_id == user_id
              )
              .first()
        )
        if conversation:
            return conversation
    
    # Buscar conversación activa o crear nueva
    return StateManager.get_or_create_conversation(db, user_id)

def _procesar_mensaje_hibrido(
    flow_manager: ConfigurableFlowManagerAdaptado,
    ml_engine,  # MLConversationEngine
    conversation,
    mensaje: str,
    context_data: dict,
    db: Session
) -> dict:
    """
    NÚCLEO CORREGIDO: Combina ML inteligente con reglas de negocio
    """
    current_state = conversation.current_state
    
    print(f"🎯 Estado actual: {current_state}")
    print(f"📋 Contexto: {list(context_data.keys())}")
    
    # PASO 1: ANÁLISIS ML del mensaje
    ml_analysis = ml_engine.analizar_mensaje_completo(
        mensaje=mensaje,
        context_data=context_data,
        estado_actual=current_state
    )
    
    print(f"🤖 Análisis ML: {ml_analysis}")
    
    # PASO 2: DECISIÓN HÍBRIDA - ML + Reglas
    if ml_analysis['confianza'] > 0.8 and ml_analysis.get('accion_sugerida'):
        # Alta confianza ML - usar sugerencia inteligente
        print("🎯 Usando decisión ML (alta confianza)")
        next_state = ml_analysis['estado_sugerido']
        respuesta = ml_analysis['respuesta_personalizada']
        
        # Ejecutar acción ML si existe
        if ml_analysis.get('accion_sugerida'):
            context_data = flow_manager.ejecutar_accion_configurable(
                ml_analysis['accion_sugerida'],
                context_data,
                mensaje,
                conversation.user_id
            )
    else:
        # Baja confianza ML - usar reglas de negocio tradicionales
        print("📋 Usando reglas de negocio (baja confianza ML)")
        
        # Obtener configuración del estado desde BD o YAML (fallback)
        estado_config = flow_manager.obtener_estado(current_state)
        
        if not estado_config:
            # FALLBACK a YAML si no existe en BD
            estado_config = _obtener_estado_yaml_fallback(current_state)
        
        # Ejecutar acción si está definida
        if estado_config.get('accion'):
            context_data = flow_manager.ejecutar_accion_configurable(
                estado_config['accion'],
                context_data,
                mensaje,
                conversation.user_id
            )
        
        # Evaluar condición
        next_state = estado_config.get('estado_siguiente_default', current_state)
        if estado_config.get('condicion'):
            condicion_resultado = flow_manager.evaluar_condicion_inteligente(
                estado_config['condicion'],
                mensaje,
                context_data
            )
            
            if condicion_resultado and estado_config.get('estado_siguiente_true'):
                next_state = estado_config['estado_siguiente_true']
            elif not condicion_resultado and estado_config.get('estado_siguiente_false'):
                next_state = estado_config['estado_siguiente_false']
        
        # Generar respuesta usando template - CORREGIDO
        mensaje_template = estado_config.get('mensaje_template', 'Procesando tu solicitud...')
        respuesta = flow_manager.reemplazar_variables_inteligente(mensaje_template, context_data)
    
    # PASO 3: OBTENER BOTONES/OPCIONES
    botones = flow_manager.obtener_opciones_estado(current_state)
    
    # PASO 4: ENRIQUECER CON ML si es necesario
    if ml_analysis.get('personalizacion_adicional'):
        respuesta = ml_engine.personalizar_respuesta(respuesta, context_data, ml_analysis)
    
    return {
        'respuesta': respuesta,
        'next_state': next_state,
        'botones': botones,
        'context_data': context_data,
        'ml_analysis': ml_analysis
    }

def _obtener_estado_yaml_fallback(estado: str) -> dict:
    """
    FALLBACK: Si no existe en BD, usar YAML
    (Durante transición gradual)
    """
    try:
        import yaml
        with open("base_conocimiento.yaml", "r", encoding="utf-8") as f:
            kb = yaml.safe_load(f)
        return kb.get(estado, {})
    except:
        return {"message": "Estoy procesando tu solicitud...", "next": estado}

def _log_interaction(db, conversation, mensaje, resultado, button_selected):
    """Registra la interacción completa"""
    
    # Log mensaje usuario
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="user",
        text_content=mensaje,
        button_selected=button_selected,
        previous_state=conversation.current_state
    )
    
    # Log respuesta sistema
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="system",
        text_content=resultado['respuesta'],
        previous_state=conversation.current_state,
        next_state=resultado['next_state']
    )
    
    # Log predicción ML
    if 'ml_analysis' in resultado:
        ml_metrics = MLMetrics(db)
        ml_analysis = resultado['ml_analysis']
        ml_metrics.registrar_prediccion_ml(
            mensaje=mensaje,
            intencion_predicha=ml_analysis.get('intencion', 'desconocida'),
            confianza=ml_analysis.get('confianza', 0.0),
            conversation_id=conversation.id
        )

# ===========================================
# ML CONVERSATION ENGINE - CORREGIDO
# ===========================================

class MLConversationEngine:
    """
    Motor ML para conversaciones inteligentes
    Combina clasificación de intenciones + personalización
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ml_classifier = self._cargar_clasificador()
    
    def _cargar_clasificador(self):
        """Carga el clasificador ML"""
        try:
            # Usar el clasificador existente de machine_learning/ml.py
            from app.machine_learning.ml import MLIntentionClassifier
            return MLIntentionClassifier(self.db)
        except ImportError:
            print("⚠️ MLIntentionClassifier no disponible, usando clasificador simple")
            return None
    
    def analizar_mensaje_completo(self, mensaje: str, context_data: dict, estado_actual: str) -> dict:
        """
        Análisis completo ML del mensaje del usuario
        """
        # 1. Detectar intención básica
        if self.ml_classifier:
            intencion_base = self.ml_classifier.predecir_intencion(mensaje)
        else:
            # Fallback simple si no hay ML
            intencion_base = {"intencion": "DESCONOCIDA", "confianza": 0.0}
        
        # 2. Analizar contexto del cliente
        perfil_cliente = self._analizar_perfil_cliente(context_data)
        
        # 3. Evaluar momento óptimo (timing)
        momento_optimo = self._evaluar_momento_interaccion(context_data, estado_actual)
        
        # 4. Determinar estrategia conversacional
        estrategia = self._determinar_estrategia(intencion_base, perfil_cliente, momento_optimo)
        
        # 5. Generar respuesta personalizada
        respuesta_personalizada = self._generar_respuesta_ml(
            estrategia, context_data, mensaje
        )
        
        return {
            "intencion": intencion_base["intencion"],
            "confianza": intencion_base["confianza"],
            "perfil_cliente": perfil_cliente,
            "estrategia": estrategia,
            "estado_sugerido": estrategia.get("proximo_estado"),
            "accion_sugerida": estrategia.get("accion_recomendada"),
            "respuesta_personalizada": respuesta_personalizada,
            "personalizacion_adicional": estrategia.get("personalizar", False)
        }
    
    def _analizar_perfil_cliente(self, context_data: dict) -> dict:
        """Perfila al cliente usando ML"""
        # Factores para ML
        factores = {
            "antiguedad_deuda": context_data.get("antiguedad_deuda", 0),
            "monto_deuda": self._extraer_valor_numerico(context_data.get("saldo_total", "0")),
            "campana": context_data.get("campana", ""),
            "interacciones_previas": context_data.get("interacciones_count", 0),
            "ultima_respuesta_positiva": context_data.get("ultima_intencion") in ["INTENCION_PAGO", "CONFIRMACION"]
        }
        
        # Modelo simple de propensión (se puede mejorar con ML real)
        propension_pago = self._calcular_propension_simple(factores)
        
        return {
            "propension_pago": propension_pago,
            "segmento": self._determinar_segmento(propension_pago, factores),
            "factores_riesgo": self._identificar_factores_riesgo(factores)
        }
    
    def _evaluar_momento_interaccion(self, context_data: dict, estado_actual: str) -> dict:
        """Evalúa el momento óptimo de la interacción"""
        return {
            "estado_actual": estado_actual,
            "momento": "optimo" if context_data.get("nombre_cliente") else "temprano"
        }
    
    def _determinar_segmento(self, propension: float, factores: dict) -> str:
        """Determina el segmento del cliente"""
        if propension > 0.7:
            return "ALTO_POTENCIAL"
        elif propension > 0.4:
            return "MEDIO_POTENCIAL"
        else:
            return "BAJO_POTENCIAL"
    
    def _identificar_factores_riesgo(self, factores: dict) -> list:
        """Identifica factores de riesgo"""
        riesgos = []
        if factores["monto_deuda"] > 1000000:
            riesgos.append("monto_alto")
        if "castig" in factores["campana"].lower():
            riesgos.append("cartera_castigada")
        return riesgos
    
    def _determinar_estrategia(self, intencion: dict, perfil: dict, momento: dict) -> dict:
        """Determina la mejor estrategia conversacional"""
        
        # Reglas ML-based para estrategia
        if perfil["propension_pago"] > 0.7:
            if intencion["intencion"] in ["CONSULTA_DEUDA", "INTENCION_PAGO"]:
                return {
                    "tipo": "AGRESIVA_POSITIVA",
                    "proximo_estado": "proponer_planes_pago",
                    "accion_recomendada": "mostrar_ofertas_atractivas",
                    "tono": "entusiasta",
                    "personalizar": True
                }
        
        elif perfil["propension_pago"] < 0.3:
            return {
                "tipo": "CONSERVACION",
                "proximo_estado": "mensaje_empatico",
                "accion_recomendada": "construir_relacion",
                "tono": "comprensivo",
                "personalizar": True
            }
        
        # Estrategia balanceada por defecto
        return {
            "tipo": "BALANCEADA",
            "proximo_estado": "evaluar_intencion_pago",
            "accion_recomendada": None,
            "tono": "profesional",
            "personalizar": False
        }
    
    def _generar_respuesta_ml(self, estrategia: dict, context_data: dict, mensaje_usuario: str) -> str:
        """Genera respuesta personalizada usando ML"""
        
        if estrategia["tipo"] == "AGRESIVA_POSITIVA":
            return f"""¡Perfecto {context_data.get('nombre_cliente', 'estimado cliente')}! 
            
Veo que estás interesado en resolver tu situación. Tengo excelentes noticias:
✨ **OFERTA ESPECIAL SOLO PARA TI**
💰 De {context_data.get('saldo_total', '$500.000')} ➜ {context_data.get('oferta_2', '$150.000')}
🎯 ¡Ahorra más del 60% pagando HOY!

¿Procedemos con esta oportunidad única?"""
        
        elif estrategia["tipo"] == "CONSERVACION":
            return f"""Entiendo tu situación, {context_data.get('nombre_cliente', '')}. 

Sabemos que pueden presentarse dificultades, y estamos aquí para ayudarte a encontrar una solución que funcione para ti.

Tu tranquilidad es importante para nosotros. ¿Te gustaría que conversemos sobre alternativas flexibles?"""
        
        # Respuesta balanceada
        return f"""Gracias por contactarnos, {context_data.get('nombre_cliente', '')}.

Tu situación actual es:
💰 Saldo: {context_data.get('saldo_total', '$0')}
🏛️ Entidad: {context_data.get('banco', 'N/A')}

¿Te gustaría conocer las opciones disponibles para normalizar tu situación?"""
    
    def personalizar_respuesta(self, respuesta: str, context_data: dict, ml_analysis: dict) -> str:
        """Personaliza la respuesta basada en análisis ML"""
        # Implementar personalización adicional aquí
        return respuesta
    
    def _calcular_propension_simple(self, factores: dict) -> float:
        """Modelo simple de propensión al pago"""
        score = 0.5  # Base neutral
        
        # Factor deuda (menor deuda = mayor propensión)
        if factores["monto_deuda"] < 200000:
            score += 0.2
        elif factores["monto_deuda"] > 1000000:
            score -= 0.2
        
        # Factor interacciones (más interacciones = más interés)
        if factores["interacciones_previas"] > 3:
            score += 0.15
        
        # Factor respuesta positiva previa
        if factores["ultima_respuesta_positiva"]:
            score += 0.25
        
        # Factor campaña
        if "castig" in factores["campana"].lower():
            score -= 0.1  # Más difícil
        
        return max(0.0, min(1.0, score))  # Clamp entre 0 y 1
    
    def _extraer_valor_numerico(self, valor_texto: str) -> float:
        """Extrae valor numérico de texto con formato de moneda"""
        import re
        if not valor_texto:
            return 0.0
        
        # Remover símbolos y convertir
        numero = re.sub(r'[^\d.]', '', str(valor_texto))
        try:
            return float(numero)
        except:
            return 0.0

# ===========================================
# ENDPOINTS ADICIONALES MANTENIDOS
# ===========================================

@router.post("/reset-conversation")
def reset_conversation(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Reinicia la conversación del usuario"""
    # Marcar todas las conversaciones activas como inactivas
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.is_active == True)
        .all()
    )
    
    for conv in conversations:
        conv.is_active = False
        conv.ended_at = datetime.now()
    
    db.commit()
    
    new_conv = StateManager.get_or_create_conversation(db, user_id)
    
    return {
        "message": "Conversación reiniciada",
        "new_conversation_id": new_conv.id,
        "current_state": new_conv.current_state
    }

@router.get("/history")
def get_conversation_history(
    user_id: int,
    conversation_id: Optional[int] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """Historial de mensajes"""
    if not conversation_id:
        conv = StateManager.get_or_create_conversation(db, user_id)
        conversation_id = conv.id
    
    return LogService.get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        skip=skip
    )

@router.get("/test")
def test():
    return {"message": "API funcionando correctamente"}