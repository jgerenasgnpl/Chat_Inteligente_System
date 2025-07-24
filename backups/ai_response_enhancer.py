import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.openai_service import openai_cobranza_service

logger = logging.getLogger(__name__)

class AIResponseEnhancer:
    """
    ✅ SERVICIO PARA MEJORAR RESPUESTAS CON IA
    - No limita la entrada del usuario
    - Mejora las respuestas del sistema
    - Mantiene el contexto de cobranza
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_service = openai_cobranza_service
    
    def enhance_response(self, base_response: str, context: Dict[str, Any], 
                        user_message: str, current_state: str) -> str:
        """✅ MEJORAR RESPUESTA CON IA SIN LIMITAR ENTRADA DEL USUARIO"""
        
        try:
            # ✅ 1. VERIFICAR SI DEBE USAR IA
            if not self._should_enhance(base_response, context, current_state):
                return base_response
            
            # ✅ 2. CREAR PROMPT ESPECÍFICO PARA MEJORAR RESPUESTA
            enhancement_prompt = self._create_enhancement_prompt(
                base_response, context, user_message, current_state
            )
            
            # ✅ 3. LLAMAR A IA PARA MEJORAR
            enhanced_response = self.openai_service.enhance_response(
                enhancement_prompt, context
            )
            
            # ✅ 4. VALIDAR Y DEVOLVER RESPUESTA MEJORADA
            if enhanced_response and len(enhanced_response) > 10:
                logger.info(f"✅ Respuesta mejorada con IA")
                return enhanced_response
            else:
                return base_response
                
        except Exception as e:
            logger.error(f"❌ Error mejorando respuesta: {e}")
            return base_response
    
    def _should_enhance(self, response: str, context: Dict, state: str) -> bool:
        """✅ DETERMINAR SI DEBE MEJORAR CON IA"""
        
        # ✅ NO MEJORAR SI NO HAY DATOS DEL CLIENTE
        if not context.get('cliente_encontrado'):
            return False
        
        # ✅ MEJORAR SOLO EN ESTADOS CRÍTICOS
        critical_states = [
            'proponer_planes_pago',
            'generar_acuerdo', 
            'gestionar_objecion',
            'aclarar_proceso_pago'
        ]
        
        if state not in critical_states:
            return False
        
        # ✅ MEJORAR SI LA RESPUESTA ES GENÉRICA
        generic_indicators = [
            '¿en qué puedo ayudarte?',
            'para ayudarte',
            'proporciona tu cédula'
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in generic_indicators)
    
    def _create_enhancement_prompt(self, base_response: str, context: Dict, 
                                 user_message: str, state: str) -> str:
        """✅ CREAR PROMPT PARA MEJORA ESPECÍFICA"""
        
        cliente_info = self._extract_client_info(context)
        
        prompt = f"""
        CONTEXTO: Sistema de cobranza inteligente
        ESTADO ACTUAL: {state}
        MENSAJE DEL CLIENTE: {user_message}
        
        INFORMACIÓN DEL CLIENTE:
        {cliente_info}
        
        RESPUESTA BASE GENERADA:
        {base_response}
        
        INSTRUCCIONES:
        1. Mejora la respuesta manteniéndola profesional y empática
        2. Incluye información específica del cliente cuando sea relevante
        3. Mantén el tono de negociación de deudas
        4. No agregues información falsa
        5. Máximo 200 palabras
        6. Incluye emojis apropiados para el contexto
        
        RESPUESTA MEJORADA:
        """
        
        return prompt
    
    def _extract_client_info(self, context: Dict) -> str:
        """✅ EXTRAER INFORMACIÓN RELEVANTE DEL CLIENTE"""
        
        info_parts = []
        
        if context.get('Nombre_del_cliente'):
            info_parts.append(f"Cliente: {context['Nombre_del_cliente']}")
        
        if context.get('saldo_total'):
            info_parts.append(f"Saldo: ${context['saldo_total']:,}")
        
        if context.get('banco'):
            info_parts.append(f"Entidad: {context['banco']}")
        
        if context.get('oferta_2'):
            info_parts.append(f"Oferta disponible: ${context['oferta_2']:,}")
        
        return "\n".join(info_parts) if info_parts else "Sin información específica"


def create_ai_response_enhancer(db: Session) -> AIResponseEnhancer:
    """Factory para crear el servicio de mejora de respuestas"""
    return AIResponseEnhancer(db)