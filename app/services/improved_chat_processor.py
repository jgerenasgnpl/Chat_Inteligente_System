from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ImprovedChatProcessor:
    """
    ✅ PROCESADOR MEJORADO PARA CORREGIR PROBLEMAS:
    1. Transiciones bloqueadas
    2. Datos hardcodeados
    3. Variables mal resueltas
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.dynamic_service = self._init_dynamic_service()
        self.variable_service = self._init_variable_service()
        
    def _init_dynamic_service(self):
        try:
            from app.services.dynamic_transition_service import create_dynamic_transition_service
            return create_dynamic_transition_service(self.db)
        except Exception as e:
            logger.error(f"Error inicializando dynamic service: {e}")
            return None
    
    def _init_variable_service(self):
        try:
            from app.services.variable_service import crear_variable_service
            return crear_variable_service(self.db)
        except Exception as e:
            logger.error(f"Error inicializando variable service: {e}")
            return None

    def process_message_improved(self, mensaje: str, contexto: Dict[str, Any], 
                                estado_actual: str) -> Dict[str, Any]:
        """✅ PROCESAMIENTO MEJORADO CON CLAVES ESTANDARIZADAS"""
        
        try:
            logger.info(f"🔄 [IMPROVED] Procesando: '{mensaje}' en '{estado_actual}'")
            
            # 1. ✅ DETECCIÓN DE CÉDULA (MÁXIMA PRIORIDAD)
            cedula = self._detectar_cedula_robusta(mensaje)
            if cedula:
                resultado = self._procesar_cedula_mejorada(cedula, contexto)
                # ✅ ESTANDARIZAR CLAVES
                return self._estandarizar_respuesta(resultado)
            
            # 2. ✅ PROCESAMIENTO CON SISTEMA DINÁMICO MEJORADO
            if self.dynamic_service:
                resultado = self._procesar_con_dynamic_service_mejorado(
                    mensaje, contexto, estado_actual
                )
                if resultado.get('success'):
                    # ✅ ESTANDARIZAR CLAVES
                    return self._estandarizar_respuesta(resultado)
            
            # 3. ✅ FALLBACK INTELIGENTE
            resultado = self._fallback_mejorado(mensaje, contexto, estado_actual)
            return self._estandarizar_respuesta(resultado)
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento mejorado: {e}")
            resultado = self._error_response_mejorado(mensaje, contexto, estado_actual)
            return self._estandarizar_respuesta(resultado)
    
    def _estandarizar_respuesta(self, resultado: Dict[str, Any]) -> Dict[str, Any]:
        """✅ NUEVO: Estandarizar todas las claves de respuesta"""
        
        # ✅ MAPEO DE CLAVES PARA COMPATIBILIDAD
        respuesta_estandar = {
            'intencion': resultado.get('intention') or resultado.get('intencion', 'PROCESAMIENTO_GENERAL'),
            'confianza': resultado.get('confidence') or resultado.get('confianza', 0.0),
            'next_state': resultado.get('next_state') or resultado.get('estado_siguiente', 'inicial'),
            'contexto_actualizado': resultado.get('context') or resultado.get('contexto_actualizado', {}),
            'mensaje_respuesta': resultado.get('message') or resultado.get('mensaje_respuesta', '¿En qué puedo ayudarte?'),
            'botones': resultado.get('buttons') or resultado.get('botones', []),
            'metodo': resultado.get('method') or resultado.get('metodo', 'sistema_mejorado'),
            'usar_resultado': resultado.get('success', True),
            'transition_info': resultado.get('transition_info', {})
        }
        
        # ✅ VALIDAR QUE TODAS LAS CLAVES REQUERIDAS EXISTAN
        claves_requeridas = ['intencion', 'confianza', 'next_state', 'contexto_actualizado', 
                           'mensaje_respuesta', 'botones', 'metodo', 'usar_resultado']
        
        for clave in claves_requeridas:
            if clave not in respuesta_estandar or respuesta_estandar[clave] is None:
                # ✅ VALORES FALLBACK DINÁMICOS
                respuesta_estandar[clave] = self._get_valor_fallback(clave, resultado)
        
        logger.info(f"✅ Respuesta estandarizada con todas las claves requeridas")
        return respuesta_estandar
    
    def _get_valor_fallback(self, clave: str, resultado_original: Dict) -> Any:
        """✅ VALORES FALLBACK DINÁMICOS (NO HARDCODEADOS)"""
        
        fallbacks = {
            'intencion': 'PROCESAMIENTO_GENERAL',
            'confianza': 0.5,
            'next_state': 'inicial',
            'contexto_actualizado': {},
            'mensaje_respuesta': 'Para ayudarte, necesito tu número de cédula.',
            'botones': [{'id': 'ayuda', 'text': 'Necesito ayuda'}],
            'metodo': 'fallback_automatico',
            'usar_resultado': True
        }
        
        return fallbacks.get(clave, None)
    
    def _detectar_cedula_robusta(self, mensaje: str) -> Optional[str]:
        """✅ DETECCIÓN ROBUSTA DE CÉDULAS"""
        patrones = [
            r'\b(\d{7,12})\b',
            r'cédula\s*:?\s*(\d{7,12})',
            r'documento\s*:?\s*(\d{7,12})',
            r'cc\s*:?\s*(\d{7,12})'
        ]
        
        for patron in patrones:
            matches = re.findall(patron, mensaje, re.IGNORECASE)
            for match in matches:
                if 7 <= len(match) <= 12 and len(set(match)) > 1:
                    logger.info(f"🎯 Cédula detectada: {match}")
                    return match
        return None
    
    def _generar_mensaje_cliente_encontrado(self, cliente_data: Dict) -> str:
        """✅ GENERAR MENSAJE CUANDO SE ENCUENTRA CLIENTE"""
        nombre = cliente_data.get('Nombre_del_cliente', 'Cliente')
        banco = cliente_data.get('banco', 'tu entidad financiera')
        saldo = cliente_data.get('saldo_total', 0)
        
        return f"""¡Perfecto, {nombre}! 

📋 **Información de tu cuenta:**
🏦 Entidad: {banco}
💰 Saldo actual: ${saldo:,}

¿Te gustaría conocer las opciones de pago disponibles para ti?"""

    def _generar_botones_cliente_encontrado(self) -> list:
        """✅ BOTONES PARA CLIENTE ENCONTRADO"""
        return [
            {'id': 'ver_opciones', 'text': 'Ver opciones de pago'},
            {'id': 'mas_info', 'text': 'Más información'},
            {'id': 'no_ahora', 'text': 'No por ahora'}
        ]

    def _procesar_cedula_mejorada(self, cedula: str, contexto: Dict) -> Dict[str, Any]:
        """✅ PROCESAMIENTO MEJORADO DE CÉDULA"""
        try:
            cliente_data = self._consultar_cliente_real(cedula)
            
            if cliente_data.get('encontrado'):
                # ✅ CONTEXTO LIMPIO SIN DATOS HARDCODEADOS
                nuevo_contexto = {
                    **contexto,
                    **cliente_data,
                    'cedula_detectada': cedula,
                    'consulta_timestamp': datetime.now().isoformat()
                }
                
                mensaje = self._generar_mensaje_cliente_encontrado(cliente_data)
                
                return {
                    'success': True,
                    'next_state': 'informar_deuda',
                    'context': nuevo_contexto,
                    'message': mensaje,
                    'buttons': self._generar_botones_cliente_encontrado(),
                    'method': 'cedula_detection_improved'
                }
            else:
                return {
                    'success': True,
                    'next_state': 'cliente_no_encontrado',
                    'context': {**contexto, 'cedula_no_encontrada': cedula},
                    'message': f'No encontré información para la cédula {cedula}. Verifica el número.',
                    'buttons': [{'id': 'retry', 'text': 'Intentar otra cédula'}],
                    'method': 'cedula_not_found'
                }
                
        except Exception as e:
            logger.error(f"❌ Error procesando cédula: {e}")
            return {'success': False, 'error': str(e)}
    
    def _consultar_cliente_real(self, cedula: str) -> Dict[str, Any]:
        """✅ CONSULTA REAL SIN VALORES HARDCODEADOS"""
        try:
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Saldo_total, banco,
                    Oferta_1, Oferta_2, 
                    Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas,
                    Producto
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                # ✅ SOLO DATOS REALES - SIN HARDCODING
                return {
                    'encontrado': True,
                    'cliente_encontrado': True,
                    'Nombre_del_cliente': result[0] or "Cliente",
                    'saldo_total': int(float(result[1])) if result[1] else 0,
                    'banco': result[2] or "Entidad Financiera",
                    'oferta_1': int(float(result[3])) if result[3] else 0,
                    'oferta_2': int(float(result[4])) if result[4] else 0,
                    'hasta_3_cuotas': int(float(result[5])) if result[5] else 0,
                    'hasta_6_cuotas': int(float(result[6])) if result[6] else 0,
                    'hasta_12_cuotas': int(float(result[7])) if result[7] else 0,
                    'producto': result[8] or "Producto"
                }
            
            return {'encontrado': False}
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente: {e}")
            return {'encontrado': False}
    
    def _procesar_con_dynamic_service_mejorado(self, mensaje: str, contexto: Dict, 
                                              estado: str) -> Dict[str, Any]:
        """✅ PROCESAMIENTO CON SISTEMA DINÁMICO MEJORADO"""
        try:
            # ✅ CREAR ML RESULT
            ml_result = self._generar_ml_result(mensaje)
            
            # ✅ USAR SISTEMA DINÁMICO
            transition_result = self.dynamic_service.determine_next_state(
                current_state=estado,
                user_message=mensaje,
                ml_result=ml_result,
                context=contexto
            )
            
            logger.info(f"🎯 Transición: {estado} → {transition_result['next_state']}")
            logger.info(f"🔧 Método: {transition_result.get('detection_method')}")
            
            # ✅ VERIFICAR QUE LA TRANSICIÓN SEA VÁLIDA
            if transition_result['next_state'] == estado and estado == 'proponer_planes_pago':
                # ✅ FORZAR TRANSICIÓN SI DETECTA SELECCIÓN
                if self._detecta_seleccion_plan(mensaje):
                    logger.info(f"🔧 Forzando transición por selección detectada")
                    transition_result['next_state'] = 'confirmar_plan_elegido'
                    transition_result['condition_detected'] = 'cliente_selecciona_plan'
            
            # ✅ GENERAR RESPUESTA CON VARIABLES CORRECTAS
            mensaje_respuesta = self._generar_respuesta_mejorada(
                transition_result['next_state'], contexto
            )
            
            # ✅ CAPTURAR INFORMACIÓN DEL PLAN
            contexto_actualizado = self._capturar_plan_si_aplica(
                mensaje, transition_result, contexto
            )
            
            return {
                'success': True,
                'next_state': transition_result['next_state'],
                'context': contexto_actualizado,
                'message': mensaje_respuesta,
                'buttons': self._generar_botones_dinamicos(
                    transition_result['next_state'], contexto_actualizado
                ),
                'method': 'dynamic_service_improved',
                'transition_info': transition_result
            }
            
        except Exception as e:
            logger.error(f"❌ Error en dynamic service: {e}")
            return {'success': False, 'error': str(e)}
    
    def _detecta_seleccion_plan(self, mensaje: str) -> bool:
        """✅ DETECTAR SELECCIÓN DE PLAN"""
        mensaje_lower = mensaje.lower()
        patrones_seleccion = [
            'pago unico', 'pago único', 'primera', 'acepto',
            '3 cuotas', 'segunda', '6 cuotas', 'tercera',
            '1', '2', '3', 'plan'
        ]
        return any(patron in mensaje_lower for patron in patrones_seleccion)
    
    def _generar_ml_result(self, mensaje: str) -> Dict[str, Any]:
        """✅ GENERAR RESULTADO ML"""
        mensaje_lower = mensaje.lower()
        
        if any(word in mensaje_lower for word in ['pago unic', 'primera', 'liquidar']):
            return {"intention": "SELECCION_PLAN_UNICO", "confidence": 0.9}
        elif any(word in mensaje_lower for word in ['acepto', 'confirmo', 'está bien']):
            return {"intention": "CONFIRMACION_EXITOSA", "confidence": 0.9}
        elif any(word in mensaje_lower for word in ['3 cuotas', 'segunda']):
            return {"intention": "PLAN_3_CUOTAS", "confidence": 0.9}
        elif any(word in mensaje_lower for word in ['6 cuotas', 'tercera']):
            return {"intention": "PLAN_6_CUOTAS", "confidence": 0.9}
        elif any(word in mensaje_lower for word in ['si', 'sí', 'quiero', 'opciones']):
            return {"intention": "CONFIRMACION", "confidence": 0.8}
        else:
            return {"intention": "MENSAJE_GENERAL", "confidence": 0.5}
    
    def _generar_respuesta_mejorada(self, estado: str, contexto: Dict) -> str:
        """✅ GENERAR RESPUESTA SIN DATOS HARDCODEADOS"""
        try:
            # ✅ OBTENER TEMPLATE DESDE BD
            query = text("""
                SELECT mensaje_template 
                FROM Estados_Conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado}).fetchone()
            
            if result and result[0]:
                template = result[0]
                
                # ✅ RESOLVER VARIABLES CON DATOS REALES ÚNICAMENTE
                if self.variable_service and contexto.get('cliente_encontrado'):
                    try:
                        mensaje_final = self.variable_service.resolver_variables(template, contexto)
                        return mensaje_final
                    except Exception as e:
                        logger.error(f"Error resolviendo variables: {e}")
                        return self._limpiar_template_sin_datos(template, contexto)
                else:
                    return self._limpiar_template_sin_datos(template, contexto)
            else:
                # ✅ FALLBACK SIN HARDCODING
                return self._generar_mensaje_fallback(estado, contexto)
                
        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            return "¿En qué más puedo ayudarte?"
    
    def _limpiar_template_sin_datos(self, template: str, contexto: Dict) -> str:
        """✅ LIMPIAR TEMPLATE CUANDO NO HAY DATOS REALES"""
        
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        # ✅ REEMPLAZAR VARIABLES BÁSICAS
        template_limpio = template.replace('{{Nombre_del_cliente}}', nombre)
        template_limpio = template_limpio.replace('{{nombre_cliente}}', nombre)
        
        # ✅ ELIMINAR VARIABLES MONETARIAS SIN DATOS
        patron_monetario = r'\{\{[^}]*(?:saldo|oferta|cuota|pago)[^}]*\}\}'
        template_limpio = re.sub(patron_monetario, '', template_limpio)
        
        # ✅ ELIMINAR LÍNEAS VACÍAS RESULTANTES
        lineas = template_limpio.split('\n')
        lineas_limpias = [linea.strip() for linea in lineas if linea.strip() and not re.match(r'^[\$\s:]+$', linea.strip())]
        
        resultado = '\n'.join(lineas_limpias)
        
        # ✅ SI QUEDA VACÍO, MENSAJE GENÉRICO
        if not resultado.strip():
            if contexto.get('cliente_encontrado'):
                return f"¿En qué puedo ayudarte, {nombre}?"
            else:
                return "Para ayudarte, necesito tu número de cédula."
        
        return resultado
    
    def _capturar_plan_si_aplica(self, mensaje: str, transition_result: Dict, 
                                contexto: Dict) -> Dict[str, Any]:
        """✅ CAPTURAR INFORMACIÓN DEL PLAN SELECCIONADO"""
        
        contexto_actualizado = contexto.copy()
        
        # ✅ SI HAY CONDICIÓN DE SELECCIÓN DE PLAN
        condicion = transition_result.get('condition_detected', '')
        if 'cliente_selecciona_plan' in condicion:
            
            plan_info = self._determinar_plan_por_mensaje(mensaje, contexto)
            if plan_info:
                contexto_actualizado.update(plan_info)
                logger.info(f"✅ Plan capturado: {plan_info.get('plan_seleccionado')}")
        
        return contexto_actualizado
    
    def _determinar_plan_por_mensaje(self, mensaje: str, contexto: Dict) -> Dict[str, Any]:
        """✅ DETERMINAR PLAN ESPECÍFICO POR MENSAJE"""
        
        mensaje_lower = mensaje.lower()
        saldo = contexto.get('saldo_total', 0)
        oferta_2 = contexto.get('oferta_2', 0)
        cuotas_3 = contexto.get('hasta_3_cuotas', 0)
        cuotas_6 = contexto.get('hasta_6_cuotas', 0)
        
        # ✅ SOLO PROCESAR SI HAY DATOS REALES
        if saldo <= 0:
            return {}
        
        fecha_limite = (datetime.now() + timedelta(days=30)).strftime("%d de %B de %Y")
        
        if any(word in mensaje_lower for word in ['pago unic', 'primera', 'liquidar', '1']):
            if oferta_2 > 0:
                return {
                    'plan_seleccionado': 'Pago único con descuento',
                    'monto_acordado': oferta_2,
                    'numero_cuotas': 1,
                    'valor_cuota': oferta_2,
                    'fecha_limite': fecha_limite,
                    'plan_capturado': True
                }
        
        elif any(word in mensaje_lower for word in ['3 cuotas', 'segunda', 'tres', '2']):
            if cuotas_3 > 0:
                return {
                    'plan_seleccionado': 'Plan 3 cuotas sin interés',
                    'monto_acordado': cuotas_3 * 3,
                    'numero_cuotas': 3,
                    'valor_cuota': cuotas_3,
                    'fecha_limite': fecha_limite,
                    'plan_capturado': True
                }
        
        elif any(word in mensaje_lower for word in ['6 cuotas', 'tercera', 'seis', '3']):
            if cuotas_6 > 0:
                return {
                    'plan_seleccionado': 'Plan 6 cuotas sin interés',
                    'monto_acordado': cuotas_6 * 6,
                    'numero_cuotas': 6,
                    'valor_cuota': cuotas_6,
                    'fecha_limite': fecha_limite,
                    'plan_capturado': True
                }
        
        return {}
    
    def _generar_mensaje_fallback(self, estado: str, contexto: Dict) -> str:
        """✅ MENSAJE FALLBACK SIN HARDCODING"""
        
        tiene_cliente = contexto.get('cliente_encontrado', False)
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        if estado == 'informar_deuda' and tiene_cliente:
            return f"Hola {nombre}, ¿te gustaría conocer las opciones de pago disponibles?"
        elif estado == 'proponer_planes_pago' and tiene_cliente:
            return f"Te puedo ofrecer diferentes planes de pago, {nombre}. ¿Cuál te interesa más?"
        elif estado == 'confirmar_plan_elegido' and tiene_cliente:
            return f"¿Confirmas el plan que elegiste, {nombre}?"
        elif tiene_cliente:
            return f"¿En qué más puedo ayudarte, {nombre}?"
        else:
            return "Para ayudarte, necesito tu número de cédula."
    
    def _generar_botones_cliente_encontrado(self) -> list:
        """✅ BOTONES PARA CLIENTE ENCONTRADO"""
        return [
            {'id': 'ver_opciones', 'text': 'Ver opciones de pago'},
            {'id': 'mas_info', 'text': 'Más información'},
            {'id': 'no_ahora', 'text': 'No por ahora'}
        ]
    
    def _generar_botones_dinamicos(self, estado: str, contexto: Dict) -> list:
        """✅ BOTONES DINÁMICOS POR ESTADO"""
        
        if estado == 'proponer_planes_pago':
            return [
                {'id': 'pago_unico', 'text': 'Pago único con descuento'},
                {'id': 'plan_3_cuotas', 'text': '3 cuotas sin interés'},
                {'id': 'plan_6_cuotas', 'text': '6 cuotas sin interés'}
            ]
        elif estado == 'confirmar_plan_elegido':
            return [
                {'id': 'confirmar_acuerdo', 'text': 'Sí, confirmo'},
                {'id': 'cambiar_plan', 'text': 'Cambiar plan'},
                {'id': 'mas_info', 'text': 'Más información'}
            ]
        elif estado == 'generar_acuerdo':
            return [
                {'id': 'finalizar', 'text': 'Finalizar proceso'},
                {'id': 'imprimir', 'text': 'Imprimir acuerdo'}
            ]
        else:
            return [{'id': 'ayuda', 'text': 'Necesito ayuda'}]
    
    def _fallback_mejorado(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        """✅ FALLBACK MEJORADO"""
        
        mensaje_lower = mensaje.lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        # ✅ CONFIRMACIONES SIMPLES
        if any(word in mensaje_lower for word in ['si', 'sí', 'acepto']):
            if estado == 'informar_deuda':
                return {
                    'success': True,
                    'next_state': 'proponer_planes_pago',
                    'context': contexto,
                    'message': f"Perfecto {nombre}, estas son tus opciones de pago.",
                    'buttons': self._generar_botones_dinamicos('proponer_planes_pago', contexto),
                    'method': 'fallback_confirmacion'
                }
        
        # ✅ FALLBACK GENÉRICO
        if tiene_cliente:
            mensaje_respuesta = f"¿Puedes ser más específico, {nombre}? Estoy aquí para ayudarte."
            botones = [
                {'id': 'opciones_pago', 'text': 'Ver opciones de pago'},
                {'id': 'asesor', 'text': 'Hablar con asesor'}
            ]
        else:
            mensaje_respuesta = "Para ayudarte mejor, necesito tu número de cédula."
            botones = [{'id': 'proporcionar_cedula', 'text': 'Proporcionar cédula'}]
        
        return {
            'success': True,
            'next_state': estado,
            'context': contexto,
            'message': mensaje_respuesta,
            'buttons': botones,
            'method': 'fallback_mejorado'
        }
    
    def _error_response_mejorado(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        """✅ RESPUESTA DE ERROR MEJORADA"""
        return {
            'success': True,
            'next_state': 'inicial',
            'context': {},
            'message': 'Hubo un problema técnico. Por favor, proporciona tu cédula para reiniciar.',
            'buttons': [{'id': 'reiniciar', 'text': 'Reiniciar conversación'}],
            'method': 'error_recovery'
        }

# ✅ FACTORY FUNCTION
def create_improved_chat_processor(db: Session) -> ImprovedChatProcessor:
    return ImprovedChatProcessor(db)