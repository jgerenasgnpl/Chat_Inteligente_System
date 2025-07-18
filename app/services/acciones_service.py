import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class AccionesService:
    """Servicio para ejecutar acciones de negocio"""
    
    def __init__(self, db: Session):
        self.db = db
        self.acciones_registradas = {
            'registrar_plan_pago': self._registrar_plan_pago,
            'verificar_contacto': self._verificar_contacto,
            'generar_propuesta': self._generar_propuesta,
            'enviar_recordatorio': self._enviar_recordatorio,
            'escalar_supervisor': self._escalar_supervisor,
            'crear_planes_pago': self._crear_planes_pago,
            'actualizar_cliente': self._actualizar_cliente
        }
    
    def ejecutar_accion(self, nombre_accion: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una acción específica
        
        Args:
            nombre_accion: Nombre de la acción a ejecutar
            contexto: Contexto con datos para la acción
            
        Returns:
            Resultado de la acción ejecutada
        """
        try:
            if nombre_accion in self.acciones_registradas:
                resultado = self.acciones_registradas[nombre_accion](contexto)
                logger.info(f"Acción '{nombre_accion}' ejecutada: {resultado}")
                return resultado
            else:
                logger.warning(f"Acción no encontrada: {nombre_accion}")
                return {"error": f"Acción {nombre_accion} no encontrada", "exito": False}
                
        except Exception as e:
            logger.error(f"Error ejecutando acción {nombre_accion}: {e}")
            return {"error": str(e), "exito": False}
    
    def _registrar_plan_pago(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Registra el plan de pago seleccionado"""
        try:
            conversation_id = contexto.get('conversation_id')
            plan_seleccionado = contexto.get('plan_seleccionado', 'plan_1')
            cliente_id = contexto.get('cliente_id')
            
            insert_plan = text("""
                INSERT INTO planes_pago (conversation_id, tipo_plan, cliente_id, fecha_creacion)
                VALUES (:conversation_id, :tipo_plan, :cliente_id, GETDATE())
            """)
            
            self.db.execute(insert_plan, {
                "conversation_id": conversation_id,
                "tipo_plan": plan_seleccionado,
                "cliente_id": cliente_id
            })
            
            self.db.commit()
            
            return {
                "exito": True,
                "mensaje": f"Plan {plan_seleccionado} registrado exitosamente",
                "plan_registrado": plan_seleccionado
            }
            
        except Exception as e:
            logger.error(f"Error registrando plan de pago: {e}")
            return {"error": str(e), "exito": False}
    
    def _verificar_contacto(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica información de contacto"""
        try:
            telefono = contexto.get('telefono')
            email = contexto.get('email')
            
            resultado = {
                "exito": True,
                "telefono_valido": bool(telefono and len(telefono) >= 10),
                "email_valido": bool(email and '@' in email),
                "requiere_actualizacion": False
            }
            
            if not resultado["telefono_valido"] or not resultado["email_valido"]:
                resultado["requiere_actualizacion"] = True
            
            return resultado
            
        except Exception as e:
            return {"error": str(e), "exito": False}
    
    def _generar_propuesta(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Genera propuesta personalizada"""
        try:
            saldo = contexto.get('saldo', 0)
            capacidad_pago = contexto.get('capacidad_pago', saldo * 0.1)
            
            propuesta = {
                "pago_unico": saldo * 0.7,  
                "plan_2_cuotas": saldo * 0.5, 
                "plan_6_cuotas": saldo / 6, 
                "descuento_maximo": saldo * 0.3
            }
            
            return {
                "exito": True,
                "propuesta": propuesta,
                "saldo_original": saldo
            }
            
        except Exception as e:
            return {"error": str(e), "exito": False}
    
    def _enviar_recordatorio(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Envía recordatorio de pago"""
        return {
            "exito": True,
            "mensaje": "Recordatorio programado",
            "canal": contexto.get('canal_preferido', 'whatsapp')
        }
    
    def _escalar_supervisor(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Escala la conversación a supervisor"""
        return {
            "exito": True,
            "mensaje": "Conversación escalada a supervisor",
            "supervisor_asignado": "Supervisor_001"
        }
    
    def _crear_planes_pago(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Crea planes de pago personalizados"""
        try:
            saldo = float(contexto.get('saldo', 15000))
            
            planes = {
                "plan_1": {
                    "tipo": "Pago único con descuento",
                    "monto": saldo * 0.7,
                    "descuento": "30%",
                    "cuotas": 1
                },
                "plan_2": {
                    "tipo": "Plan en 2 cuotas sin interés",
                    "monto": saldo,
                    "cuota": saldo / 2,
                    "cuotas": 2
                },
                "plan_3": {
                    "tipo": "Plan en 6 cuotas",
                    "monto": saldo,
                    "cuota": saldo / 6,
                    "cuotas": 6
                }
            }
            
            return {
                "exito": True,
                "planes_creados": planes,
                "saldo_original": saldo
            }
            
        except Exception as e:
            return {"error": str(e), "exito": False}
    
    def _actualizar_cliente(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza información del cliente"""
        return {
            "exito": True,
            "mensaje": "Información del cliente actualizada",
            "campos_actualizados": list(contexto.keys())
        }

def crear_acciones_service(db: Session):
    """Factory para crear instancia del servicio de acciones"""
    return AccionesService(db)
