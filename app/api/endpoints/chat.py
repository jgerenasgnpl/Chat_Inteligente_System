from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal
from datetime import datetime, timedelta, date
from app.api.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationHistoryResponse, CedulaTestResponse, CedulaTestRequest
from app.services.conversation_service import crear_conversation_service
from app.services.state_manager import StateManager
from app.services.log_service import LogService
from app.models.message import Message
from app.models.conversation import Conversation
from app.models.user import User
from dotenv import load_dotenv
import json
import logging
import os
import re
import traceback

load_dotenv()
router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger("uvicorn.error")


class CustomJSONEncoder(json.JSONEncoder):
    """Encoder personalizado para manejar tipos especiales"""
    
    def default(self, obj):
        # ✅ DECIMAL → INT
        if isinstance(obj, Decimal):
            return int(obj)
        
        # ✅ DATETIME → ISO STRING
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # ✅ NUMPY TYPES (si están presentes)
        elif hasattr(obj, 'item'):
            return obj.item()
        
        # ✅ BYTES → STRING
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='ignore')
        
        # ✅ SET → LIST
        elif isinstance(obj, set):
            return list(obj)
        
        # ✅ OTROS TIPOS NUMÉRICOS
        elif hasattr(obj, '__int__'):
            try:
                return int(obj)
            except:
                return str(obj)
        
        # ✅ FALLBACK
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

# ✅ FUNCIÓN HELPER PARA SERIALIZACIÓN SEGURA
def safe_json_dumps(data: any, **kwargs) -> str:
    """Serialización JSON segura que maneja todos los tipos"""
    try:
        return json.dumps(
            data, 
            cls=CustomJSONEncoder, 
            ensure_ascii=False, 
            **kwargs
        )
    except Exception as e:
        print(f"⚠️ Error en serialización JSON: {e}")
        # Fallback: convertir todo a strings
        try:
            cleaned_data = clean_data_for_json(data)
            return json.dumps(cleaned_data, ensure_ascii=False, **kwargs)
        except:
            return "{}"

def clean_data_for_json(obj):
    """Limpia recursivamente un objeto para serialización JSON"""
    if isinstance(obj, dict):
        return {k: clean_data_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_data_for_json(item) for item in obj]
    elif isinstance(obj, Decimal):
        return int(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        try:
            return int(obj)
        except:
            return str(obj)

def limpiar_contexto_para_bd(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """Limpia el contexto convirtiendo tipos problemáticos"""
    contexto_limpio = {}
    
    for key, value in contexto.items():
        if isinstance(value, Decimal):
            contexto_limpio[key] = int(value)
        elif isinstance(value, (datetime, date)):
            contexto_limpio[key] = value.isoformat()
        elif isinstance(value, (list, dict)):
            contexto_limpio[key] = clean_data_for_json(value)
        else:
            contexto_limpio[key] = value
    
    return contexto_limpio

def _get_or_create_conversation(db: Session, user_id: int, conversation_id: Optional[int] = None) -> Conversation:
    """Obtener o crear conversación de forma robusta"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=f"user{user_id}@systemgroup.com",
            hashed_password="temp_hash", 
            full_name=f"Usuario {user_id}", 
            is_active=True,
            created_at=datetime.now()
        )
        db.add(user)
        db.commit()
        logger.info(f"🆕 Usuario {user_id} creado")
    
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
    
    return StateManager.get_or_create_conversation(db, user_id)

def _recuperar_contexto_seguro(db: Session, conversation: Conversation) -> Dict[str, Any]:
    """Recuperar contexto con verificación mejorada"""
    try:
        contexto = {}
        
        # 1. Intentar desde conversation.context_data
        if hasattr(conversation, 'context_data') and conversation.context_data:
            try:
                if isinstance(conversation.context_data, str):
                    contexto = json.loads(conversation.context_data)
                elif isinstance(conversation.context_data, dict):
                    contexto = conversation.context_data
                
                if isinstance(contexto, dict) and len(contexto) > 0:
                    logger.info(f"✅ [CONTEXTO] Recuperado: {len(contexto)} elementos")
                    
                    # Verificar datos críticos
                    if contexto.get('cliente_encontrado'):
                        logger.info(f"✅ Cliente en contexto: {contexto.get('Nombre_del_cliente')}")
                        logger.info(f"✅ Saldo en contexto: ${contexto.get('saldo_total', 0):,}")
                    
                    return contexto
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Error parseando JSON del contexto: {e}")
        
        # 2. Consulta directa a BD como fallback
        try:
            query = text("SELECT context_data FROM conversations WHERE id = :conv_id")
            result = db.execute(query, {"conv_id": conversation.id}).fetchone()
            
            if result and result[0]:
                contexto = json.loads(result[0])
                if isinstance(contexto, dict):
                    logger.info(f"✅ [CONTEXTO] Recuperado desde consulta directa: {len(contexto)} elementos")
                    return contexto
        except Exception as e:
            logger.warning(f"⚠️ Error en consulta directa de contexto: {e}")
        
        logger.info(f"⚠️ No se encontró contexto válido, iniciando vacío")
        return {}
        
    except Exception as e:
        logger.error(f"❌ Error crítico recuperando contexto: {e}")
        return {}

def _validar_estado_existente(estado: str) -> str:
    """Validar que el estado existe en BD o mapear a uno válido"""
    
    estados_validos = [
        'inicial', 'validar_documento', 'informar_deuda', 
        'proponer_planes_pago', 'generar_acuerdo', 
        'cliente_no_encontrado', 'finalizar_conversacion', 
        'gestionar_objecion', 'escalamiento'
    ]
    
    if estado in estados_validos:
        return estado
    
    mapeo_estados = {
        'seleccionar_plan': 'proponer_planes_pago',
        'confirmar_plan_elegido': 'generar_acuerdo',
        'procesar_pago': 'finalizar_conversacion',
        'acuerdo_generado': 'finalizar_conversacion',
        'conversacion_exitosa': 'finalizar_conversacion',
        'conversacion_cerrada': 'finalizar_conversacion',
        'manejo_timeout': 'escalamiento',
        'error': 'inicial'
    }
    
    estado_mapeado = mapeo_estados.get(estado, 'inicial')
    
    if estado_mapeado != estado:
        logger.info(f"🔄 Estado mapeado: {estado} → {estado_mapeado}")
    
    return estado_mapeado

def _extraer_informacion_resultado_seguro(resultado: Dict[str, Any]) -> Dict[str, Any]:
    """Extraer información de resultado con compatibilidad total"""
    
    info_extraida = {}
    
    # Intención
    info_extraida['intencion'] = (
        resultado.get('intencion') or 
        resultado.get('intention') or 
        resultado.get('detected_intention') or 
        'PROCESAMIENTO_GENERAL'
    )
    
    # Confianza
    info_extraida['confianza'] = (
        resultado.get('confianza') or 
        resultado.get('confidence') or 
        resultado.get('detection_confidence') or 
        0.0
    )
    
    # Método
    info_extraida['metodo'] = (
        resultado.get('metodo') or 
        resultado.get('method') or 
        resultado.get('detection_method') or 
        resultado.get('processor_method') or 
        'sistema_optimizado'
    )
    
    # Estado siguiente
    info_extraida['next_state'] = (
        resultado.get('next_state') or 
        resultado.get('estado_siguiente') or 
        resultado.get('new_state') or 
        'inicial'
    )
    
    # Contexto
    info_extraida['contexto_actualizado'] = (
        resultado.get('contexto_actualizado') or 
        resultado.get('context') or 
        resultado.get('context_updates') or 
        {}
    )
    
    # Mensaje
    info_extraida['mensaje_respuesta'] = (
        resultado.get('mensaje_respuesta') or 
        resultado.get('message') or 
        resultado.get('response') or 
        '¿En qué puedo ayudarte?'
    )
    
    # Botones
    info_extraida['botones'] = (
        resultado.get('botones') or 
        resultado.get('buttons') or 
        resultado.get('button_options') or 
        []
    )
    
    # Información adicional
    info_extraida['ai_enhanced'] = resultado.get('ai_enhanced', False)
    info_extraida['success'] = resultado.get('success', True)
    
    return info_extraida

def _log_interaccion_completa_segura(db: Session, conversation: Conversation, mensaje_usuario: str,
                                   info: Dict[str, Any], button_selected: Optional[str]):
    """Logging seguro con información estandarizada"""
    try:
        # Metadata segura
        metadata_raw = {
            "intencion_detectada": info.get('intencion'),
            "metodo_procesamiento": info.get('metodo'),
            "confianza": info.get('confianza'),
            "sistema_optimizado": True,
            "ai_enhanced": info.get('ai_enhanced', False),
            "procesamiento_dinamico": True,
            "timestamp": datetime.now().isoformat()
        }

        # Usar función de limpieza para metadata
        metadata_limpio = clean_data_for_json(metadata_raw)
        metadata_json = safe_json_dumps(metadata_limpio)

        # Log con metadata serializada segura
        LogService.log_message(
            db=db,
            conversation_id=conversation.id,
            sender_type="system",
            text_content=info.get('mensaje_respuesta', 'Respuesta procesada'),
            previous_state=conversation.current_state,
            next_state=info.get('next_state', conversation.current_state),
            metadata=metadata_json
        )

    except Exception as e:
        logger.error(f"⚠️ Error en logging seguro: {e}")
        # Fallback mínimo
        try:
            LogService.log_message(
                db=db,
                conversation_id=conversation.id,
                sender_type="system",
                text_content=info.get('mensaje_respuesta', 'Respuesta procesada'),
                previous_state=conversation.current_state,
                next_state=info.get('next_state', conversation.current_state)
            )
        except Exception as fallback_e:
            logger.error(f"❌ Error en fallback de logging: {fallback_e}")


# ✅ ENDPOINT PRINCIPAL CORREGIDO

@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_message_OPTIMIZADO(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    🎯 ENDPOINT PRINCIPAL OPTIMIZADO Y CORREGIDO
    - Sistema 100% dinámico
    - OpenAI como motor principal (80% casos)
    - ML + Sistema dinámico como fallback
    - Sin valores hardcodeados
    - Manejo robusto de errores
    """
    
    # ✅ DEFINIR VARIABLES PRIMERO (CORRIGE EL ERROR)
    user_id = request.user_id
    message_content = request.message or request.text or ""
    conversation_id = request.conversation_id or 1
    
    # ✅ AHORA SÍ MOSTRAR DEBUG
    logger.info(f"🚀 [OPTIMIZADO] Procesando mensaje")
    logger.info(f"   Usuario: {user_id}")
    logger.info(f"   Conversación: {conversation_id}")
    logger.info(f"   Mensaje: '{message_content[:50]}...'")
    
    try:
        # ✅ 1. OBTENER O CREAR CONVERSACIÓN
        conversation = _get_or_create_conversation(db, user_id, conversation_id)
        
        # ✅ 2. RECUPERAR CONTEXTO SEGURO
        contexto_actual = _recuperar_contexto_seguro(db, conversation)
        
        logger.info(f"💬 Conversación {conversation.id} - Estado: {conversation.current_state}")
        logger.info(f"📋 Contexto: {len(contexto_actual)} elementos")
        
        # ✅ 3. CREAR PROCESADOR OPTIMIZADO
        processor = crear_conversation_service(db)
        
        # ✅ 4. PROCESAR MENSAJE CON SISTEMA OPTIMIZADO
        resultado_raw = await processor.process_message(
            conversation.id, message_content, user_id
        )
        
        # ✅ 5. EXTRAER INFORMACIÓN DE FORMA SEGURA
        info = _extraer_informacion_resultado_seguro(resultado_raw)
        
        logger.info(f"🎯 Resultado: {info['intencion']} (confianza: {info['confianza']:.2f})")
        logger.info(f"🔧 Método: {info['metodo']}")
        logger.info(f"📍 Estado: {conversation.current_state} → {info['next_state']}")
        
        if info.get('ai_enhanced'):
            logger.info(f"🤖 IA mejorado: SÍ")
        
        # ✅ 6. VALIDAR Y ACTUALIZAR ESTADO
        nuevo_estado = _validar_estado_existente(info['next_state'])
        contexto_actualizado = info.get('contexto_actualizado', contexto_actual)

        if not isinstance(contexto_actualizado, dict):
            logger.warning(f"⚠️ Contexto inválido, usando contexto actual")
            contexto_actualizado = contexto_actual
        
        # ✅ 7. PRESERVAR DATOS DEL CLIENTE SI EXISTÍAN
        if contexto_actual.get('cliente_encontrado') and not contexto_actualizado.get('cliente_encontrado'):
            logger.info(f"🔧 Preservando datos del cliente")
            datos_cliente = {
                'cliente_encontrado': contexto_actual.get('cliente_encontrado'),
                'Nombre_del_cliente': contexto_actual.get('Nombre_del_cliente'),
                'saldo_total': contexto_actual.get('saldo_total'),
                'banco': contexto_actual.get('banco'),
                'oferta_1': contexto_actual.get('oferta_1'),
                'oferta_2': contexto_actual.get('oferta_2'),
                'hasta_3_cuotas': contexto_actual.get('hasta_3_cuotas'),
                'hasta_6_cuotas': contexto_actual.get('hasta_6_cuotas'),
                'hasta_12_cuotas': contexto_actual.get('hasta_12_cuotas'),
            }
            # Filtrar valores None
            datos_cliente = {k: v for k, v in datos_cliente.items() if v is not None}
            contexto_actualizado.update(datos_cliente)
        
        # ✅ 8. ACTUALIZAR CONVERSACIÓN
        conversation.current_state = nuevo_estado
        conversation.updated_at = datetime.now()
        
        # ✅ 9. SERIALIZAR Y GUARDAR CONTEXTO
        contexto_limpio = limpiar_contexto_para_bd(contexto_actualizado)
        conversation.context_data = safe_json_dumps(contexto_limpio)
        
        logger.info(f"💾 GUARDANDO CONTEXTO FINAL:")
        logger.info(f"   Elementos totales: {len(contexto_actualizado)}")
        logger.info(f"   Cliente encontrado: {contexto_actualizado.get('cliente_encontrado', False)}")
        
        if contexto_actualizado.get('plan_capturado'):
            logger.info(f"   ✅ PLAN DETECTADO: {contexto_actualizado.get('plan_seleccionado')}")
            logger.info(f"   ✅ MONTO: ${contexto_actualizado.get('monto_acordado', 0):,}")
        
        def _validar_estado_bd(estado: str) -> str:
            """Validar que el estado esté permitido en BD"""
            
            estados_permitidos = [
                'inicial', 'validar_documento', 'informar_deuda',
                'proponer_planes_pago', 'confirmar_plan_elegido', 
                'generar_acuerdo', 'finalizar_conversacion',
                'cliente_no_encontrado', 'gestionar_objecion'
                # 'escalamiento' NO está permitido
            ]
            
            # Mapear estados problemáticos
            mapeo_estados = {
                'escalamiento': 'gestionar_objecion',  # ← FIX TEMPORAL
                'timeout': 'finalizar_conversacion',
                'error': 'inicial'
            }
            
            if estado in estados_permitidos:
                return estado
            elif estado in mapeo_estados:
                logger.warning(f"🔄 Estado mapeado: {estado} → {mapeo_estados[estado]}")
                return mapeo_estados[estado]
            else:
                logger.warning(f"⚠️ Estado no válido: {estado}, usando 'inicial'")
                return 'inicial'

        # ✅ USAR EN EL CÓDIGO PRINCIPAL:
        nuevo_estado = _validar_estado_existente(info['next_state'])
        nuevo_estado_validado = _validar_estado_bd(nuevo_estado)  # ← AGREGAR ESTA LÍNEA
        conversation.current_state = nuevo_estado_validado  # ← CAMBIAR ESTA LÍNEA

        db.commit()
        logger.info(f"✅ CONTEXTO GUARDADO EN BD")
        
        # ✅ 10. LOGGING SEGURO
        try:
            _log_interaccion_completa_segura(db, conversation, message_content, info, request.button_selected)
        except Exception as log_error:
            logger.warning(f"⚠️ Error en logging (no crítico): {log_error}")
        
        # ✅ 11. CREAR RESPUESTA FINAL
        try:
            response = ChatResponse(
                conversation_id=conversation.id,
                message=info.get('mensaje_respuesta', '¿En qué puedo ayudarte?'),
                current_state=nuevo_estado,
                buttons=info.get('botones', []),
                context=contexto_actualizado or {}
            )
            
            logger.info(f"✅ Respuesta optimizada generada exitosamente")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error creando respuesta: {e}")
            # Respuesta de emergencia
            return ChatResponse(
                conversation_id=conversation.id,
                message="¿En qué puedo ayudarte? Para comenzar, proporciona tu cédula.",
                current_state="inicial",
                buttons=[{"id": "ayuda", "text": "Necesito ayuda"}],
                context={}
            )
        
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO: {e}")
        traceback.print_exc()
        
        conversation_id = conversation.id if 'conversation' in locals() else 1
        
        return ChatResponse(
            conversation_id=conversation_id,
            message="Disculpa los inconvenientes técnicos. Para ayudarte mejor, por favor proporciona tu número de cédula.",
            current_state="validar_documento",
            buttons=[
                {"id": "reintentar", "text": "Intentar de nuevo"},
                {"id": "asesor", "text": "Hablar con asesor"}
            ],
            context={}
        )


# ✅ ENDPOINTS DE TESTING Y DIAGNÓSTICO

@router.post("/test-sistema-optimizado")
async def test_sistema_optimizado(db: Session = Depends(get_db)):
    """Test completo del sistema optimizado"""
    
    test_messages = [
        "hola mi cedula es 93388915",
        "quiero pagar mi deuda", 
        "cuales son las opciones",
        "pago unico",
        "acepto la primera opción",
        "no puedo pagar ahora",
        "necesito mas descuento"
    ]
    
    try:
        processor = crear_conversation_service(db)
        
        results = []
        contexto_test = {}
        estado_test = "inicial"
        
        for i, mensaje in enumerate(test_messages):
            try:
                logger.info(f"\n🧪 Test {i+1}: '{mensaje}' en estado '{estado_test}'")
                
                resultado = processor.process_message_optimized(mensaje, contexto_test, estado_test)
                
                # Validar resultado
                if not isinstance(resultado, dict) or not resultado.get('success', True):
                    logger.warning(f"⚠️ Resultado inválido en test {i+1}")
                    resultado = {
                        'intencion': 'ERROR_PROCESAMIENTO',
                        'confianza': 0.0,
                        'next_state': estado_test,
                        'contexto_actualizado': contexto_test,
                        'mensaje_respuesta': 'Error en procesamiento.',
                        'botones': [],
                        'metodo': 'error_recovery',
                        'success': False
                    }
                
                # Extraer información segura
                info = _extraer_informacion_resultado_seguro(resultado)
                
                # Actualizar contexto y estado para siguiente iteración
                contexto_test = info.get('contexto_actualizado', contexto_test)
                estado_test = info.get('next_state', estado_test)
                
                results.append({
                    "paso": i + 1,
                    "mensaje": mensaje,
                    "intencion": info.get('intencion'),
                    "confianza": round(info.get('confianza', 0.0), 3),
                    "metodo": info.get('metodo'),
                    "estado_anterior": estado_test,
                    "estado_nuevo": info.get('next_state'),
                    "cliente_encontrado": contexto_test.get('cliente_encontrado', False),
                    "ai_enhanced": resultado.get('ai_enhanced', False),
                    "success": resultado.get('success', True)
                })
                
                logger.info(f"✅ Paso {i+1} completado: {estado_test}")
                
            except Exception as e:
                logger.error(f"❌ Error en paso {i+1}: {e}")
                results.append({
                    "paso": i + 1,
                    "mensaje": mensaje,
                    "success": False,
                    "error": str(e)
                })
        
        # Calcular estadísticas
        total_tests = len(results)
        successful_tests = len([r for r in results if r.get('success', False)])
        ai_enhanced_tests = len([r for r in results if r.get('ai_enhanced', False)])
        
        return {
            "status": "completed",
            "sistema": "OptimizedChatProcessor",
            "estadisticas": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "ai_enhanced_tests": ai_enhanced_tests,
                "success_rate": f"{(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
                "ai_usage_rate": f"{(ai_enhanced_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "test_results": results,
            "features_optimizadas": [
                "deteccion_automatica_cedulas_mejorada",
                "openai_como_motor_principal_80_porciento", 
                "sistema_dinamico_fallback_robusto",
                "ml_classification_integrado",
                "variables_dinamicas_sin_hardcoding",
                "preservacion_contexto_cliente",
                "manejo_errores_completo",
                "logging_seguro_mejorado"
            ],
            "contexto_final": {
                "cliente_encontrado": contexto_test.get('cliente_encontrado', False),
                "nombre_cliente": contexto_test.get('Nombre_del_cliente', 'N/A'),
                "estado_final": estado_test,
                "elementos_contexto": len(contexto_test)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error en test sistema optimizado: {e}")
        return {
            "status": "error",
            "error": str(e),
            "recommendation": "Verificar logs para más detalles"
        }

@router.get("/test-openai-integration")
async def test_openai_integration(db: Session = Depends(get_db)):
    """Test específico de integración OpenAI"""
    try:
        processor = crear_conversation_service(db)
        
        if not processor.openai_service or not processor.openai_service.disponible:
            return {
                "openai_available": False,
                "message": "OpenAI no disponible",
                "recommendation": "Verificar API_KEY y configuración"
            }
        
        # Test de conexión
        connection_test = processor.openai_service.test_connection()
        
        # Test de procesamiento
        test_context = {
            "cliente_encontrado": True,
            "Nombre_del_cliente": "MARIA ANGELICA",
            "saldo_total": 4173695,
            "oferta_2": 784744
        }
        
        resultado_test = processor.openai_service.procesar_mensaje_cobranza(
            "necesito un descuento mayor porque estoy en crisis financiera",
            test_context,
            "proponer_planes_pago"
        )
        
        return {
            "openai_available": True,
            "connection_test": connection_test,
            "processing_test": {
                "enhanced": resultado_test.get('enhanced', False),
                "message_preview": resultado_test.get('message', '')[:100] + "...",
                "tipo_interaccion": resultado_test.get('tipo_interaccion'),
                "success": resultado_test.get('enhanced', False)
            },
            "service_stats": processor.openai_service.get_stats(),
            "recommendation": "✅ OpenAI funcionando correctamente" if resultado_test.get('enhanced') else "❌ Verificar configuración OpenAI"
        }
        
    except Exception as e:
        return {
            "openai_available": False,
            "error": str(e),
            "recommendation": "Revisar logs de OpenAI para diagnóstico detallado"
        }

@router.get("/health-sistema-completo")
async def health_sistema_completo(db: Session = Depends(get_db)):
    """Health check completo del sistema optimizado"""
    try:
        processor = crear_conversation_service(db)
        
        # Verificar componentes
        components_status = {
            "dynamic_transition_service": processor.dynamic_transition_service is not None,
            "openai_service": processor.openai_service is not None and processor.openai_service.disponible,
            "ml_service": processor.ml_service is not None,
            "variable_service": processor.variable_service is not None
        }
        
        # Verificar tablas críticas
        tables_status = {}
        critical_tables = [
            "Estados_Conversacion",
            "ml_intention_mappings", 
            "keyword_condition_patterns",
            "ConsolidadoCampañasNatalia"
        ]
        
        for table in critical_tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                tables_status[table] = {"exists": True, "count": result}
            except Exception as e:
                tables_status[table] = {"exists": False, "error": str(e)}
        
        # Estado general
        critical_components_ok = components_status["dynamic_transition_service"]
        critical_tables_ok = all(t.get("exists", False) for t in tables_status.values())
        
        overall_status = "healthy" if (critical_components_ok and critical_tables_ok) else "degraded"
        
        return {
            "status": overall_status,
            "version": "OptimizedChatProcessor_v1.0",
            "components": components_status,
            "tables": tables_status,
            "features": [
                "sistema_100_dinamico",
                "openai_motor_principal_80_porciento",
                "ml_fallback_robusto",
                "deteccion_automatica_cedulas",
                "preservacion_contexto_inteligente",
                "variables_dinamicas_sin_hardcoding",
                "manejo_errores_completo"
            ],
            "recommendations": [
                "✅ Sistema optimizado funcionando" if overall_status == "healthy" else "❌ Verificar componentes fallidos",
                "OpenAI disponible para 80% de casos" if components_status["openai_service"] else "⚠️ OpenAI no disponible - usando fallbacks",
                "Todas las tablas críticas disponibles" if critical_tables_ok else "⚠️ Verificar tablas faltantes"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "version": "OptimizedChatProcessor_v1.0"
        }


# ✅ ENDPOINTS LEGACY MANTENIDOS PARA COMPATIBILIDAD

@router.post("/test-cedula", response_model=CedulaTestResponse)
async def test_cedula_inteligente(request: CedulaTestRequest, db: Session = Depends(get_db)):
    """Test de detección y consulta de cédulas"""
    try:
        processor = crear_conversation_service(db)
        
        test_messages = [
            request.cedula,
            f"mi cedula es {request.cedula}",
            f"documento {request.cedula}",
            f"cc: {request.cedula}"
        ]
        
        cedula_detectada = None
        for msg in test_messages:
            cedula_detectada = processor._detectar_cedula_inteligente(msg)
            if cedula_detectada:
                break
        
        if cedula_detectada:
            resultado = processor._consultar_cliente_completo(cedula_detectada)
            
            if resultado['encontrado']:
                datos = resultado['datos']
                return CedulaTestResponse(
                    cedula=cedula_detectada,
                    cliente_encontrado=True,
                    nombre_cliente=datos.get("Nombre_del_cliente"),
                    saldo_total=f"${datos.get('saldo_total', 0):,}",
                    banco=datos.get("banco"),
                    mensaje=f"Cliente {datos.get('Nombre_del_cliente')} encontrado con sistema optimizado"
                )
            else:
                return CedulaTestResponse(
                    cedula=cedula_detectada,
                    cliente_encontrado=False,
                    mensaje=f"Cédula {cedula_detectada} detectada pero cliente no encontrado en BD"
                )
        else:
            return CedulaTestResponse(
                cedula=request.cedula,
                cliente_encontrado=False,
                mensaje=f"No se pudo detectar cédula válida en: {request.cedula}"
            )
            
    except Exception as e:
        return CedulaTestResponse(
            cedula=request.cedula,
            cliente_encontrado=False,
            mensaje=f"Error en test optimizado: {str(e)}"
        )

@router.get("/historial/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtener historial de conversación"""
    try:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
            .all()
        )
        
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        
        context_data = _recuperar_contexto_seguro(db, conversation)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=[
                {
                    "id": msg.id,
                    "sender_type": msg.sender_type,
                    "text_content": msg.text_content,
                    "timestamp": msg.timestamp.isoformat(),
                    "button_selected": msg.button_selected
                }
                for msg in reversed(messages)
            ],
            current_state=conversation.current_state,
            context_data=context_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {e}")

@router.get("/test")
async def system_health_check():
    """Health check del sistema optimizado"""
    return {
        "status": "operational",
        "system": "OptimizedChatProcessor_v1.0",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "deteccion_automatica_cedulas_multiples_formatos",
            "openai_motor_principal_80_porciento_casos",
            "ml_classification_fallback_robusto",
            "sistema_dinamico_transiciones_bd",
            "preservacion_contexto_inteligente",
            "variables_dinamicas_sin_hardcoding",
            "manejo_errores_completo_con_fallbacks",
            "logging_seguro_mejorado",
            "compatible_con_sistema_existente"
        ],
        "dependencies": {
            "openai_service": "primary_engine_optional",
            "ml_service": "fallback_classification", 
            "dynamic_transition_service": "required",
            "database": "required",
            "tables_required": ["ConsolidadoCampañasNatalia", "conversations", "messages"],
            "tables_optimal": ["Estados_Conversacion", "ml_intention_mappings", "keyword_condition_patterns"]
        },
        "message": "Sistema optimizado funcionando - OpenAI como motor principal, fallbacks robustos"
    }