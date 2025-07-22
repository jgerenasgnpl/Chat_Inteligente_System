# app/services/improved_chat_processor.py - VERSIÓN OPTIMIZADA CON TUS SERVICIOS

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ImprovedChatProcessor:
    """
    ✅ PROCESADOR OPTIMIZADO QUE APROVECHA TUS SERVICIOS EXISTENTES
    - Integración completa con dynamic_transition_service
    - Uso inteligente del openai_service (con enhance_response)
    - Aprovecha variable_service corregido
    """
    
    def __init__(self, db: Session):
        self.db = db
        # ✅ SERVICIOS EXISTENTES
        self.dynamic_service = self._init_dynamic_service()
        self.variable_service = self._init_variable_service()
        # ✅ NUEVO: Integrar OpenAI service para mejoras
        self.openai_service = self._init_openai_service()
        logger.info("✅ ImprovedChatProcessor optimizado inicializado")
    
    def _init_dynamic_service(self):
        """✅ INICIALIZAR TU SERVICIO DINÁMICO EXISTENTE"""
        try:
            from app.services.dynamic_transition_service import create_dynamic_transition_service
            service = create_dynamic_transition_service(self.db)
            logger.info("✅ Dynamic transition service inicializado")
            return service
        except Exception as e:
            logger.error(f"❌ Error inicializando dynamic service: {e}")
            return None
    
    def _init_variable_service(self):
        """✅ INICIALIZAR TU SERVICIO DE VARIABLES EXISTENTE"""
        try:
            from app.services.variable_service import crear_variable_service
            service = crear_variable_service(self.db)
            logger.info("✅ Variable service inicializado")
            return service
        except Exception as e:
            logger.error(f"❌ Error inicializando variable service: {e}")
            return None
    
    def _init_openai_service(self):
        """✅ NUEVO: Inicializar tu OpenAI service existente"""
        try:
            from app.services.openai_service import openai_cobranza_service
            if openai_cobranza_service.disponible:
                logger.info("✅ OpenAI service disponible para mejoras")
                return openai_cobranza_service
            else:
                logger.info("⚠️ OpenAI service no disponible")
                return None
        except Exception as e:
            logger.error(f"❌ Error inicializando OpenAI service: {e}")
            return None

    def process_message_improved(self, mensaje: str, contexto: Dict[str, Any], 
                                estado_actual: str) -> Dict[str, Any]:
        """✅ PROCESAMIENTO OPTIMIZADO CON TUS SERVICIOS EXISTENTES"""
        
        try:
            logger.info(f"🔄 [IMPROVED+OPTIMIZED] Procesando: '{mensaje}' en '{estado_actual}'")
            
            # 1. ✅ DETECCIÓN DE CÉDULA (MÁXIMA PRIORIDAD)
            cedula = self._detectar_cedula_robusta(mensaje)
            if cedula:
                resultado = self._procesar_cedula_mejorada(cedula, contexto)
                return self._estandarizar_respuesta(resultado)
            
            # 2. ✅ USAR TU SISTEMA DINÁMICO EXISTENTE (OPTIMIZADO)
            if self.dynamic_service:
                resultado = self._procesar_con_dynamic_service_optimizado(
                    mensaje, contexto, estado_actual
                )
                if resultado.get('success'):
                    return self._estandarizar_respuesta(resultado)
            
            # 3. ✅ FALLBACK INTELIGENTE
            resultado = self._fallback_mejorado(mensaje, contexto, estado_actual)
            return self._estandarizar_respuesta(resultado)
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento optimizado: {e}")
            resultado = self._error_response_mejorado(mensaje, contexto, estado_actual)
            return self._estandarizar_respuesta(resultado)
    
    def _procesar_con_dynamic_service_optimizado(self, mensaje: str, contexto: Dict, 
                                               estado: str) -> Dict[str, Any]:
        """✅ APROVECHA COMPLETAMENTE TU SISTEMA DINÁMICO EXISTENTE"""
        try:
            # ✅ CREAR ML RESULT MEJORADO
            ml_result = self._generar_ml_result_inteligente(mensaje)
            
            # ✅ USAR TU SISTEMA DINÁMICO COMPLETO
            transition_result = self.dynamic_service.determine_next_state(
                current_state=estado,
                user_message=mensaje,
                ml_result=ml_result,
                context=contexto
            )
            
            logger.info(f"🎯 Transición dinámica: {estado} → {transition_result['next_state']}")
            logger.info(f"🔧 Método dinámico: {transition_result.get('detection_method')}")
            
            # ✅ LOGGING AUTOMÁTICO (aprovecha tu función existente)
            try:
                conversation_id = contexto.get('conversation_id', 1)
                self.dynamic_service.log_decision(
                    conversation_id, estado, mensaje, ml_result, transition_result
                )
            except Exception as log_e:
                logger.warning(f"⚠️ Error en logging automático: {log_e}")
            
            # ✅ GENERAR RESPUESTA CON MEJORA OPCIONAL DE IA
            mensaje_base = self._generar_respuesta_con_variables(
                transition_result['next_state'], contexto
            )
            
            # ✅ MEJORA OPCIONAL CON TU OPENAI SERVICE
            mensaje_final = self._mejorar_respuesta_con_openai_si_aplica(
                mensaje_base, contexto, mensaje, transition_result['next_state']
            )
            
            # ✅ CAPTURAR INFORMACIÓN DEL PLAN
            contexto_actualizado = self._capturar_plan_inteligente(
                mensaje, transition_result, contexto
            )
            
            return {
                'success': True,
                'next_state': transition_result['next_state'],
                'context': contexto_actualizado,
                'message': mensaje_final,
                'buttons': self._generar_botones_dinamicos(
                    transition_result['next_state'], contexto_actualizado
                ),
                'method': 'dynamic_service_optimized',
                'transition_info': transition_result,
                'ai_enhanced': mensaje_final != mensaje_base
            }
            
        except Exception as e:
            logger.error(f"❌ Error en sistema dinámico optimizado: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generar_ml_result_inteligente(self, mensaje: str) -> Dict[str, Any]:
        """✅ ML RESULT MEJORADO QUE APROVECHA TUS MAPEOS EXISTENTES"""
        mensaje_lower = mensaje.lower().strip()
        
        # ✅ DETECCIÓN MEJORADA BASADA EN TUS MAPEOS ML
        mappings = [
            # Selecciones específicas (alta confianza)
            (['pago unic', 'pago único', 'liquidar', 'primera'], 'SELECCION_PLAN_UNICO', 0.95),
            (['3 cuotas', 'tres cuotas', 'segunda'], 'PLAN_3_CUOTAS', 0.95),
            (['6 cuotas', 'seis cuotas', 'tercera'], 'PLAN_6_CUOTAS', 0.95),
            (['12 cuotas', 'doce cuotas', 'cuarta'], 'PLAN_12_CUOTAS', 0.95),
            
            # Confirmaciones (confianza media-alta)
            (['acepto', 'confirmo', 'de acuerdo', 'está bien'], 'CONFIRMACION_EXITOSA', 0.90),
            (['si acepto', 'sí acepto', 'acepto el plan'], 'CONFIRMACION_EXITOSA', 0.95),
            
            # Consultas proceso de pago
            (['como pago', 'donde pago', 'métodos de pago'], 'CONSULTA_PROCESO_PAGO', 0.90),
            
            # Rechazos y objeciones
            (['no puedo', 'imposible', 'muy caro'], 'OBJECION', 0.85),
            (['no me interesa', 'no quiero'], 'RECHAZO', 0.90),
            
            # Números simples (confianza media)
            (['1'], 'SELECCION_PLAN_UNICO', 0.85),
            (['2'], 'PLAN_3_CUOTAS', 0.85),
            (['3'], 'PLAN_6_CUOTAS', 0.85),
            
            # Confirmaciones simples (confianza baja)
            (['si', 'sí', 'ok'], 'CONFIRMACION', 0.75),
        ]
        
        # ✅ BUSCAR COINCIDENCIA CON MAYOR CONFIANZA
        for keywords, intention, confidence in mappings:
            if any(keyword in mensaje_lower for keyword in keywords):
                return {
                    "intention": intention,
                    "confidence": confidence,
                    "method": "intelligent_mapping",
                    "matched_keywords": [kw for kw in keywords if kw in mensaje_lower]
                }
        
        # ✅ FALLBACK PARA MENSAJES GENERALES
        if len(mensaje.strip()) > 5:
            return {"intention": "MENSAJE_GENERAL", "confidence": 0.6, "method": "fallback"}
        else:
            return {"intention": "ENTRADA_SIMPLE", "confidence": 0.4, "method": "fallback"}
    
    def _generar_respuesta_con_variables(self, estado: str, contexto: Dict) -> str:
        """✅ GENERAR RESPUESTA USANDO TU VARIABLE SERVICE"""
        try:
            # ✅ OBTENER TEMPLATE DESDE BD (TU MÉTODO EXISTENTE)
            query = text("""
                SELECT mensaje_template 
                FROM Estados_Conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado}).fetchone()
            
            if result and result[0]:
                template = result[0]
                
                # ✅ USAR TU SERVICIO DE VARIABLES EXISTENTE
                if self.variable_service and contexto.get('cliente_encontrado'):
                    try:
                        mensaje_resuelto = self.variable_service.resolver_variables(template, contexto)
                        logger.info(f"✅ Variables resueltas con tu servicio existente")
                        return mensaje_resuelto
                    except Exception as e:
                        logger.error(f"Error resolviendo variables: {e}")
                        return self._limpiar_template_fallback(template, contexto)
                else:
                    return self._limpiar_template_fallback(template, contexto)
            else:
                return self._generar_mensaje_fallback(estado, contexto)
                
        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            return "¿En qué más puedo ayudarte?"
    
    def _mejorar_respuesta_con_openai_si_aplica(self, mensaje_base: str, contexto: Dict,
                                              user_message: str, estado: str) -> str:
        """✅ USAR TU OPENAI SERVICE EXISTENTE PARA MEJORAS OPCIONALES"""
        
        # ✅ VERIFICAR SI TU OPENAI SERVICE ESTÁ DISPONIBLE
        if not self.openai_service or not self.openai_service.disponible:
            return mensaje_base
        
        # ✅ USAR TU MÉTODO should_use_openai EXISTENTE
        if not self.openai_service.should_use_openai(user_message, contexto, estado):
            return mensaje_base
        
        try:
            # ✅ CREAR PROMPT ESPECÍFICO PARA TU enhance_response
            enhancement_prompt = f"""
            CONTEXTO DE MEJORA:
            Estado: {estado}
            Mensaje del cliente: {user_message}
            Cliente: {contexto.get('Nombre_del_cliente', 'Cliente')}
            Saldo: ${contexto.get('saldo_total', 0):,}
            
            RESPUESTA BASE:
            {mensaje_base}
            
            Mejora esta respuesta manteniéndola empática y profesional.
            Incluye datos específicos del cliente cuando sea relevante.
            Máximo 200 palabras.
            """
            
            # ✅ USAR TU MÉTODO enhance_response EXISTENTE
            respuesta_mejorada = self.openai_service.enhance_response(
                enhancement_prompt, contexto
            )
            
            if respuesta_mejorada and len(respuesta_mejorada) > 10:
                logger.info(f"✅ Respuesta mejorada con tu OpenAI service")
                return respuesta_mejorada
            
        except Exception as e:
            logger.error(f"❌ Error mejorando con OpenAI: {e}")
        
        return mensaje_base
    
    def _capturar_plan_inteligente(self, mensaje: str, transition_result: Dict, 
                                  contexto: Dict) -> Dict[str, Any]:
        """✅ CAPTURA DE PLAN MEJORADA"""
        
        contexto_actualizado = contexto.copy()
        
        # ✅ VERIFICAR CONDICIONES DE TU SISTEMA DINÁMICO
        condicion = transition_result.get('condition_detected', '')
        
        # ✅ MAPEO DE CONDICIONES A PLANES
        plan_mappings = {
            'cliente_selecciona_pago_unico': self._crear_plan_pago_unico,
            'cliente_selecciona_plan_3_cuotas': lambda ctx: self._crear_plan_cuotas(ctx, 3),
            'cliente_selecciona_plan_6_cuotas': lambda ctx: self._crear_plan_cuotas(ctx, 6),
            'cliente_selecciona_plan_12_cuotas': lambda ctx: self._crear_plan_cuotas(ctx, 12),
        }
        
        if condicion in plan_mappings:
            try:
                plan_info = plan_mappings[condicion](contexto)
                if plan_info:
                    contexto_actualizado.update(plan_info)
                    logger.info(f"✅ Plan inteligente capturado: {plan_info.get('plan_seleccionado')}")
            except Exception as e:
                logger.error(f"❌ Error capturando plan: {e}")
        
        return contexto_actualizado
    
    def _crear_plan_pago_unico(self, contexto: Dict) -> Dict[str, Any]:
        """✅ CREAR PLAN PAGO ÚNICO CON DATOS REALES"""
        saldo = contexto.get('saldo_total', 0)
        oferta_2 = contexto.get('oferta_2', 0)
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        if saldo <= 0:
            return {}
        
        # ✅ USAR OFERTA REAL O CALCULAR
        monto_final = oferta_2 if oferta_2 > 0 else int(saldo * 0.7)
        descuento = saldo - monto_final
        porcentaje_desc = int((descuento / saldo) * 100) if saldo > 0 else 0
        
        return {
            'plan_capturado': True,
            'plan_seleccionado': 'Pago único con descuento',
            'tipo_plan': 'pago_unico',
            'monto_acordado': monto_final,
            'numero_cuotas': 1,
            'valor_cuota': monto_final,
            'descuento_aplicado': descuento,
            'porcentaje_descuento': porcentaje_desc,
            'fecha_limite': (datetime.now() + timedelta(days=30)).strftime("%d de %B de %Y"),
            'metodo_captura': 'inteligente_dinamico'
        }
    
    def _crear_plan_cuotas(self, contexto: Dict, num_cuotas: int) -> Dict[str, Any]:
        """✅ CREAR PLAN DE CUOTAS CON DATOS REALES"""
        saldo = contexto.get('saldo_total', 0)
        
        # ✅ OBTENER VALOR DE CUOTA DESDE CONTEXTO
        campo_cuota = f'hasta_{num_cuotas}_cuotas'
        valor_cuota = contexto.get(campo_cuota, 0)
        
        if saldo <= 0:
            return {}
        
        # ✅ USAR VALOR REAL O CALCULAR
        if valor_cuota <= 0:
            # Calcular con descuento progresivo
            factor_descuento = 1.0 - (num_cuotas / 100)  # Más cuotas = menos descuento
            valor_cuota = int((saldo * factor_descuento) / num_cuotas)
        
        monto_total = valor_cuota * num_cuotas
        descuento = saldo - monto_total
        
        return {
            'plan_capturado': True,
            'plan_seleccionado': f'Plan {num_cuotas} cuotas sin interés',
            'tipo_plan': f'cuotas_{num_cuotas}',
            'monto_acordado': monto_total,
            'numero_cuotas': num_cuotas,
            'valor_cuota': valor_cuota,
            'descuento_aplicado': descuento,
            'fecha_limite': (datetime.now() + timedelta(days=30)).strftime("%d de %B de %Y"),
            'metodo_captura': 'inteligente_dinamico'
        }
    
    # ✅ MÉTODOS HEREDADOS (sin cambios significativos)
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
    
    def _procesar_cedula_mejorada(self, cedula: str, contexto: Dict) -> Dict[str, Any]:
        """✅ PROCESAMIENTO MEJORADO DE CÉDULA"""
        try:
            cliente_data = self._consultar_cliente_real(cedula)
            
            if cliente_data.get('encontrado'):
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
    
    def _estandarizar_respuesta(self, resultado: Dict[str, Any]) -> Dict[str, Any]:
        """✅ ESTANDARIZAR TODAS LAS CLAVES DE RESPUESTA"""
        respuesta_estandar = {
            'intencion': resultado.get('intention') or resultado.get('intencion', 'PROCESAMIENTO_GENERAL'),
            'confianza': resultado.get('confidence') or resultado.get('confianza', 0.0),
            'next_state': resultado.get('next_state') or resultado.get('estado_siguiente', 'inicial'),
            'contexto_actualizado': resultado.get('context') or resultado.get('contexto_actualizado', {}),
            'mensaje_respuesta': resultado.get('message') or resultado.get('mensaje_respuesta', '¿En qué puedo ayudarte?'),
            'botones': resultado.get('buttons') or resultado.get('botones', []),
            'metodo': resultado.get('method') or resultado.get('metodo', 'sistema_optimizado'),
            'usar_resultado': resultado.get('success', True),
            'transition_info': resultado.get('transition_info', {}),
            'ai_enhanced': resultado.get('ai_enhanced', False)
        }
        
        return respuesta_estandar
    
    # ✅ MÉTODOS AUXILIARES SIMPLIFICADOS
    def _generar_mensaje_cliente_encontrado(self, cliente_data: Dict) -> str:
        nombre = cliente_data.get('Nombre_del_cliente', 'Cliente')
        banco = cliente_data.get('banco', 'tu entidad financiera')
        saldo = cliente_data.get('saldo_total', 0)
        
        return f"""¡Perfecto, {nombre}! 

📋 **Información de tu cuenta:**
🏦 Entidad: {banco}
💰 Saldo actual: ${saldo:,}

¿Te gustaría conocer las opciones de pago disponibles para ti?"""

    def _generar_botones_cliente_encontrado(self) -> list:
        return [
            {'id': 'ver_opciones', 'text': 'Ver opciones de pago'},
            {'id': 'mas_info', 'text': 'Más información'},
            {'id': 'no_ahora', 'text': 'No por ahora'}
        ]
    
    def _generar_botones_dinamicos(self, estado: str, contexto: Dict) -> list:
        if estado == 'proponer_planes_pago':
            return [
                {'id': 'pago_unico', 'text': 'Pago único con descuento'},
                {'id': 'plan_3_cuotas', 'text': '3 cuotas sin interés'},
                {'id': 'plan_6_cuotas', 'text': '6 cuotas sin interés'}
            ]
        elif estado == 'confirmar_plan_elegido':
            return [
                {'id': 'confirmar_acuerdo', 'text': 'Sí, confirmo'},
                {'id': 'cambiar_plan', 'text': 'Cambiar plan'}
            ]
        elif estado == 'generar_acuerdo':
            return [
                {'id': 'finalizar', 'text': 'Finalizar proceso'},
                {'id': 'imprimir', 'text': 'Imprimir acuerdo'}
            ]
        else:
            return [{'id': 'ayuda', 'text': 'Necesito ayuda'}]
    
    def _limpiar_template_fallback(self, template: str, contexto: Dict) -> str:
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        template_limpio = template.replace('{{Nombre_del_cliente}}', nombre)
        patron_monetario = r'\{\{[^}]*(?:saldo|oferta|cuota|pago)[^}]*\}\}'
        template_limpio = re.sub(patron_monetario, '', template_limpio)
        
        if not template_limpio.strip():
            return f"¿En qué puedo ayudarte, {nombre}?" if nombre != 'Cliente' else "Para ayudarte, necesito tu cédula."
        
        return template_limpio
    
    def _generar_mensaje_fallback(self, estado: str, contexto: Dict) -> str:
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        if contexto.get('cliente_encontrado'):
            return f"¿En qué más puedo ayudarte, {nombre}?"
        else:
            return "Para ayudarte, necesito tu número de cédula."
    
    def _fallback_mejorado(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        return {
            'success': True,
            'next_state': estado,
            'context': contexto,
            'message': self._generar_mensaje_fallback(estado, contexto),
            'buttons': [{'id': 'ayuda', 'text': 'Necesito ayuda'}],
            'method': 'fallback_optimizado'
        }
    
    def _error_response_mejorado(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        return {
            'success': True,
            'next_state': 'inicial',
            'context': {},
            'message': 'Hubo un problema técnico. Por favor, proporciona tu cédula para reiniciar.',
            'buttons': [{'id': 'reiniciar', 'text': 'Reiniciar conversación'}],
            'method': 'error_recovery'
        }

# ✅ FACTORY FUNCTIONS OPTIMIZADAS
def create_improved_chat_processor(db: Session) -> ImprovedChatProcessor:
    """Factory optimizada que aprovecha tus servicios existentes"""
    try:
        processor = ImprovedChatProcessor(db)
        logger.info("✅ ImprovedChatProcessor optimizado creado exitosamente")
        return processor
    except Exception as e:
        logger.error(f"❌ Error creando ImprovedChatProcessor optimizado: {e}")
        raise

def create_compatible_chat_processor(db: Session) -> ImprovedChatProcessor:
    """Alias para compatibilidad"""
    return create_improved_chat_processor(db)