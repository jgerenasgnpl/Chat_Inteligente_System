# ejemplo_variable_service.py
"""
Ejemplo de cómo usar correctamente el VariableService
"""

from app.services.variable_service import VariableService

def ejemplo_resolucion_variables(db, mensaje_con_variables, contexto_conversacion):
    """
    Ejemplo de cómo resolver variables en mensajes
    """
    
    # 1. Crear instancia del servicio
    variable_service = VariableService(db)
    
    # 2. Preparar contexto con datos específicos de la conversación
    contexto = {
        'saldo': 18500,  # Saldo real del cliente
        'nombre_cliente': 'Juan Pérez',
        'entidad': 'Banco Nacional',
        'descuento': 15,
        'num_cuotas': 6,
        'conversation_id': 123
    }
    
    # 3. Combinar con contexto general si existe
    if contexto_conversacion:
        contexto.update(contexto_conversacion)
    
    # 4. Resolver variables en el mensaje
    mensaje_resuelto = variable_service.resolver_variables(
        mensaje_con_variables, 
        contexto
    )
    
    return mensaje_resuelto

# Ejemplo de uso en conversation_manager:
class ConversationManager:
    def __init__(self, db, variable_service=None):
        self.db = db
        self.variable_service = variable_service or VariableService(db)
    
    def procesar_mensaje(self, user_message, conversation_id):
        # ... lógica de procesamiento ...
        
        # Obtener respuesta base
        respuesta_base = self._get_response_template(estado_actual)
        
        # Preparar contexto
        contexto = {
            'conversation_id': conversation_id,
            'saldo': self._get_saldo_cliente(conversation_id),
            'nombre_cliente': self._get_nombre_cliente(conversation_id),
            # ... otros datos del contexto ...
        }
        
        # IMPORTANTE: Resolver variables antes de devolver
        respuesta_final = self.variable_service.resolver_variables(
            respuesta_base, 
            contexto
        )
        
        return {
            'message': respuesta_final,
            'estado': estado_actual,
            'contexto': contexto
        }
