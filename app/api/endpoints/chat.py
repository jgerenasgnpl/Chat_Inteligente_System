from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

# Dependencias
from app.api.deps import get_db

# Modelos SQLAlchemy
from app.models.conversation import Conversation
from app.models.message import Message as MessageModel
from app.models.user import User

# Schemas Pydantic
from app.schemas.chat import ChatRequest, ChatResponse, ConversationListResponse
from app.schemas.message import Message as MessageSchema

# Servicios
from app.services.state_manager import StateManager
from app.services.log_service import LogService

import yaml
from pathlib import Path

router = APIRouter(
    prefix="",
    tags=["chat"]
)

# Cargar la base de conocimiento
kb_path = Path("base_conocimiento.yaml")
try:
    with open(kb_path, "r", encoding="utf-8") as f:
        kb = yaml.safe_load(f)
    print(f"Base de conocimiento cargada correctamente con {len(kb)} estados")
    print(f"Estados disponibles: {list(kb.keys())}")
except Exception as e:
    print(f"Error al cargar la base de conocimiento: {e}")
    kb = {}

def evaluar_condicion(condition_name, user_message, context_data, user_id, db):
    """
    Evalúa condiciones basadas en el mensaje del usuario y el contexto
    """
    # Convertir mensaje a minúsculas para facilitar comparaciones
    mensaje_lower = user_message.lower() if user_message else ""
    print(f"Evaluando condición: {condition_name}")
    print(f"Mensaje usuario: {mensaje_lower}")
    print(f"Contexto: {context_data}")

    # Implementación de condiciones específicas
    if condition_name == "consulta_exitosa":
        # Simulamos que la consulta es exitosa para avanzar en el flujo
        print("Evaluando consulta_exitosa = True para validar_documento")
        return True
    
    elif condition_name == "cliente_muestra_frustracion":
        # Buscar palabras que indiquen frustración
        palabras_frustracion = ["molesto", "enojado", "injusto", "absurdo", "ridiculo", "no entiendo"]
        return any(palabra in mensaje_lower for palabra in palabras_frustracion)
    
    elif condition_name == "cliente_con_deuda_antigua":
        # Consultar la base de datos para determinar si la deuda es antigua
        # Ejemplo simplificado:
        return context_data and context_data.get("antiguedad_deuda", 0) > 90
    
    elif condition_name == "cliente_alto_riesgo":
        # Consultar la base de datos para determinar el riesgo del cliente
        # Ejemplo simplificado:
        return context_data and context_data.get("nivel_riesgo", "bajo") == "alto"
    
    elif condition_name == "cliente_selecciona_plan":
        # Verificar si el usuario seleccionó un plan del 1 al 3
        return mensaje_lower in ["1", "2", "3", "opcion 1", "opcion 2", "opcion 3"]
    
    elif condition_name == "cliente_indica_motivo":
        # Verificar si el usuario indica algún motivo para no pagar
        motivos = ["no tengo", "no puedo", "sin dinero", "ya pagué", "no reconozco", "no es mío"]
        return any(motivo in mensaje_lower for motivo in motivos)
    
    elif condition_name == "objecion_ya_pague":
        # Verificar si el usuario indica que ya pagó
        return any(frase in mensaje_lower for frase in ["ya pagué", "ya pague", "hice el pago", "transferí", "deposité"])
    
    elif condition_name == "objecion_sin_dinero":
        # Verificar si el usuario indica que no tiene dinero
        return any(frase in mensaje_lower for frase in ["no tengo dinero", "sin fondos", "no puedo pagar", "estoy desempleado"])
    
    elif condition_name == "objecion_no_reconoce":
        # Verificar si el usuario no reconoce la deuda
        return any(frase in mensaje_lower for frase in ["no reconozco", "no es mía", "no es mio", "nunca compré", "error"])
    
    # Valor por defecto para condiciones no implementadas
    return True

def reemplazar_variables_en_mensaje(mensaje, context_data):
    """
    Reemplaza variables del tipo {{variable}} en el mensaje con valores reales
    """
    if not mensaje:
        return mensaje
    
    # Crear un diccionario con todas las variables disponibles
    variables = {}
    
    # Añadir variables de contexto
    if context_data:
        variables.update(context_data)
    
    # Añadir variables específicas
    if "opcion" in variables:
        if variables["opcion"] == "1":
            variables["opcion"] = "Pago único con descuento"
        elif variables["opcion"] == "2":
            variables["opcion"] = "Plan en 2 cuotas sin interés"
        elif variables["opcion"] == "3":
            variables["opcion"] = "Plan en 6 cuotas"
    
    # Añadir fecha actual si no existe
    if "fecha" not in variables:
        variables["fecha"] = datetime.now().strftime("%d/%m/%Y")
    
    # Añadir otras variables frecuentes
    variables["nombre_empresa"] = "NegotiationCorp"
    variables["monto_deuda"] = "$500.000"  # Valor por defecto
    
    # Reemplazar todas las variables que coincidan
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        mensaje = mensaje.replace(placeholder, str(value))
    
    return mensaje

@router.post("/message", response_model=ChatResponse)
def process_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Procesa un mensaje de chat y devuelve la respuesta.
    """
    user_id = request.user_id
    
    # Verificar si el usuario existe y crearlo si no
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Crear usuario nuevo
        user = User(
            id=user_id,
            email=f"user{user_id}@example.com",  # Email temporal
            hashed_password="temppassword",      # Contraseña temporal
            full_name=f"Usuario {user_id}",      # Nombre temporal
            is_active=True
        )
        db.add(user)
        db.commit()
    
    # Aceptar tanto message como text (del frontend)
    message_content = request.message
    if hasattr(request, 'text') and request.text and not message_content:
        message_content = request.text
    
    print(f"Mensaje recibido: {message_content}")
    
    # Validar o crear conversación
    if request.conversation_id:
        conversation = (
            db.query(Conversation)
              .filter(
                  Conversation.id == request.conversation_id,
                  Conversation.user_id == user_id
              )
              .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    else:
        conversation = StateManager.get_or_create_conversation(db, user_id)
    
    consulta_deuda_keywords = ["cuanto debo", "cuánto debo", "deuda", "debo", "saldo", "consultar"]
    if any(keyword in message_content.lower() for keyword in consulta_deuda_keywords):
        # Si el usuario ya tiene documento en contexto, ir a mostrar deuda
        if context_data.get("documento_cliente"):
            next_state = "mostrar_deuda"
            # Actualizar estado inmediatamente
            conversation = StateManager.update_conversation_state(
                db=db,
                conversation_id=conversation.id,
                new_state=next_state,
                context_data=context_data
            )
            current_state = next_state
            kb_state = kb.get(current_state, {})
        else:
            # Si no tiene documento, ir a solicitar documento
            next_state = "solicitar_documento"
            # Actualizar estado inmediatamente
            conversation = StateManager.update_conversation_state(
                db=db,
                conversation_id=conversation.id,
                new_state=next_state,
                context_data=context_data
            )
            current_state = next_state
            kb_state = kb.get(current_state, {})

    # Obtener y actualizar contexto
    context_data = conversation.context_data or {}
    
    # Si se seleccionó un botón, guardarlo en el contexto
    if request.button_selected:
        print(f"Botón seleccionado: {request.button_selected}")
        context_data["opcion"] = request.button_selected
        conversation = StateManager.update_conversation_state(
            db=db,
            conversation_id=conversation.id,
            new_state=conversation.current_state,
            context_data=context_data
        )
    
    # Log mensaje usuario
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="user",
        text_content=message_content,
        button_selected=request.button_selected,
        previous_state=conversation.current_state
    )
    
    # Lógica para procesar el mensaje utilizando base_conocimiento.yaml
    current_state = conversation.current_state
    print(f"Estado actual: {current_state}")
    
    kb_state = kb.get(current_state, {})
    print(f"Datos del estado: {kb_state}")
    
    # Ejecutar acción si está definida
    if "action" in kb_state:
        action_name = kb_state["action"]
        print(f"Ejecutando acción: {action_name}")
        action_result = ejecutar_accion(
            action_name, 
            context_data, 
            message_content,  
            user_id, 
            db
        )
        # Si la acción devuelve datos de contexto, actualizarlos
        if isinstance(action_result, dict):
            context_data.update(action_result)
    
    # Procesar estado actual y determinar respuesta
    system_response = kb_state.get("message", "Estoy procesando tu solicitud.")
    print(f"Respuesta sin procesar: {system_response}")
    
    # Determinar siguiente estado
    next_state = kb_state.get("next", current_state)
    
    # Si hay condición, evaluarla usando la función implementada
    if "condition" in kb_state:
        condition_name = kb_state["condition"]
        condition_result = evaluar_condicion(
            condition_name, 
            message_content, 
            context_data, 
            user_id, 
            db
        )
        print(f"Condición '{condition_name}' resultado: {condition_result}")
        
        if condition_result and "true_next" in kb_state:
            next_state = kb_state["true_next"]
            print(f"Siguiente estado (true): {next_state}")
        elif not condition_result and "false_next" in kb_state:
            next_state = kb_state["false_next"]
            print(f"Siguiente estado (false): {next_state}")
    
    # Preparar botones si están definidos en el estado
    buttons = []
    # Manejar el caso especial de proponer_planes_pago
    if current_state == "proponer_planes_pago":
        buttons = [
            {"id": "1", "text": "Pago único con descuento"},
            {"id": "2", "text": "Plan en 2 cuotas sin interés"},
            {"id": "3", "text": "Plan en 6 cuotas"}
        ]
    elif kb_state.get("options"):
        for opt in kb_state["options"]:
            buttons.append({"id": opt["id"], "text": opt["text"]})
    
    # Reemplazar variables en el mensaje
    system_response = reemplazar_variables_en_mensaje(system_response, context_data)
    print(f"Respuesta final: {system_response}")
    
    # Actualizar estado
    conversation = StateManager.update_conversation_state(
        db=db,
        conversation_id=conversation.id,
        new_state=next_state,
        context_data=context_data
    )
    
    # Log respuesta sistema
    LogService.log_message(
        db=db,
        conversation_id=conversation.id,
        sender_type="system",
        text_content=system_response,
        previous_state=current_state,
        next_state=next_state
    )
    
    return ChatResponse(
        conversation_id=conversation.id,
        message=system_response,
        current_state=next_state,
        buttons=buttons,
        context_data=context_data
    )

def extraer_documento(mensaje):
    """
    Extrae un posible número de documento del mensaje del usuario
    """
    if not mensaje:
        return None
    
    import re
    patrones = [
        r'\b\d{6,12}\b',            
        r'cédula\s+(\d{6,12})',  
        r'cedula\s+(\d{6,12})',     
        r'cc\s+(\d{6,12})',    
        r'documento\s+(\d{6,12})'  
    ]
    
    mensaje = mensaje.lower() if mensaje else ""
    for patron in patrones:
        match = re.search(patron, mensaje)
        if match:
            if len(match.groups()) > 0:
                return match.group(1)
            return match.group(0)
    
    return None

def ejecutar_accion(action_name, context_data, user_message, user_id, db):
    """
    Ejecuta acciones definidas en la base de conocimiento
    """
    print(f"Ejecutando acción: {action_name}")
    
    if action_name == "consultar_base_datos":
        # Obtener documento de identidad del cliente
        documento_cliente = extraer_documento(user_message)
        if documento_cliente:
            print(f"Documento detectado en mensaje: {documento_cliente}")
            context_data["documento_cliente"] = documento_cliente
            return context_data
        
        context_data["documento_cliente"] = documento_cliente
        
        try:
            # Consulta directa a la tabla ConsolidadoCampañasNatalia
            from sqlalchemy import text
            
            query = text("""
                SELECT 
                    Nombre_del_cliente,
                    Cedula,
                    Telefono,
                    Email,
                    Campaña,
                    Producto,
                    banco,
                    Saldo_total,
                    Capital,
                    Intereses,
                    Oferta_1,
                    Oferta_2,
                    Oferta_3,
                    Oferta_4,
                    Hasta_2_cuotas,
                    Hasta_3_cuotas,
                    Hasta_6_cuotas,
                    Hasta_12_cuotas,
                    Hasta_18_cuotas,
                    Pago_flexible,
                    NumerodeObligacion
                FROM 
                    [turnosvirtuales_dev].[dbo].[ConsolidadoCampañasNatalia]
                WHERE 
                    Cedula = :cedula
            """)
            
            result = db.execute(query, {"cedula": documento_cliente}).fetchone()
            
            if not result:
                print(f"No se encontró cliente con cédula {documento_cliente}")
                context_data["cliente_no_encontrado"] = True
                return context_data
            
            # Asignar resultados a variables en el contexto
            context_data["nombre_cliente"] = result[0] or ""
            context_data["cedula"] = result[1] or ""
            context_data["telefono"] = result[2] or ""
            context_data["email"] = result[3] or ""
            context_data["campana"] = result[4] or ""
            context_data["producto"] = result[5] or ""
            context_data["banco"] = result[6] or ""
            
            # Formatear valores monetarios
            context_data["saldo_total"] = f"${result[7]:,.0f}".replace(",", ".") if result[7] else "$0"
            context_data["capital"] = f"${result[8]:,.0f}".replace(",", ".") if result[8] else "$0"
            context_data["intereses"] = f"${result[9]:,.0f}".replace(",", ".") if result[9] else "$0"
            
            # Ofertas con descuento
            context_data["oferta_1"] = f"${result[10]:,.0f}".replace(",", ".") if result[10] else "$0"
            context_data["oferta_2"] = f"${result[11]:,.0f}".replace(",", ".") if result[11] else "$0"
            context_data["oferta_3"] = f"${result[12]:,.0f}".replace(",", ".") if result[12] else "$0"
            context_data["oferta_4"] = f"${result[13]:,.0f}".replace(",", ".") if result[13] else "$0"
            
            # Valores de cuotas
            context_data["cuota_dos"] = f"${result[14]:,.0f}".replace(",", ".") if result[14] else "$0"
            context_data["cuota_tres"] = f"${result[15]:,.0f}".replace(",", ".") if result[15] else "$0"
            context_data["cuota_seis"] = f"${result[16]:,.0f}".replace(",", ".") if result[16] else "$0"
            context_data["cuota_doce"] = f"${result[17]:,.0f}".replace(",", ".") if result[17] else "$0"
            context_data["cuota_dieciocho"] = f"${result[18]:,.0f}".replace(",", ".") if result[18] else "$0"
            
            # Pago flexible
            context_data["pago_flexible"] = f"${result[19]:,.0f}".replace(",", ".") if result[19] else "$0"
            
            # Número de obligación
            context_data["numero_obligacion"] = result[20] or ""
            
            # Datos adicionales para el flujo
            context_data["nivel_riesgo"] = "alto" if context_data.get("campana", "").lower().find("castig") >= 0 else "bajo"
            context_data["antiguedad_deuda"] = 120  # Valor predeterminado, podrías añadir esta columna a la tabla
            context_data["nombre_empresa"] = context_data.get("banco", "NegotiationCorp")
            
            print(f"Información cliente recuperada: {context_data['nombre_cliente']}, saldo: {context_data['saldo_total']}")
            return context_data
            
        except Exception as e:
            print(f"Error al consultar información del cliente: {e}")
            context_data["error_consulta"] = True
            return context_data
    
    elif action_name == "analizar_historial_cliente":
        # Usar los datos ya cargados del cliente para análisis
        nivel_riesgo = context_data.get("nivel_riesgo", "bajo")
        print(f"Analizando historial cliente, nivel_riesgo={nivel_riesgo}")
        return context_data
    
    elif action_name == "crear_planes_pago":
        # Usar los valores de cuotas ya cargados de la base de datos
        print("Creando planes de pago con datos de la tabla")
        return context_data
    
    elif action_name == "registrar_plan_pago":
        # Registrar el plan elegido y generar fechas de pago
        from datetime import datetime, timedelta
        
        hoy = datetime.now()
        primer_pago = hoy + timedelta(days=7)  # Primera cuota a 7 días
        context_data["fecha_primer_pago"] = primer_pago.strftime("%d/%m/%Y")
        
        # Si se eligió un plan de cuotas, calcular segunda fecha
        if context_data.get("opcion") in ["2", "3"]:
            segunda_fecha = hoy + timedelta(days=30)  # Segunda cuota a 30 días
            context_data["fecha_segundo_pago"] = segunda_fecha.strftime("%d/%m/%Y")
            
        print(f"Plan registrado: opción {context_data.get('opcion', 'No especificada')}, primer pago: {context_data['fecha_primer_pago']}")
        return context_data
    
    return context_data

@router.post("/reset-conversation")
def reset_conversation(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Reinicia la conversación del usuario
    """
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
    
    # Crear nueva conversación
    new_conv = StateManager.get_or_create_conversation(db, user_id)
    
    return {
        "message": "Conversación reiniciada",
        "new_conversation_id": new_conv.id,
        "current_state": new_conv.current_state
    }

@router.get("/history", response_model=List[MessageSchema])
def get_conversation_history(
    user_id: int,
    conversation_id: Optional[int] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """
    Historial de mensajes.
    """
    # Verificar si el usuario existe y crearlo si no
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Crear usuario nuevo
        user = User(
            id=user_id,
            email=f"user{user_id}@example.com",  # Email temporal
            hashed_password="temppassword",      # Contraseña temporal
            full_name=f"Usuario {user_id}",      # Nombre temporal
            is_active=True
        )
        db.add(user)
        db.commit()
    
    if not conversation_id:
        conv = StateManager.get_or_create_conversation(db, user_id)
        conversation_id = conv.id
    else:
        conv = (
            db.query(Conversation)
              .filter(
                  Conversation.id == conversation_id,
                  Conversation.user_id == user_id
              )
              .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no existe")

    return LogService.get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        skip=skip
    )

@router.get("/historial/{user_id}", response_model=List[MessageSchema])
def get_user_history(
    user_id: int,
    conversation_id: Optional[int] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """
    Endpoint alternativo para mantener compatibilidad con el frontend
    """
    return get_conversation_history(
        user_id=user_id, 
        conversation_id=conversation_id,
        limit=limit, 
        skip=skip, 
        db=db
    )

@router.get("/test")
def test():
    return {"message": "API funcionando correctamente"}

@router.get("/debug-kb")
def debug_kb():
    """
    Endpoint para depurar la base de conocimiento
    """
    return {
        "kb_loaded": kb is not None,
        "kb_states": list(kb.keys()) if kb else [],
        "initial_state_data": kb.get("initial", {})
    }

@router.get("/conversations", response_model=ConversationListResponse)
def get_user_conversations(
    user_id: int,
    active_only: bool = False,
    limit: int = 10,
    skip: int = 0,
    db: Session = Depends(get_db),
):
    """
    Lista de conversaciones del usuario.
    """
    # Verificar si el usuario existe y crearlo si no
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Crear usuario nuevo
        user = User(
            id=user_id,
            email=f"user{user_id}@example.com",  # Email temporal
            hashed_password="temppassword",      # Contraseña temporal
            full_name=f"Usuario {user_id}",      # Nombre temporal
            is_active=True
        )
        db.add(user)
        db.commit()
    
    total = (
        db.query(Conversation)
          .filter(Conversation.user_id == user_id)
          .count()
    )
    convs = LogService.get_user_conversations(
        db=db,
        user_id=user_id,
        include_active_only=active_only,
        limit=limit,
        skip=skip
    )

    items = []
    for c in convs:
        count = (
            db.query(MessageModel)
              .filter(MessageModel.conversation_id == c.id)
              .count()
        )
        items.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
            "is_active": c.is_active,
            "message_count": count
        })

    return ConversationListResponse(conversations=items, total=total)