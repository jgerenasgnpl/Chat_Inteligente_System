"""
Gestor de Timeouts para Conversaciones
Ubicación: app/services/conversation_timeout.py
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
import json
import logging

# Imports del proyecto
from app.models.conversation import Conversation
from app.services.log_service import LogService

logger = logging.getLogger(__name__)


class ConversationTimeoutManager:
    """Gestor de timeouts automáticos para conversaciones"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # ⚙️ PARÁMETROS CONFIGURABLES
        self.timeout_configs = {
            "default": {
                "timeout_hours": 12,
                "warning_hours": 10,  # Advertencia 2h antes
                "max_messages": 30,
                "auto_close_enabled": True
            },
            "premium": {
                "timeout_hours": 24,
                "warning_hours": 20,
                "max_messages": 50,
                "auto_close_enabled": True
            },
            "vip": {
                "timeout_hours": 48,
                "warning_hours": 40,
                "max_messages": 100,
                "auto_close_enabled": False  # VIP sin auto-cierre
            },
            "express": {
                "timeout_hours": 6,
                "warning_hours": 5,
                "max_messages": 20,
                "auto_close_enabled": True
            }
        }
    
    def get_timeout_config(self, conversation_type: str = "default") -> Dict[str, Any]:
        """Obtener configuración de timeout por tipo de conversación"""
        return self.timeout_configs.get(conversation_type, self.timeout_configs["default"])
    
    def should_close_conversation(self, conversation: Conversation, config: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluar si una conversación debe cerrarse automáticamente"""
        try:
            now = datetime.now()
            created_at = conversation.created_at
            
            # 1. ⏰ Verificar timeout por tiempo
            timeout_delta = timedelta(hours=config["timeout_hours"])
            time_expired = (now - created_at) > timeout_delta
            
            # 2. 📊 Verificar límite de mensajes
            message_count = self.get_message_count(conversation.id)
            message_limit_reached = message_count >= config["max_messages"]
            
            # 3. 🏁 Verificar si ya se completó la negociación
            negotiation_completed = conversation.current_state in [
                "acuerdo_generado", 
                "finalizar_conversacion",
                "conversacion_exitosa"
            ]
            
            # 4. 💤 Verificar inactividad (última interacción)
            last_activity = self.get_last_activity(conversation.id)
            inactive_hours = (now - last_activity).total_seconds() / 3600 if last_activity else 0
            
            should_close = (
                config["auto_close_enabled"] and 
                (time_expired or message_limit_reached or negotiation_completed)
            )
            
            return {
                "should_close": should_close,
                "reasons": {
                    "time_expired": time_expired,
                    "message_limit_reached": message_limit_reached,
                    "negotiation_completed": negotiation_completed,
                    "inactive_hours": inactive_hours
                },
                "stats": {
                    "age_hours": (now - created_at).total_seconds() / 3600,
                    "message_count": message_count,
                    "last_activity_hours_ago": inactive_hours,
                    "current_state": conversation.current_state
                },
                "config_used": config
            }
            
        except Exception as e:
            logger.error(f"❌ Error evaluando cierre de conversación {conversation.id}: {e}")
            return {"should_close": False, "error": str(e)}
    
    def close_conversation_gracefully(self, conversation_id: int, reason: str, stats: Dict[str, Any]) -> bool:
        """Cerrar conversación de forma elegante con mensaje de cierre"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                logger.warning(f"⚠️ Conversación {conversation_id} no encontrada para cierre")
                return False
            
            # 1. 💬 Crear mensaje de cierre personalizado
            closure_message = self.generate_closure_message(reason, stats, conversation)
            
            # 2. 📝 Registrar mensaje de cierre del sistema
            try:
                LogService.log_message(
                    db=self.db,
                    conversation_id=conversation_id,
                    sender_type="system",
                    text_content=closure_message,
                    previous_state=conversation.current_state,
                    next_state="conversacion_cerrada",
                    metadata=json.dumps({
                        "closure_reason": reason,
                        "auto_closed": True,
                        "closure_stats": stats,
                        "closure_timestamp": datetime.now().isoformat()
                    })
                )
            except Exception as e:
                logger.warning(f"⚠️ Error registrando mensaje de cierre: {e}")
                # Continuar con el cierre aunque falle el log
            
            # 3. 🔒 Actualizar estado de la conversación
            conversation.current_state = "conversacion_cerrada"
            conversation.is_active = False
            conversation.ended_at = datetime.now()
            
            # 4. 📊 Agregar metadata de cierre al contexto
            try:
                if hasattr(conversation, 'context_data') and conversation.context_data:
                    try:
                        context = json.loads(conversation.context_data) if isinstance(conversation.context_data, str) else conversation.context_data
                    except:
                        context = {}
                else:
                    context = {}
                
                context.update({
                    "conversation_closed": True,
                    "closure_reason": reason,
                    "closure_timestamp": datetime.now().isoformat(),
                    "final_stats": stats
                })
                
                if hasattr(conversation, 'context_data'):
                    conversation.context_data = json.dumps(context, ensure_ascii=False, default=str)
                
            except Exception as e:
                logger.warning(f"⚠️ Error actualizando contexto en cierre: {e}")
            
            # 5. 💾 Guardar cambios
            self.db.commit()
            
            logger.info(f"✅ Conversación {conversation_id} cerrada: {reason}")
            logger.info(f"📊 Stats: {stats['age_hours']:.1f}h, {stats['message_count']} mensajes")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cerrando conversación {conversation_id}: {e}")
            self.db.rollback()
            return False
    
    def generate_closure_message(self, reason: str, stats: Dict[str, Any], conversation: Conversation) -> str:
        """Generar mensaje de cierre personalizado"""
        
        # Obtener nombre del cliente si existe
        client_name = ""
        try:
            if hasattr(conversation, 'context_data') and conversation.context_data:
                context = json.loads(conversation.context_data) if isinstance(conversation.context_data, str) else conversation.context_data
                client_name = context.get("Nombre_del_cliente", "")
        except:
            pass
        
        greeting = f"Estimado/a {client_name}, " if client_name else "Hola, "
        
        if "time_expired" in reason:
            return f"""{greeting}tu sesión de negociación ha expirado después de {stats['age_hours']:.1f} horas. 
            
📞 **Para continuar**, puedes:
• Iniciar una nueva conversación
• Llamarnos al 123-456-7890
• Escribir a negociacion@systemgroup.com

¡Estamos aquí para ayudarte a encontrar la mejor solución!"""
            
        elif "message_limit" in reason:
            return f"""{greeting}hemos alcanzado el límite de {stats['message_count']} mensajes en esta conversación.
            
📞 **Para continuar tu negociación**:
• Te transferiremos con un asesor especializado
• Llámanos al 123-456-7890
• Escríbenos a negociacion@systemgroup.com

¡Tu caso es importante para nosotros!"""
            
        elif "negotiation_completed" in reason:
            return f"""{greeting}¡Felicitaciones! Tu proceso de negociación se ha completado exitosamente.
            
✅ **Próximos pasos**:
• Recibirás la documentación por email
• Un asesor te contactará para finalizar detalles
• Puedes consultar el estado en nuestro portal

¡Gracias por confiar en nosotros!"""
        
        else:
            return f"""{greeting}esta conversación se ha cerrado automáticamente.
            
📞 **¿Necesitas ayuda?**
• Inicia una nueva conversación
• Llámanos al 123-456-7890

¡Estamos aquí para ayudarte!"""
    
    def get_message_count(self, conversation_id: int) -> int:
        """Obtener número de mensajes en una conversación"""
        try:
            query = text("SELECT COUNT(*) FROM messages WHERE conversation_id = :conv_id")
            result = self.db.execute(query, {"conv_id": conversation_id})
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo count de mensajes: {e}")
            return 0
    
    def get_last_activity(self, conversation_id: int) -> Optional[datetime]:
        """Obtener timestamp de la última actividad"""
        try:
            query = text("""
                SELECT TOP 1 timestamp 
                FROM messages 
                WHERE conversation_id = :conv_id 
                ORDER BY timestamp DESC
            """)
            result = self.db.execute(query, {"conv_id": conversation_id})
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo última actividad: {e}")
            return None
    
    def send_warning_message(self, conversation_id: int, config: Dict[str, Any]) -> bool:
        """Enviar mensaje de advertencia antes del cierre"""
        try:
            warning_message = f"""⚠️ **Aviso importante**: Esta conversación se cerrará automáticamente en {config['timeout_hours'] - config['warning_hours']} horas por inactividad.

¿Necesitas más tiempo? Responde cualquier mensaje para mantener la sesión activa.

📞 También puedes llamarnos al 123-456-7890"""
            
            LogService.log_message(
                db=self.db,
                conversation_id=conversation_id,
                sender_type="system",
                text_content=warning_message,
                metadata=json.dumps({
                    "message_type": "timeout_warning",
                    "warning_sent_at": datetime.now().isoformat()
                })
            )
            
            self.db.commit()
            logger.info(f"⚠️ Advertencia enviada a conversación {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando advertencia a conversación {conversation_id}: {e}")
            return False
    
    def process_all_conversations(self) -> Dict[str, Any]:
        """Procesar todas las conversaciones activas para auto-cierre"""
        try:
            logger.info("🔄 Iniciando proceso de auto-cierre de conversaciones...")
            
            # Obtener todas las conversaciones activas
            active_conversations = self.db.query(Conversation).filter(
                Conversation.is_active == True
            ).all()
            
            stats = {
                "processed": 0,
                "closed": 0,
                "warnings_sent": 0,
                "errors": 0,
                "details": []
            }
            
            for conversation in active_conversations:
                try:
                    stats["processed"] += 1
                    
                    # Determinar tipo de conversación (podría venir del contexto)
                    conversation_type = self.determine_conversation_type(conversation)
                    config = self.get_timeout_config(conversation_type)
                    
                    # Evaluar si debe cerrarse
                    evaluation = self.should_close_conversation(conversation, config)
                    
                    if evaluation["should_close"]:
                        # Cerrar conversación
                        reason = ", ".join([k for k, v in evaluation["reasons"].items() if v])
                        success = self.close_conversation_gracefully(
                            conversation.id, 
                            reason, 
                            evaluation["stats"]
                        )
                        
                        if success:
                            stats["closed"] += 1
                            stats["details"].append({
                                "id": conversation.id,
                                "action": "closed",
                                "reason": reason,
                                "age_hours": evaluation["stats"]["age_hours"]
                            })
                        else:
                            stats["errors"] += 1
                    
                    else:
                        # Verificar si necesita advertencia
                        age_hours = evaluation["stats"]["age_hours"]
                        warning_threshold = config["warning_hours"]
                        
                        if age_hours >= warning_threshold and not self.has_warning_been_sent(conversation.id):
                            if self.send_warning_message(conversation.id, config):
                                stats["warnings_sent"] += 1
                                stats["details"].append({
                                    "id": conversation.id,
                                    "action": "warning_sent",
                                    "age_hours": age_hours
                                })
                
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"❌ Error procesando conversación {conversation.id}: {e}")
            
            logger.info(f"✅ Proceso completado: {stats['closed']} cerradas, {stats['warnings_sent']} advertencias")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error en proceso de auto-cierre: {e}")
            return {"error": str(e)}
    
    def determine_conversation_type(self, conversation: Conversation) -> str:
        """Determinar el tipo de conversación para aplicar configuración apropiada"""
        try:
            # Por defecto es "default"
            # Aquí puedes implementar lógica para determinar tipo:
            # - Por monto de deuda (VIP para deudas altas)
            # - Por tipo de cliente
            # - Por configuración manual
            
            if hasattr(conversation, 'context_data') and conversation.context_data:
                try:
                    context = json.loads(conversation.context_data) if isinstance(conversation.context_data, str) else conversation.context_data
                    
                    # Ejemplo: VIP para deudas > $100M
                    saldo = float(context.get("saldo_total", 0))
                    if saldo > 100000000:  # $100M
                        return "vip"
                    elif saldo > 10000000:  # $10M
                        return "premium"
                except:
                    pass
            
            return "default"
            
        except Exception:
            return "default"
    
    def has_warning_been_sent(self, conversation_id: int) -> bool:
        """Verificar si ya se envió advertencia a una conversación"""
        try:
            query = text("""
                SELECT COUNT(*) 
                FROM messages 
                WHERE conversation_id = :conv_id 
                    AND sender_type = 'system'
                    AND (
                        text_content LIKE '%Aviso importante%'
                        OR (metadata IS NOT NULL AND metadata LIKE '%timeout_warning%')
                    )
            """)
            result = self.db.execute(query, {"conv_id": conversation_id})
            return (result.scalar() or 0) > 0
        except Exception as e:
            logger.warning(f"⚠️ Error verificando advertencias previas: {e}")
            return False
    
    def _fix_proponer_planes_transition(self, user_message: str, contexto: Dict) -> Optional[str]:
        """
        🔧 FIX ESPECÍFICO para proponer_planes_pago → confirmar_plan_elegido
        """
        
        mensaje_lower = user_message.lower()
        
        # Palabras que indican selección de plan
        seleccion_keywords = [
            'acepto', 'aceptar', 'acepta', 'si', 'sí',
            'plan', 'opcion', 'primera', 'segunda', 'tercera',
            '1', '2', '3', 'uno', 'dos', 'tres',
            'de acuerdo', 'está bien', 'perfecto',
            'pago unico', 'cuotas', 'elegir'
        ]
        
        # Si el usuario indica selección, ir a confirmar_plan_elegido
        if any(keyword in mensaje_lower for keyword in seleccion_keywords):
            logger.info(f"🎯 FIX: Transición proponer_planes_pago → confirmar_plan_elegido")
            return "confirmar_plan_elegido"
        
        return None

    def extend_conversation_timeout(self, conversation_id: int, additional_hours: int, reason: str) -> bool:
        """Extender timeout de una conversación específica"""
        try:
            # Verificar que la conversación existe y está activa
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.is_active == True
            ).first()
            
            if not conversation:
                logger.warning(f"⚠️ Conversación {conversation_id} no encontrada o inactiva")
                return False
            
            # Registrar extensión en tabla específica (si existe)
            try:
                extension_query = text("""
                    INSERT INTO conversation_extensions (
                        conversation_id, extension_hours, reason, 
                        requested_by, original_timeout, new_timeout
                    ) VALUES (
                        :conv_id, :hours, :reason, 'system',
                        DATEADD(hour, 12, :created_at),
                        DATEADD(hour, :new_timeout, :created_at)
                    )
                """)
                
                self.db.execute(extension_query, {
                    "conv_id": conversation_id,
                    "hours": additional_hours,
                    "reason": reason,
                    "created_at": conversation.created_at,
                    "new_timeout": 12 + additional_hours  # 12h default + extensión
                })
                
            except Exception as e:
                logger.warning(f"⚠️ No se pudo registrar extensión en tabla: {e}")
                # Continuar aunque falle el registro
            
            # Mensaje informativo
            extension_message = f"""✅ **Tiempo extendido**: Se han agregado {additional_hours} horas adicionales a tu conversación.

**Motivo**: {reason}

Tu sesión ahora estará activa por más tiempo. ¡Aprovecha para resolver todas tus dudas!"""
            
            LogService.log_message(
                db=self.db,
                conversation_id=conversation_id,
                sender_type="system",
                text_content=extension_message,
                metadata=json.dumps({
                    "message_type": "timeout_extension",
                    "extension_hours": additional_hours,
                    "extension_reason": reason,
                    "extended_at": datetime.now().isoformat()
                })
            )
            
            self.db.commit()
            logger.info(f"✅ Conversación {conversation_id} extendida por {additional_hours}h: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error extendiendo conversación {conversation_id}: {e}")
            self.db.rollback()
            return False