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
from app.services.conversation_service import crear_conversation_service
from app.services.log_service import LogService
from app.monitoring.monitoring_system import MLMetrics
from app.models.conversation import Conversation
from app.models.user import User
import json
import logging

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger("uvicorn.error")

def safe_get_context_data(conversation):
    """Obtiene context_data como diccionario de forma segura"""
    try:
        if hasattr(conversation, 'context_data'):
            raw_context = conversation.context_data
            if isinstance(raw_context, dict):
                return raw_context
            elif isinstance(raw_context, str):
                return json.loads(raw_context) if raw_context else {}
            else:
                return {}
        else:
            return {}
    except Exception as e:
        print(f"⚠️ Error procesando contexto: {e}")
        return {}

@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Procesador PRINCIPAL CORREGIDO con Variables Integradas
    """
    user_id = request.user_id
    message_content = request.message or request.text or ""
    
    print(f"📩 Mensaje recibido: '{message_content}' de usuario {user_id}")
    
    try:
        # 1. OBTENER/CREAR CONVERSACIÓN
        conversation = _get_or_create_conversation(db, user_id, request.conversation_id)
        
        # ✅ CORRECCIÓN: Manejo seguro del contexto
        context_data = safe_get_context_data(conversation)
        
        print(f"💬 Conversación {conversation.id} - Estado actual: {conversation.current_state}")
        print(f"📋 Contexto actual: {list(context_data.keys()) if context_data else 'vacío'}")
        
        # 2. INICIALIZAR FLOW MANAGER
        flow_manager = ConfigurableFlowManagerAdaptado(db)
        
        # 3. PROCESO PRINCIPAL - PRIORIZAR DETECCIÓN DE CÉDULA
        resultado = flow_manager.process_user_message(
            conversation_id=conversation.id,
            user_message=message_content,
            current_state=conversation.current_state,
            context_data=context_data
        )
        
        # 4. ✅ RESOLUCIÓN DE VARIABLES - CORREGIDO
        try:
            conversation_service = crear_conversation_service(db)
            
            # Crear contexto para variables
            contexto_variables = {}
            if context_data.get("cedula_detectada"):
                contexto_variables["cedula_detectada"] = str(context_data["cedula_detectada"])
            if context_data.get("Nombre_del_cliente"):
                contexto_variables["nombre_cliente"] = context_data.get("Nombre_del_cliente", "Cliente")
                contexto_variables["banco"] = context_data.get("banco", "Entidad Financiera")
                contexto_variables["saldo_total"] = context_data.get("saldo_total", "$0")
                # Agregar cálculos de ofertas
                try:
                    saldo_num = float(str(context_data.get("saldo_total", "0")).replace("$", "").replace(",", ""))
                    contexto_variables["oferta_1"] = f"${saldo_num * 0.3:,.0f}"
                    contexto_variables["hasta_3_cuotas"] = f"${saldo_num * 0.4 / 3:,.0f}"
                    contexto_variables["hasta_6_cuotas"] = f"${saldo_num * 0.5 / 6:,.0f}"
                    contexto_variables["hasta_12_cuotas"] = f"${saldo_num * 0.6 / 12:,.0f}"
                except:
                    contexto_variables["oferta_1"] = "$0"
                    contexto_variables["hasta_3_cuotas"] = "$0"
                    contexto_variables["hasta_6_cuotas"] = "$0"
                    contexto_variables["hasta_12_cuotas"] = "$0"
            
            # ✅ RESOLVER VARIABLES EN LA RESPUESTA
            mensaje_final = conversation_service.variable_service.resolver_variables(
                resultado['message'], 
                contexto_variables
            )
            
            print(f"🔧 Variables aplicadas: {list(contexto_variables.keys())}")
            
        except Exception as var_error:
            print(f"⚠️ Error en variables (usando mensaje original): {var_error}")
            mensaje_final = resultado['message']
        
        # 5. VERIFICAR SI ENCONTRÓ CLIENTE
        if resultado.get('datos_cliente_encontrados', False):
            print(f"🎉 Cliente encontrado y cargado en contexto!")
            print(f"👤 Cliente: {resultado['context_data'].get('Nombre_del_cliente')}")
            print(f"💰 Saldo: {resultado['context_data'].get('saldo_total')}")
        
        # 6. ACTUALIZAR ESTADO Y CONTEXTO
        conversation = StateManager.update_conversation_state(
            db=db,
            conversation_id=conversation.id,
            new_state=resultado['next_state'],
            context_data=resultado.get('context_data', {})
        )
        
        # 7. LOG INTERACCIÓN
        _log_interaction_simple(db, conversation, message_content, resultado, request.button_selected)
        
        print(f"✅ Respuesta con variables generada - Estado: {resultado['next_state']}")
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=mensaje_final,  # ✅ CON VARIABLES RESUELTAS
            current_state=resultado['next_state'],
            buttons=resultado.get('buttons', []),
            context_data=resultado.get('context_data', {})
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
    FUNCIÓN CORREGIDA: Obtiene o crea conversación con manejo seguro de contexto
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

# ===== MANTENER TODOS LOS OTROS ENDPOINTS =====
@router.post("/message-v2", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_message_v2(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Procesador V2 con sistema de variables integrado
    """
    user_id = request.user_id
    message_content = request.message or request.text or ""
    
    logger.info(f"📩 Mensaje V2 recibido: '{message_content}' de usuario {user_id}")
    
    try:
        # ✅ USAR NUEVO CONVERSATION SERVICE
        conversation_service = crear_conversation_service(db)
        
        # ✅ PROCESAR CON INTENCIÓN SI VIENE DE BOTÓN
        if hasattr(request, 'intention') and request.intention:
            logger.info(f"🎯 Intención específica del botón: {request.intention}")
            result = await conversation_service.process_message_with_intention(
                request.conversation_id or 1,
                message_content,
                user_id,
                request.intention
            )
        else:
            # Procesamiento normal con variables
            result = await conversation_service.process_message(
                request.conversation_id or 1,
                message_content,
                user_id
            )
        
        # ✅ LOG COMPATIBLE CON TU SISTEMA ACTUAL
        _log_interaction_simple(
            db, 
            conversation_service.get_or_create_conversation(result["conversation_id"], user_id),
            message_content, 
            {"message": result["response"], "next_state": result["state"]}, 
            getattr(request, 'button_selected', None)
        )
        
        return ChatResponse(
            conversation_id=result["conversation_id"],
            message=result["response"],
            current_state=result["state"],
            buttons=result.get("buttons", []),
            context_data=result.get("context", {})
        )
        
    except Exception as e:
        logger.error(f"❌ Error en V2: {e}")
        import traceback
        traceback.print_exc()
        
        return ChatResponse(
            conversation_id=request.conversation_id or 1,
            message="Lo siento, ha ocurrido un error. ¿Podrías proporcionarme tu número de cédula?",
            current_state="validar_documento",
            buttons=[],
            context_data={}
        )

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

@router.get("/historial/{conversation_id}")
async def get_historial(
    conversation_id: int,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db)):
    try:
        messages = LogService.get_conversation_history(
            db=db, 
            conversation_id=conversation_id,
            limit=limit,
            skip=skip
        )
        
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": msg.id,
                    "sender_type": msg.sender_type,
                    "text_content": msg.text_content,
                    "timestamp": msg.timestamp,
                    "button_selected": msg.button_selected
                }
                for msg in messages
            ],
            "total": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
def test():
    return {"message": "API funcionando correctamente"}
