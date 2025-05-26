# app/services/condiciones_service.py
"""
Servicio para evaluar condiciones de negocio
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CondicionesService:
    """Servicio para evaluar condiciones de negocio"""
    
    def __init__(self):
        self.condiciones_registradas = {
            'cliente_selecciona_plan': self._cliente_selecciona_plan,
            'cliente_muestra_frustracion': self._cliente_muestra_frustracion,
            'tiene_documento_valido': self._tiene_documento_valido,
            'saldo_mayor_1000': self._saldo_mayor_1000,
            'primera_conversacion': self._primera_conversacion
        }
    
    def evaluar_condicion(self, nombre_condicion: str, contexto: Dict[str, Any]) -> bool:
        """
        Evalúa una condición específica
        
        Args:
            nombre_condicion: Nombre de la condición a evaluar
            contexto: Contexto con datos para la evaluación
            
        Returns:
            True si la condición se cumple, False caso contrario
        """
        try:
            if nombre_condicion in self.condiciones_registradas:
                resultado = self.condiciones_registradas[nombre_condicion](contexto)
                logger.info(f"Condición '{nombre_condicion}': {resultado}")
                return resultado
            else:
                logger.warning(f"Condición no encontrada: {nombre_condicion}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluando condición {nombre_condicion}: {e}")
            return False
    
    def _cliente_selecciona_plan(self, contexto: Dict[str, Any]) -> bool:
        """Verifica si el cliente seleccionó un plan"""
        mensaje = contexto.get('mensaje', '').lower()
        plan_seleccionado = contexto.get('plan_seleccionado')
        
        # Palabras clave que indican selección de plan
        palabras_plan = ['1', '2', '3', 'uno', 'dos', 'tres', 'primero', 'segundo', 'tercero', 
                        'pago único', 'cuotas', 'plan']
        
        if plan_seleccionado:
            return True
            
        return any(palabra in mensaje for palabra in palabras_plan)
    
    def _cliente_muestra_frustracion(self, contexto: Dict[str, Any]) -> bool:
        """Detecta signos de frustración en el cliente"""
        mensaje = contexto.get('mensaje', '').lower()
        
        palabras_frustracion = [
            'no puedo', 'imposible', 'no tengo', 'dificil', 'problema',
            'no entiendo', 'complicado', 'ayuda', 'perdido', 'confundido'
        ]
        
        return any(palabra in mensaje for palabra in palabras_frustracion)
    
    def _tiene_documento_valido(self, contexto: Dict[str, Any]) -> bool:
        """Verifica si el documento es válido"""
        documento = contexto.get('documento', '')
        mensaje = contexto.get('mensaje', '')
        
        # Buscar cédula en el mensaje (formato colombiano)
        import re
        patron_cedula = r'\b\d{7,10}\b'
        
        if documento and len(documento) >= 7:
            return True
            
        if re.search(patron_cedula, mensaje):
            return True
            
        return False
    
    def _saldo_mayor_1000(self, contexto: Dict[str, Any]) -> bool:
        """Verifica si el saldo es mayor a $1000"""
        saldo = contexto.get('saldo', 0)
        
        try:
            saldo_numerico = float(saldo)
            return saldo_numerico > 1000
        except (ValueError, TypeError):
            return False
    
    def _primera_conversacion(self, contexto: Dict[str, Any]) -> bool:
        """Verifica si es la primera conversación del cliente"""
        conversaciones_previas = contexto.get('conversaciones_previas', 0)
        return conversaciones_previas == 0

def crear_condiciones_service():
    """Factory para crear instancia del servicio de condiciones"""
    return CondicionesService()
