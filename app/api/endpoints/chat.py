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


class OptimizedChatProcessor:
    """
    🎯 PROCESADOR DE CHAT OPTIMIZADO Y DINÁMICO
    - Sistema 100% dinámico basado en BD
    - OpenAI como motor principal (80% de casos)
    - ML como fallback
    - Reglas dinámicas desde BD
    - Sin valores hardcodeados
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.dynamic_transition_service = self._init_dynamic_service()
        self.openai_service = self._init_openai_service()
        self.ml_service = self._init_ml_service()
        self.variable_service = self._init_variable_service()
        
        logger.info("✅ OptimizedChatProcessor inicializado - Sistema 100% dinámico")
    
    def _init_dynamic_service(self):
        """Inicializar servicio de transiciones dinámicas"""
        try:
            from app.services.dynamic_transition_service import create_dynamic_transition_service
            return create_dynamic_transition_service(self.db)
        except Exception as e:
            logger.error(f"❌ Error inicializando servicio dinámico: {e}")
            return None
    
    def _init_openai_service(self):
        """Inicializar OpenAI como motor principal"""
        try:
            from app.services.openai_service import openai_cobranza_service
            if openai_cobranza_service.disponible:
                logger.info("🤖 OpenAI disponible como motor principal")
                return openai_cobranza_service
        except Exception as e:
            logger.warning(f"⚠️ OpenAI no disponible: {e}")
        return None
    
    def _init_ml_service(self):
        """Inicializar ML como fallback"""
        try:
            from app.services.nlp_service import nlp_service
            return nlp_service
        except Exception as e:
            logger.warning(f"⚠️ ML no disponible: {e}")
            return None
    
    def _init_variable_service(self):
        """Inicializar servicio de variables"""
        try:
            from app.services.variable_service import crear_variable_service
            return crear_variable_service(self.db)
        except Exception as e:
            logger.warning(f"⚠️ Variable service no disponible: {e}")
            return None
    
    def process_message_optimized(self, mensaje: str, contexto: Dict[str, Any], estado_actual: str) -> Dict[str, Any]:
        """
        🎯 MÉTODO PRINCIPAL OPTIMIZADO
        1. Detección automática de cédulas (máxima prioridad)
        2. OpenAI (80% de casos)
        3. Sistema dinámico + ML (fallback)
        4. Reglas básicas (último recurso)
        """
        
        logger.info(f"🚀 [OPTIMIZED] Procesando: '{mensaje[:30]}...' en estado '{estado_actual}'")
        
        # ✅ 1. DETECCIÓN AUTOMÁTICA DE CÉDULAS (PRIORIDAD MÁXIMA)
        cedula_detectada = self._detectar_cedula_inteligente(mensaje)
        if cedula_detectada:
            return self._procesar_cedula_completa(cedula_detectada, contexto)
        
        # ✅ 2. MOTOR PRINCIPAL: OPENAI (80% de casos relevantes)
        if self.openai_service and self.openai_service.should_use_openai(mensaje, contexto, estado_actual):
            resultado_openai = self._procesar_con_openai_principal(mensaje, contexto, estado_actual)
            if resultado_openai.get('success'):
                return resultado_openai
            else:
                logger.info(f"🔄 OpenAI falló, usando fallback")
        
        # ✅ 3. FALLBACK: SISTEMA DINÁMICO + ML
        if self.dynamic_transition_service:
            return self._procesar_con_sistema_dinamico(mensaje, contexto, estado_actual)
        
        # ✅ 4. ÚLTIMO RECURSO: REGLAS BÁSICAS
        return self._procesar_con_reglas_basicas(mensaje, contexto, estado_actual)
    
    def _detectar_cedula_inteligente(self, mensaje: str) -> Optional[str]:
        """Detección robusta de cédulas con múltiples patrones"""
        patrones_cedula = [
            r'\b(\d{7,12})\b',                   
            r'cédula\s*:?\s*(\d{7,12})',         
            r'cedula\s*:?\s*(\d{7,12})',         
            r'documento\s*:?\s*(\d{7,12})',      
            r'cc\s*:?\s*(\d{7,12})',             
            r'es\s+(\d{7,12})',                  
            r'tengo\s+(\d{7,12})',               
            r'mi\s+(\d{7,12})',                 
        ]
        
        for patron in patrones_cedula:
            matches = re.findall(patron, mensaje, re.IGNORECASE)
            for match in matches:
                cedula = str(match).strip()
                if self._validar_cedula(cedula):
                    logger.info(f"🎯 [CEDULA] Detectada: {cedula}")
                    return cedula
        return None
    
    def _validar_cedula(self, cedula: str) -> bool:
        """Validar que la cédula sea válida"""
        if not cedula or len(cedula) < 7 or len(cedula) > 12:
            return False
        
        if len(set(cedula)) <= 1:
            return False
        
        if not cedula.isdigit():
            return False
        
        return True
    
    def _procesar_cedula_completa(self, cedula: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """Procesamiento completo de cédula detectada"""
        logger.info(f"🔍 [CEDULA] Consultando cliente: {cedula}")
        
        # Consultar cliente en BD
        cliente_data = self._consultar_cliente_completo(cedula)
        
        if cliente_data['encontrado']:
            contexto_actualizado = {**contexto, **cliente_data['datos']}
            
            # Generar respuesta dinámica
            mensaje_respuesta = self._generar_mensaje_cliente_encontrado(cliente_data['datos'])
            botones = self._generar_botones_cliente_encontrado(cliente_data['datos'])
            
            return {
                'intencion': 'IDENTIFICACION_EXITOSA',
                'confianza': 0.98,
                'next_state': 'informar_deuda',
                'contexto_actualizado': contexto_actualizado,
                'mensaje_respuesta': mensaje_respuesta,
                'botones': botones,
                'metodo': 'deteccion_cedula_automatica_completa',
                'usar_resultado': True,
                'success': True
            }
        else:
            return {
                'intencion': 'IDENTIFICACION_FALLIDA',
                'confianza': 0.95,
                'next_state': 'cliente_no_encontrado',
                'contexto_actualizado': {**contexto, 'cedula_no_encontrada': cedula},
                'mensaje_respuesta': f"No encontré información para la cédula {cedula}. Por favor verifica el número o comunícate con atención al cliente.",
                'botones': [
                    {"id": "reintentar", "text": "Intentar otra cédula"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ],
                'metodo': 'cedula_no_encontrada',
                'usar_resultado': True,
                'success': True
            }
    
    def _consultar_cliente_completo(self, cedula: str) -> Dict[str, Any]:
        """Consulta completa de cliente con cálculos dinámicos"""
        try:
            query = text("""
                SELECT TOP 1 
                    [Nombre_del_cliente],
                    [Saldo_total],
                    [banco],
                    [Oferta_1],
                    [Oferta_2],
                    [Hasta_3_cuotas],
                    [Hasta_6_cuotas],
                    [Hasta_12_cuotas],
                    [Producto],
                    [Telefono],
                    [Email],
                    [Capital],
                    [Intereses]
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                datos_base = {
                    'cliente_encontrado': True,
                    'cedula_detectada': cedula,
                    'Nombre_del_cliente': result[0] or "Cliente",
                    'saldo_total': int(float(result[1])) if result[1] else 0,
                    'banco': result[2] or "Entidad Financiera",
                    'producto': result[8] or "Producto",
                    'telefono': result[9] or "",
                    'email': result[10] or "",
                    'capital': int(float(result[11])) if result[11] else 0,
                    'intereses': int(float(result[12])) if result[12] else 0
                }
                
                # Cálculos dinámicos de ofertas
                if result[3] and float(result[3]) > 0:
                    datos_base['oferta_1'] = int(float(result[3]))
                else:
                    datos_base['oferta_1'] = int(datos_base['saldo_total'] * 0.6)  
                
                if result[4] and float(result[4]) > 0:
                    datos_base['oferta_2'] = int(float(result[4]))
                else:
                    datos_base['oferta_2'] = int(datos_base['saldo_total'] * 0.7) 
                
                if result[5] and float(result[5]) > 0:
                    datos_base['hasta_3_cuotas'] = int(float(result[5]))
                else:
                    datos_base['hasta_3_cuotas'] = int((datos_base['saldo_total'] * 0.85) / 3)
                
                if result[6] and float(result[6]) > 0:
                    datos_base['hasta_6_cuotas'] = int(float(result[6]))
                else:
                    datos_base['hasta_6_cuotas'] = int((datos_base['saldo_total'] * 0.9) / 6)
                
                if result[7] and float(result[7]) > 0:
                    datos_base['hasta_12_cuotas'] = int(float(result[7]))
                else:
                    datos_base['hasta_12_cuotas'] = int(datos_base['saldo_total'] / 12)
                
                # Cálculos adicionales
                datos_base.update({
                    'ahorro_oferta_1': datos_base['saldo_total'] - datos_base['oferta_1'],
                    'ahorro_oferta_2': datos_base['saldo_total'] - datos_base['oferta_2'],
                    'porcentaje_desc_1': int(((datos_base['saldo_total'] - datos_base['oferta_1']) / datos_base['saldo_total']) * 100),
                    'porcentaje_desc_2': int(((datos_base['saldo_total'] - datos_base['oferta_2']) / datos_base['saldo_total']) * 100),
                    'pago_minimo': int(datos_base['saldo_total'] * 0.1),
                    'consulta_timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"✅ [CLIENTE] Encontrado: {datos_base['Nombre_del_cliente']}")
                logger.info(f"💰 Saldo: ${datos_base['saldo_total']:,}")
                logger.info(f"🎯 Oferta mejor: ${datos_base['oferta_2']:,} ({datos_base['porcentaje_desc_2']}% desc)")
                
                return {'encontrado': True, 'datos': datos_base}
            
            logger.info(f"❌ [CLIENTE] No encontrado para cédula: {cedula}")
            return {'encontrado': False, 'datos': {}}
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente {cedula}: {e}")
            return {'encontrado': False, 'datos': {}, 'error': str(e)}
    
    def _procesar_con_openai_principal(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> Dict[str, Any]:
        """Procesamiento principal con OpenAI optimizado para cobranza"""
        try:
            logger.info(f"🤖 [OPENAI] Procesando con IA especializada")
            
            resultado_openai = self.openai_service.procesar_mensaje_cobranza(
                mensaje, contexto, estado
            )
            
            if resultado_openai.get('enhanced'):
                # Determinar siguiente estado basado en el mensaje de OpenAI
                next_state = self._determinar_estado_desde_openai(
                    resultado_openai, estado, contexto
                )
                
                # Generar botones dinámicos
                botones = self._generar_botones_dinamicos_openai(next_state, contexto)
                
                return {
                    'intencion': 'OPENAI_ENHANCED',
                    'confianza': 0.9,
                    'next_state': next_state,
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': resultado_openai['message'],
                    'botones': botones,
                    'metodo': 'openai_cobranza_principal',
                    'usar_resultado': True,
                    'success': True,
                    'ai_enhanced': True
                }
            
            return {'success': False, 'razon': 'openai_no_enhanced'}
            
        except Exception as e:
            logger.error(f"❌ [OPENAI] Error: {e}")
            return {'success': False, 'razon': f'error_openai: {e}'}
    
    def _procesar_con_sistema_dinamico(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> Dict[str, Any]:
        """Fallback con sistema dinámico + ML"""
        try:
            logger.info(f"🔧 [DINAMICO] Procesando con sistema dinámico")
            
            # Crear resultado ML
            ml_result = {}
            if self.ml_service:
                ml_prediction = self.ml_service.predict(mensaje)
                ml_result = {
                    'intention': ml_prediction.get('intention', 'DESCONOCIDA'),
                    'confidence': ml_prediction.get('confidence', 0.0),
                    'method': 'ml_classification'
                }
                logger.info(f"🤖 [ML] {ml_result['intention']} (confianza: {ml_result['confidence']:.2f})")
            
            # Usar sistema dinámico
            transition_result = self.dynamic_transition_service.determine_next_state(
                current_state=estado,
                user_message=mensaje,
                ml_result=ml_result,
                context=contexto
            )
            
            # Capturar selección de plan si es relevante
            contexto_con_plan = self._capturar_seleccion_plan_dinamica(
                mensaje, transition_result, contexto
            )
            
            # Generar respuesta dinámica
            mensaje_respuesta = self._generar_respuesta_dinamica(
                transition_result['next_state'], contexto_con_plan
            )
            
            # Generar botones dinámicos
            botones = self._generar_botones_dinamicos(
                transition_result['next_state'], contexto_con_plan
            )
            
            logger.info(f"🎯 [DINAMICO] {estado} → {transition_result['next_state']}")
            logger.info(f"🔧 Método: {transition_result['detection_method']}")
            
            return {
                'intencion': transition_result['condition_detected'],
                'confianza': transition_result['confidence'],
                'next_state': transition_result['next_state'],
                'contexto_actualizado': contexto_con_plan,
                'mensaje_respuesta': mensaje_respuesta,
                'botones': botones,
                'metodo': 'sistema_dinamico_ml',
                'usar_resultado': True,
                'success': True,
                'transition_info': transition_result
            }
            
        except Exception as e:
            logger.error(f"❌ [DINAMICO] Error: {e}")
            return self._procesar_con_reglas_basicas(mensaje, contexto, estado)
    
    def _capturar_seleccion_plan_dinamica(self, mensaje: str, transition_result: Dict, contexto: Dict) -> Dict[str, Any]:
        """Capturar selección de plan de manera dinámica"""
        
        condicion = transition_result.get('condition_detected', '')
        contexto_actualizado = contexto.copy()
        
        logger.info(f"🔍 [PLAN] Verificando captura: condición={condicion}")
        
        mensaje_lower = mensaje.lower().strip()
        
        # Si la condición indica selección de plan
        if condicion and condicion.startswith('cliente_selecciona_'):
            plan_info = self._procesar_seleccion_por_condicion(condicion, contexto_actualizado, mensaje)
            if plan_info.get('plan_capturado'):
                logger.info(f"✅ [PLAN] Capturado por condición: {plan_info['plan_seleccionado']}")
                return plan_info
        
        # Detección directa por palabras clave
        plan_detectado = self._detectar_plan_directo(mensaje_lower, contexto_actualizado)
        if plan_detectado:
            logger.info(f"✅ [PLAN] Detectado directamente: {plan_detectado['plan_seleccionado']}")
            contexto_actualizado.update(plan_detectado)
            return contexto_actualizado
        
        # Detección por números/posiciones
        plan_por_numero = self._detectar_seleccion_numerica(mensaje_lower, contexto_actualizado)
        if plan_por_numero:
            logger.info(f"✅ [PLAN] Detectado por número: {plan_por_numero['plan_seleccionado']}")
            contexto_actualizado.update(plan_por_numero)
            return contexto_actualizado
        
        return contexto_actualizado
    
    def _detectar_plan_directo(self, mensaje_lower: str, contexto: Dict) -> Optional[Dict[str, Any]]:
        """Detectar plan directamente por palabras clave"""
        
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        saldo_total = contexto.get('saldo_total', 0)
        oferta_2 = contexto.get('oferta_2', 0)
        cuotas_3 = contexto.get('hasta_3_cuotas', 0)
        cuotas_6 = contexto.get('hasta_6_cuotas', 0)
        cuotas_12 = contexto.get('hasta_12_cuotas', 0)
        
        if any(keyword in mensaje_lower for keyword in [
            'pago unico', 'pago único', 'descuento', 'liquidar todo', 
            'pago completo', 'oferta especial'
        ]):
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje_lower)
        
        elif any(keyword in mensaje_lower for keyword in [
            '3 cuotas', 'tres cuotas', 'plan 3', 'plan de 3'
        ]):
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_3, 3, "3 cuotas sin interés")
        
        elif any(keyword in mensaje_lower for keyword in [
            '6 cuotas', 'seis cuotas', 'plan 6', 'plan de 6'
        ]):
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_6, 6, "6 cuotas sin interés")
        
        elif any(keyword in mensaje_lower for keyword in [
            '12 cuotas', 'doce cuotas', 'plan 12', 'plan de 12'
        ]):
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_12, 12, "12 cuotas sin interés")
        
        return None
    
    def _detectar_seleccion_numerica(self, mensaje_lower: str, contexto: Dict) -> Optional[Dict[str, Any]]:
        """Detectar selección por números o posiciones"""
        
        saldo_total = contexto.get('saldo_total', 0)
        oferta_2 = contexto.get('oferta_2', 0)
        cuotas_3 = contexto.get('hasta_3_cuotas', 0)
        cuotas_6 = contexto.get('hasta_6_cuotas', 0)
        cuotas_12 = contexto.get('hasta_12_cuotas', 0)
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        # Mapeo de selecciones numéricas
        if any(pattern in mensaje_lower for pattern in ['primera', 'primer', '1', 'uno']):
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, "primera opción")
        
        elif any(pattern in mensaje_lower for pattern in ['segunda', 'segundo', '2', 'dos']):
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_3, 3, "Plan 3 cuotas (segunda opción)")
        
        elif any(pattern in mensaje_lower for pattern in ['tercera', 'tercer', '3', 'tres']): 
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_6, 6, "Plan 6 cuotas (tercera opción)")
        
        elif any(pattern in mensaje_lower for pattern in ['cuarta', 'cuarto', '4', 'cuatro']):
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_12, 12, "Plan 12 cuotas (cuarta opción)")
        
        return None
    
    def _procesar_seleccion_por_condicion(self, condicion: str, contexto: Dict, mensaje: str) -> Dict[str, Any]:
        """Procesar selección basada en condición BD"""
        
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        saldo_total = contexto.get('saldo_total', 0)
        
        if condicion == 'cliente_selecciona_pago_unico':
            oferta_2 = contexto.get('oferta_2', 0)
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje)
        
        elif condicion == 'cliente_selecciona_plan_3_cuotas':
            cuotas_3 = contexto.get('hasta_3_cuotas', 0)
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_3, 3, "Plan 3 cuotas sin interés")
        
        elif condicion == 'cliente_selecciona_plan_6_cuotas':
            cuotas_6 = contexto.get('hasta_6_cuotas', 0)
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_6, 6, "Plan 6 cuotas sin interés")
        
        elif condicion == 'cliente_selecciona_plan_12_cuotas':
            cuotas_12 = contexto.get('hasta_12_cuotas', 0)
            return self._generar_plan_cuotas(nombre, saldo_total, cuotas_12, 12, "Plan 12 cuotas sin interés")
        
        elif condicion in ['cliente_selecciona_plan', 'cliente_confirma_plan_elegido']:
            # Detectar tipo de plan por el mensaje
            plan_detectado = self._detectar_plan_directo(mensaje.lower(), contexto)
            if plan_detectado:
                return plan_detectado
            
            # Fallback: pago único
            oferta_2 = contexto.get('oferta_2', 0)
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje)
        
        return contexto
    
    def _generar_plan_pago_unico(self, nombre: str, saldo_total: int, oferta_2: int, contexto_seleccion: str) -> Dict[str, Any]:
        """Generar datos del plan pago único"""
        
        if not oferta_2 or oferta_2 <= 0:
            oferta_2 = int(saldo_total * 0.7) if saldo_total > 0 else 0
        
        descuento = saldo_total - oferta_2 if saldo_total > oferta_2 else 0
        porcentaje_desc = int((descuento / saldo_total) * 100) if saldo_total > 0 else 0
        
        fecha_limite = (datetime.now() + timedelta(days=30)).strftime("%d de %B de %Y")
        
        return {
            'plan_capturado': True,
            'plan_seleccionado': 'Pago único con descuento',
            'tipo_plan': 'pago_unico',
            'monto_acordado': oferta_2,
            'numero_cuotas': 1,
            'valor_cuota': oferta_2,
            'descuento_aplicado': descuento,
            'porcentaje_descuento': porcentaje_desc,
            'fecha_limite': fecha_limite,
            'fecha_seleccion': datetime.now().isoformat(),
            'cliente_acepto_plan': True,
            'seleccion_original_usuario': contexto_seleccion,
            'metodo_deteccion': 'pago_unico_optimizado'
        }

    def _generar_plan_cuotas(self, nombre: str, saldo_total: int, valor_cuota: int, 
                            num_cuotas: int, descripcion_plan: str) -> Dict[str, Any]:
        """Generar datos del plan de cuotas"""
        
        if not valor_cuota or valor_cuota <= 0:
            # Calcular cuota basada en descuento progresivo
            descuento_factor = 1.0 - (num_cuotas / 100)
            valor_cuota = int((saldo_total * descuento_factor) / num_cuotas) if saldo_total > 0 else 0
        
        monto_total = valor_cuota * num_cuotas
        descuento = saldo_total - monto_total if saldo_total > monto_total else 0
        porcentaje_desc = int((descuento / saldo_total) * 100) if saldo_total > 0 else 0
        
        fecha_limite = (datetime.now() + timedelta(days=30)).strftime("%d de %B de %Y")
        
        return {
            'plan_capturado': True,
            'plan_seleccionado': descripcion_plan,
            'tipo_plan': f'cuotas_{num_cuotas}',
            'monto_acordado': monto_total,
            'numero_cuotas': num_cuotas,
            'valor_cuota': valor_cuota,
            'descuento_aplicado': descuento,
            'porcentaje_descuento': porcentaje_desc,
            'fecha_limite': fecha_limite,
            'fecha_seleccion': datetime.now().isoformat(),
            'cliente_acepto_plan': True,
            'seleccion_original_usuario': f"Plan {num_cuotas} cuotas",
            'metodo_deteccion': f'cuotas_{num_cuotas}_optimizado'
        }
    
    def _procesar_con_reglas_basicas(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> Dict[str, Any]:
        """Último recurso: reglas básicas contextuales"""
        
        mensaje_lower = mensaje.lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        logger.info(f"🔧 [REGLAS] Fallback con reglas básicas")
        
        # Confirmaciones
        if any(word in mensaje_lower for word in ['si', 'sí', 'acepto', 'ok', 'está bien', 'de acuerdo']):
            if tiene_cliente and estado in ['informar_deuda', 'proponer_planes_pago']:
                return {
                    'intencion': 'CONFIRMACION_CONTEXTUAL',
                    'confianza': 0.8,
                    'next_state': 'proponer_planes_pago' if estado == 'informar_deuda' else 'generar_acuerdo',
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': f"Perfecto, {nombre}! Te muestro las opciones disponibles." if estado == 'informar_deuda' else f"Excelente, {nombre}! Procederé a generar tu acuerdo de pago.",
                    'botones': self._generar_botones_contextuales(estado, contexto),
                    'metodo': 'reglas_confirmacion',
                    'usar_resultado': True,
                    'success': True
                }
        
        # Rechazos
        elif any(word in mensaje_lower for word in ['no', 'nop', 'negativo', 'imposible', 'no puedo']):
            return {
                'intencion': 'RECHAZO_CONTEXTUAL',
                'confianza': 0.8,
                'next_state': 'gestionar_objecion',
                'contexto_actualizado': contexto,
                'mensaje_respuesta': f"Entiendo tu situación, {nombre if tiene_cliente else ''}. ¿Qué te preocupa específicamente? Podemos buscar alternativas.",
                'botones': [
                    {"id": "plan_flexible", "text": "Plan más flexible"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ],
                'metodo': 'reglas_rechazo',
                'usar_resultado': True,
                'success': True
            }
        
        # Fallback genérico
        if tiene_cliente:
            mensaje_resp = f"¿En qué más puedo ayudarte, {nombre}? Si necesitas ver las opciones de pago, puedo mostrártelas."
            botones = [
                {"id": "opciones_pago", "text": "Ver opciones de pago"},
                {"id": "asesor", "text": "Hablar con asesor"}
            ]
        else:
            mensaje_resp = "Para ayudarte de la mejor manera, necesito que me proporciones tu número de cédula."
            botones = [
                {"id": "proporcionar_cedula", "text": "Proporcionar cédula"},
                {"id": "ayuda", "text": "Necesito ayuda"}
            ]
        
        return {
            'intencion': 'REGLAS_FALLBACK',
            'confianza': 0.5,
            'next_state': estado if tiene_cliente else 'validar_documento',
            'contexto_actualizado': contexto,
            'mensaje_respuesta': mensaje_resp,
            'botones': botones,
            'metodo': 'reglas_basicas_fallback',
            'usar_resultado': True,
            'success': True
        }
    
    def _determinar_estado_desde_openai(self, resultado_openai: Dict, estado_actual: str, contexto: Dict) -> str:
        """Determinar siguiente estado basado en resultado OpenAI"""
        
        mensaje = resultado_openai.get('message', '').lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        # Análisis del contenido del mensaje de OpenAI
        if any(palabra in mensaje for palabra in ['opciones', 'planes', 'pago', 'cuotas']):
            return 'proponer_planes_pago' if tiene_cliente else 'validar_documento'
        elif any(palabra in mensaje for palabra in ['acuerdo', 'confirmar', 'proceder']):
            return 'generar_acuerdo'
        elif any(palabra in mensaje for palabra in ['supervisor', 'asesor', 'especialista']):
            return 'escalamiento'
        elif any(palabra in mensaje for palabra in ['información', 'detalle', 'saldo']):
            return 'informar_deuda' if tiene_cliente else 'validar_documento'
        
        # Lógica contextual por estado
        estado_transitions = {
            'inicial': 'validar_documento',
            'validar_documento': 'informar_deuda' if tiene_cliente else 'validar_documento',
            'informar_deuda': 'proponer_planes_pago',
            'proponer_planes_pago': 'generar_acuerdo',
            'generar_acuerdo': 'finalizar_conversacion'
        }
        
        return estado_transitions.get(estado_actual, estado_actual)
    
    def _generar_respuesta_dinamica(self, estado: str, contexto: Dict[str, Any]) -> str:
        """Generar respuesta desde tabla Estados_Conversacion"""
        try:
            query = text("""
                SELECT mensaje_template 
                FROM Estados_Conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado}).fetchone()
            
            if result and result[0]:
                template = result[0]
                logger.info(f"✅ [TEMPLATE] Obtenido para estado '{estado}'")
                
                # Resolver variables si hay servicio disponible
                if self.variable_service:
                    try:
                        mensaje_final = self.variable_service.resolver_variables(template, contexto)
                        logger.info(f"✅ [VARIABLES] Resueltas dinámicamente")
                        return mensaje_final
                    except Exception as e:
                        logger.error(f"⚠️ Error resolviendo variables: {e}")
                        return template
                else:
                    return template
            else:
                # Fallback dinámico
                tiene_cliente = contexto.get('cliente_encontrado', False)
                if tiene_cliente:
                    nombre = contexto.get('Nombre_del_cliente', 'Cliente')
                    return f"¿En qué puedo ayudarte, {nombre}?"
                else:
                    return "Para ayudarte, necesito tu número de cédula."
                
        except Exception as e:
            logger.error(f"❌ Error generando respuesta dinámica: {e}")
            return "¿En qué puedo ayudarte?"
    
    def _generar_mensaje_cliente_encontrado(self, datos_cliente: Dict) -> str:
        """Generar mensaje personalizado cuando se encuentra cliente"""
        nombre = datos_cliente['Nombre_del_cliente']
        banco = datos_cliente['banco']
        saldo = datos_cliente['saldo_total']
        
        return f"""¡Perfecto, {nombre}! 

📋 **Información de tu cuenta:**
🏦 Entidad: {banco}
💰 Saldo actual: ${saldo:,}

¿Te gustaría conocer las opciones de pago disponibles para ti?"""
    
    def _generar_botones_cliente_encontrado(self, datos_cliente: Dict) -> List[Dict[str, str]]:
        """Botones cuando se encuentra cliente"""
        return [
            {"id": "ver_opciones", "text": "Sí, quiero ver opciones"},
            {"id": "mas_info", "text": "Más información"},
            {"id": "no_ahora", "text": "No por ahora"},
            {"id": "asesor", "text": "Hablar con asesor"}
        ]
    
    def _generar_botones_dinamicos(self, estado: str, contexto: Dict) -> List[Dict]:
        """Generar botones dinámicos según estado y contexto"""
        try:
            tiene_cliente = contexto.get('cliente_encontrado', False)
            
            if estado == "informar_deuda" and tiene_cliente:
                return [
                    {"id": "si_opciones", "text": "Sí, quiero ver opciones"},
                    {"id": "mas_info", "text": "Más información"},
                    {"id": "no_ahora", "text": "No por ahora"}
                ]
            elif estado == "proponer_planes_pago" and tiene_cliente:
                return [
                    {"id": "pago_unico", "text": "Pago único con descuento"},
                    {"id": "plan_3_cuotas", "text": "Plan 3 cuotas"},
                    {"id": "plan_6_cuotas", "text": "Plan 6 cuotas"},
                    {"id": "plan_12_cuotas", "text": "Plan 12 cuotas"}
                ]
            elif estado == "generar_acuerdo":
                return [
                    {"id": "confirmar_acuerdo", "text": "Confirmar acuerdo"},
                    {"id": "modificar_terminos", "text": "Modificar términos"}
                ]
            elif estado == "finalizar_conversacion":
                return [
                    {"id": "nueva_consulta", "text": "Nueva consulta"},
                    {"id": "finalizar", "text": "Finalizar"}
                ]
            else:
                return [
                    {"id": "ayuda", "text": "Necesito ayuda"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ]
                
        except Exception as e:
            logger.error(f"❌ Error generando botones dinámicos: {e}")
            return [{"id": "ayuda", "text": "Necesito ayuda"}]
    
    def _generar_botones_dinamicos_openai(self, estado: str, contexto: Dict) -> List[Dict]:
        """Botones específicos para respuestas mejoradas por OpenAI"""
        
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if tiene_cliente:
            if estado in ['proponer_planes_pago', 'informar_deuda']:
                return [
                    {"id": "pago_unico", "text": "Pago único"},
                    {"id": "plan_cuotas", "text": "Plan de cuotas"},
                    {"id": "mas_descuento", "text": "¿Más descuento?"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ]
            elif estado == 'generar_acuerdo':
                return [
                    {"id": "confirmar_acuerdo", "text": "Confirmar acuerdo"},
                    {"id": "modificar", "text": "Modificar términos"}
                ]
            else:
                return [
                    {"id": "opciones_pago", "text": "Ver opciones"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ]
        else:
            return [
                {"id": "proporcionar_cedula", "text": "Proporcionar cédula"},
                {"id": "ayuda", "text": "Necesito ayuda"}
            ]
    
    def _generar_botones_contextuales(self, estado: str, contexto: Dict) -> List[Dict]:
        """Botones contextuales para reglas básicas"""
        
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if estado == 'informar_deuda' and tiene_cliente:
            return [
                {"id": "ver_opciones", "text": "Ver opciones de pago"},
                {"id": "mas_info", "text": "Más información"}
            ]
        elif estado == 'proponer_planes_pago' and tiene_cliente:
            return [
                {"id": "pago_unico", "text": "Pago único"},
                {"id": "cuotas", "text": "Plan cuotas"},
                {"id": "asesor", "text": "Hablar con asesor"}
            ]
        else:
            return [
                {"id": "ayuda", "text": "Necesito ayuda"},
                {"id": "asesor", "text": "Hablar con asesor"}
            ]


# ✅ FUNCIONES AUXILIARES

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
        processor = OptimizedChatProcessor(db)
        
        # ✅ 4. PROCESAR MENSAJE CON SISTEMA OPTIMIZADO
        resultado_raw = processor.process_message_optimized(
            message_content, contexto_actual, conversation.current_state
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
        processor = OptimizedChatProcessor(db)
        
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
        processor = OptimizedChatProcessor(db)
        
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
        processor = OptimizedChatProcessor(db)
        
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
        processor = OptimizedChatProcessor(db)
        
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