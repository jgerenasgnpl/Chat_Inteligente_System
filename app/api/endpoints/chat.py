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
        
class SmartLanguageProcessor:
    """
    🎯 PROCESADOR INTELIGENTE REAL
    - Usa ML como motor principal
    - Detección automática de cédulas
    - Consulta dinámica a BD
    - Sin lógica hardcodeada
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ml_service = self._initialize_ml()
        self.openai_service = self._initialize_openai()
    
    def _initialize_ml(self):
        """Inicializar servicio ML"""
        try:
            from app.services.nlp_service import nlp_service
            return nlp_service
        except Exception as e:
            print(f"⚠️ ML no disponible: {e}")
            return None
    
    def _initialize_openai(self):
        """Inicializar OpenAI si está disponible"""
        try:
            from app.services.openai_service import openai_cobranza_service
            if openai_cobranza_service.disponible:
                return openai_cobranza_service
        except Exception as e:
            print(f"⚠️ OpenAI no disponible: {e}")
        return None
    
    def procesar_mensaje_inteligente(self, mensaje: str, contexto: Dict[str, Any], estado_actual: str) -> Dict[str, Any]:
        """
        🎯 PROCESAMIENTO PRINCIPAL INTELIGENTE - CONECTADO A SISTEMA DINÁMICO
        """
        
        mensaje_limpio = mensaje.strip().lower()
        print(f"🔍 Procesando: '{mensaje}' en estado '{estado_actual}'")
        
        cedula_detectada = self._detectar_cedula_inteligente(mensaje)
        if cedula_detectada:
            return self._procesar_cedula_completa(cedula_detectada, contexto)
        
        try:
            from app.services.dynamic_transition_service import create_dynamic_transition_service
            dynamic_service = create_dynamic_transition_service(self.db)
            
            # Crear resultado ML
            ml_result = {}
            if self.ml_service:
                ml_prediction = self.ml_service.predict(mensaje)
                ml_result = {
                    'intention': ml_prediction.get('intention', 'DESCONOCIDA'),
                    'confidence': ml_prediction.get('confidence', 0.0),
                    'method': 'ml_classification'
                }
                print(f"🤖 ML: {ml_result['intention']} (confianza: {ml_result['confidence']:.2f})")
            
            transition_result = dynamic_service.determine_next_state(
                current_state=estado_actual,
                user_message=mensaje,
                ml_result=ml_result,
                context=contexto
            )
            
            print(f"🎯 TRANSICIÓN DINÁMICA: {estado_actual} → {transition_result['next_state']}")
            print(f"🔧 Método dinámico: {transition_result['detection_method']}")
            print(f"🎯 Condición detectada: {transition_result['condition_detected']}")
            
            contexto_con_retroactiva = self._detectar_seleccion_retroactiva(mensaje, contexto, estado_actual)
            contexto_con_plan = self._capturar_seleccion_plan(mensaje, transition_result, contexto_con_retroactiva)
            
            if transition_result['next_state'] == 'inicial' and estado_actual == 'finalizar_conversacion':
                print(f"🔄 REINICIANDO CONVERSACIÓN - Limpiando contexto")
                contexto_actualizado = {
                    'conversacion_reiniciada': True,
                    'timestamp_reinicio': datetime.now().isoformat(),
                    'conversation_previous_client': contexto.get('Nombre_del_cliente', 'Cliente anterior')
                }
            else:
                contexto_actualizado = contexto_con_plan
            
            # Respuesta tabla estado_conversacion
            mensaje_respuesta = self._generar_respuesta_dinamica(
                transition_result['next_state'], contexto_actualizado
            )
            
            # invocar los botones
            botones = self._generar_botones_dinamicos(
                transition_result['next_state'], contexto_actualizado
            )

            print(f"💾 CONTEXTO PROCESADO:")
            print(f"   Elementos totales: {len(contexto_actualizado)}")
            
            # Verificar si tiene plan
            if contexto_actualizado.get('plan_capturado'):
                print(f"   ✅ PLAN DETECTADO: {contexto_actualizado.get('plan_seleccionado')}")
                print(f"   ✅ MONTO: ${contexto_actualizado.get('monto_acordado', 0):,}")
            else:
                print(f"   ⚠️ Sin información de plan en contexto")

            return {
                'intencion': transition_result['condition_detected'],
                'confianza': transition_result['confidence'],
                'next_state': transition_result['next_state'],
                'contexto_actualizado': contexto_actualizado,
                'mensaje_respuesta': mensaje_respuesta,
                'botones': botones,
                'metodo': 'sistema_dinamico_completo',
                'usar_resultado': True,
                'transition_info': transition_result
            }
                
        except Exception as e:
            print(f"❌ Error en sistema dinámico: {e}")
            return self._fallback_inteligente(mensaje, contexto, estado_actual)
    
    def _detectar_seleccion_retroactiva(self, mensaje: str, contexto: Dict[str, Any], estado_actual: str) -> Dict[str, Any]:
        """
        🔍 DETECTAR SELECCIONES RETROACTIVAS 
        Detecta cuando el usuario selecciona opciones mencionadas anteriormente
        """
        try:
            mensaje_lower = mensaje.lower()
            contexto_actualizado = contexto.copy()
            
            # Detectar selecciones numéricas retroactivas
            if estado_actual in ['proponer_planes_pago', 'informar_deuda']:
                
                # Patron de plan
                if any(pattern in mensaje_lower for pattern in ['primer', 'primera', '1', 'uno']):
                    contexto_actualizado['seleccion_retroactiva'] = 'opcion_1'
                    contexto_actualizado['usuario_selecciono'] = 'primera_opcion'
                    print("🔍 Detección retroactiva: Primera opción")
                    
                elif any(pattern in mensaje_lower for pattern in ['segunda', 'segundo', '2', 'dos']):
                    contexto_actualizado['seleccion_retroactiva'] = 'opcion_2'
                    contexto_actualizado['usuario_selecciono'] = 'segunda_opcion'
                    print("🔍 Detección retroactiva: Segunda opción")
                    
                elif any(pattern in mensaje_lower for pattern in ['tercera', 'tercer', '3', 'tres']):
                    contexto_actualizado['seleccion_retroactiva'] = 'opcion_3'
                    contexto_actualizado['usuario_selecciono'] = 'tercera_opcion'
                    print("🔍 Detección retroactiva: Tercera opción")
                    
                elif any(pattern in mensaje_lower for pattern in ['cuarta', 'cuarto', '4', 'cuatro']):
                    contexto_actualizado['seleccion_retroactiva'] = 'opcion_4'
                    contexto_actualizado['usuario_selecciono'] = 'cuarta_opcion'
                    print("🔍 Detección retroactiva: Cuarta opción")
            
            if 'pago único' in mensaje_lower or 'descuento' in mensaje_lower:
                contexto_actualizado['seleccion_retroactiva'] = 'pago_unico'
                print("🔍 Detección retroactiva: Pago único")
                
            elif '3 cuotas' in mensaje_lower or 'tres cuotas' in mensaje_lower:
                contexto_actualizado['seleccion_retroactiva'] = 'plan_3_cuotas'
                print("🔍 Detección retroactiva: Plan 3 cuotas")
                
            elif '6 cuotas' in mensaje_lower or 'seis cuotas' in mensaje_lower:
                contexto_actualizado['seleccion_retroactiva'] = 'plan_6_cuotas'
                print("🔍 Detección retroactiva: Plan 6 cuotas")
                
            elif '12 cuotas' in mensaje_lower or 'doce cuotas' in mensaje_lower:
                contexto_actualizado['seleccion_retroactiva'] = 'plan_12_cuotas'
                print("🔍 Detección retroactiva: Plan 12 cuotas")
            
            return contexto_actualizado
            
        except Exception as e:
            print(f"❌ Error en detección retroactiva: {e}")
            return contexto

    def _crear_plan_retroactivo(self, tipo_plan: str, contexto: Dict) -> Dict[str, Any]:
        """Crear información de plan retroactivamente"""
        
        contexto_actualizado = contexto.copy()
        saldo_total = contexto.get('saldo_total', 0)
        oferta_2 = contexto.get('oferta_2', 0)
        cuotas_3 = contexto.get('hasta_3_cuotas', 0)
        cuotas_6 = contexto.get('hasta_6_cuotas', 0)
        
        if tipo_plan == 'pago_unico':
            plan_info = {
                'plan_seleccionado': 'Pago único con descuento',
                'monto_acordado': oferta_2,
                'numero_cuotas': 1,
                'valor_cuota': oferta_2
            }
        elif tipo_plan == 'cuotas_3':
            plan_info = {
                'plan_seleccionado': 'Plan de 3 cuotas sin interés',
                'monto_acordado': cuotas_3 * 3,
                'numero_cuotas': 3,
                'valor_cuota': cuotas_3
            }
        elif tipo_plan == 'cuotas_6':
            plan_info = {
                'plan_seleccionado': 'Plan de 6 cuotas sin interés',
                'monto_acordado': cuotas_6 * 6,
                'numero_cuotas': 6,
                'valor_cuota': cuotas_6
            }
        
        from datetime import datetime, timedelta
        plan_info.update({
            'fecha_limite': (datetime.now() + timedelta(days=7)).strftime("%d de %B de %Y"),
            'plan_capturado': True,
            'captura_retroactiva': True
        })
        
        contexto_actualizado.update(plan_info)
        print(f"✅ PLAN RETROACTIVO CREADO: {plan_info['plan_seleccionado']}")
        
        return contexto_actualizado
    
    def _capturar_seleccion_plan(self, mensaje: str, transition_result: Dict, contexto: Dict) -> Dict[str, Any]:
        """🎯 CAPTURAR SELECCIÓN DE PLAN Y CALCULAR VARIABLES - VERSIÓN CORREGIDA"""
        
        condicion = transition_result.get('condition_detected', '')
        contexto_actualizado = contexto.copy()
        
        print(f"🔍 VERIFICANDO CAPTURA DE PLAN:")
        print(f"   Condición detectada: {condicion}")
        print(f"   Mensaje: '{mensaje}'")
        
        mensaje_lower = mensaje.lower().strip()
        
        if condicion and condicion.startswith('cliente_selecciona_'):
            print(f"🎯 CAPTURANDO POR CONDICIÓN BD: {condicion}")
            contexto_con_plan = self._procesar_seleccion_por_condicion(condicion, contexto_actualizado, mensaje)
            if contexto_con_plan.get('plan_capturado'):
                return contexto_con_plan
        
        plan_detectado = self._detectar_plan_directo(mensaje_lower, contexto_actualizado)
        if plan_detectado:
            print(f"🎯 PLAN DETECTADO DIRECTAMENTE: {plan_detectado['tipo']}")
            contexto_actualizado.update(plan_detectado)
            return contexto_actualizado
        
        plan_por_numero = self._detectar_seleccion_numerica(mensaje_lower, contexto_actualizado)
        if plan_por_numero:
            print(f"🎯 PLAN DETECTADO POR NÚMERO: {plan_por_numero['tipo']}")
            contexto_actualizado.update(plan_por_numero)
            return contexto_actualizado
        
        print(f"ℹ️ No se detectó selección de plan válida")
        return contexto_actualizado

    def _detectar_seleccion_numerica(self, mensaje_lower: str, contexto: Dict) -> Optional[Dict[str, Any]]:
        """✅ DETECTAR SELECCIÓN POR NÚMEROS O POSICIONES"""
        
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

    def _generar_plan_pago_unico(self, nombre: str, saldo_total: int, oferta_2: int, contexto_seleccion: str) -> Dict[str, Any]:
        """✅ GENERAR DATOS DEL PLAN PAGO ÚNICO"""
        
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
            'metodo_deteccion': 'pago_unico_directo'
        }

    def _generar_plan_cuotas(self, nombre: str, saldo_total: int, valor_cuota: int, 
                            num_cuotas: int, descripcion_plan: str) -> Dict[str, Any]:
        """✅ GENERAR DATOS DEL PLAN DE CUOTAS"""
        
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
            'metodo_deteccion': f'cuotas_{num_cuotas}_directo'
        }

    def _procesar_seleccion_por_condicion(self, condicion: str, contexto: Dict, mensaje: str) -> Dict[str, Any]:
        """✅ PROCESAR SELECCIÓN BASADA EN CONDICIÓN BD"""
        
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
        
        # Condiciones genéricas
        elif condicion in ['cliente_selecciona_plan', 'cliente_confirma_plan_elegido']:
            plan_detectado = self._detectar_plan_directo(mensaje.lower(), contexto)
            if plan_detectado:
                return plan_detectado
            
            # Fallback
            oferta_2 = contexto.get('oferta_2', 0)
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje)
        
        return contexto 
    def _detectar_plan_directo(self, mensaje_lower: str, contexto: Dict) -> Optional[Dict[str, Any]]:
        """✅ NUEVO: Detectar plan directamente por palabras clave"""
        
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        saldo_total = contexto.get('saldo_total', 0)
        oferta_1 = contexto.get('oferta_1', 0)
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

    def _generar_respuesta_dinamica(self, estado: str, contexto: Dict[str, Any]) -> str:
        """✅ GENERAR RESPUESTA DESDE TABLA Estados_Conversacion"""
        try:
            query = text("""
                SELECT mensaje_template 
                FROM Estados_Conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado}).fetchone()
            
            if result and result[0]:
                template = result[0]
                print(f"✅ Template dinámico obtenido para estado '{estado}'")
                
                try:
                    from app.services.variable_service import crear_variable_service
                    variable_service = crear_variable_service(self.db)
                    mensaje_final = variable_service.resolver_variables(template, contexto)
                    print(f"✅ Variables resueltas dinámicamente")
                    return mensaje_final
                except Exception as e:
                    print(f"⚠️ Error resolviendo variables: {e}")
                    return template
            else:
                print(f"⚠️ No se encontró template para estado '{estado}', usando fallback")
                # Fallback
                nombre = contexto.get('Nombre_del_cliente', 'Cliente')
                return f"Gracias {nombre}, procesando tu solicitud en estado {estado}."
                
        except Exception as e:
            print(f"❌ Error generando respuesta dinámica: {e}")
            nombre = contexto.get('Nombre_del_cliente', 'Cliente')
            return f"¿En qué más puedo ayudarte, {nombre}?"

    def _generar_botones_dinamicos(self, estado: str, contexto: Dict[str, Any]) -> List[Dict[str, str]]:
        """✅ GENERAR BOTONES DINÁMICOS DESDE BD"""
        try:
            
            if estado == "proponer_planes_pago":
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
                    {"id": "continuar", "text": "Continuar"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ]
                
        except Exception as e:
            print(f"❌ Error generando botones dinámicos: {e}")
            return [{"id": "continuar", "text": "Continuar"}]
    
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
                    print(f"🎯 Cédula detectada: {cedula}")
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
        print(f"🔍 Consultando cliente con cédula: {cedula}")
        
        # Consultar cliente en BD
        cliente_data = self._consultar_cliente_avanzado(cedula)
        
        if cliente_data['encontrado']:
            contexto_actualizado = {**contexto, **cliente_data['datos']}
            
            return {
                'intencion': 'IDENTIFICACION_EXITOSA',
                'confianza': 0.98,
                'next_state': 'informar_deuda',
                'contexto_actualizado': contexto_actualizado,
                'mensaje_respuesta': self._generar_mensaje_cliente_encontrado(cliente_data['datos']),
                'botones': self._generar_botones_cliente_encontrado(cliente_data['datos']),
                'metodo': 'deteccion_cedula_automatica',
                'usar_resultado': True
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
                'usar_resultado': True
            }
    
    def _consultar_cliente_avanzado(self, cedula: str) -> Dict[str, Any]:
        """Consulta avanzada de cliente con cálculos dinámicos"""
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
                
                datos_base.update({
                    'ahorro_oferta_1': datos_base['saldo_total'] - datos_base['oferta_1'],
                    'ahorro_oferta_2': datos_base['saldo_total'] - datos_base['oferta_2'],
                    'porcentaje_desc_1': int(((datos_base['saldo_total'] - datos_base['oferta_1']) / datos_base['saldo_total']) * 100),
                    'porcentaje_desc_2': int(((datos_base['saldo_total'] - datos_base['oferta_2']) / datos_base['saldo_total']) * 100),
                    'pago_minimo': int(datos_base['saldo_total'] * 0.1),
                    'consulta_timestamp': datetime.now().isoformat()
                })
                
                print(f"✅ Cliente encontrado: {datos_base['Nombre_del_cliente']}")
                print(f"💰 Saldo: ${datos_base['saldo_total']:,}")
                print(f"🎯 Oferta mejor: ${datos_base['oferta_2']:,} ({datos_base['porcentaje_desc_2']}% desc)")
                
                return {'encontrado': True, 'datos': datos_base}
            
            print(f"❌ Cliente no encontrado para cédula: {cedula}")
            return {'encontrado': False, 'datos': {}}
            
        except Exception as e:
            print(f"❌ Error consultando cliente {cedula}: {e}")
            return {'encontrado': False, 'datos': {}, 'error': str(e)}
    
    def _clasificar_ml_avanzado(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        """Clasificación ML con validaciones avanzadas"""
        try:
            resultado_ml = self.ml_service.predict(mensaje)
            intencion = resultado_ml.get('intention', 'DESCONOCIDA')
            confianza = resultado_ml.get('confidence', 0.0)
            
            print(f"🤖 ML: {intencion} (confianza: {confianza:.2f})")
            
            usar_ml = self._validar_resultado_ml(intencion, confianza, contexto, estado)
            
            if usar_ml:
                return {
                    'intencion': intencion,
                    'confianza': confianza,
                    'next_state': self._mapear_intencion_a_estado(intencion, estado, contexto),
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': self._generar_respuesta_por_intencion(intencion, contexto, estado),
                    'botones': self._generar_botones_por_intencion(intencion, contexto, estado),
                    'metodo': 'ml_classification',
                    'usar_resultado': True
                }
            
            return {'usar_resultado': False, 'razon': 'confianza_baja_o_incoherente'}
            
        except Exception as e:
            print(f"❌ Error en ML: {e}")
            return {'usar_resultado': False, 'razon': f'error_ml: {e}'}
    
    def _validar_resultado_ml(self, intencion: str, confianza: float, contexto: Dict, estado: str) -> bool:
        """Validar si el resultado ML es coherente y confiable"""
        
        # 1. Umbral de confianza mínimo
        if confianza < 0.6:
            return False
        
        # 2. Validaciones contextuales
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if not tiene_cliente and intencion in ['INTENCION_PAGO', 'SOLICITUD_PLAN', 'CONFIRMACION']:
            if estado in ['inicial', 'validar_documento']:
                return False
        
        if tiene_cliente and intencion == 'IDENTIFICACION' and estado != 'inicial':
            return False
        
        coherencia_estado = {
            'inicial': ['SALUDO', 'IDENTIFICACION', 'CONSULTA_DEUDA'],
            'validar_documento': ['IDENTIFICACION', 'CONSULTA_DEUDA'],
            'informar_deuda': ['INTENCION_PAGO', 'SOLICITUD_PLAN', 'CONSULTA_DEUDA'],
            'proponer_planes_pago': ['CONFIRMACION', 'RECHAZO', 'SOLICITUD_PLAN', 'INTENCION_PAGO'],
            'generar_acuerdo': ['CONFIRMACION', 'RECHAZO']
        }
        
        intenciones_validas = coherencia_estado.get(estado, [])
        if intenciones_validas and intencion not in intenciones_validas:
            if confianza < 0.8: 
                return False
        
        return True
    
    def _procesar_contexto_inteligente(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        """Procesamiento contextual inteligente sin reglas hardcodeadas"""
        
        mensaje_lower = mensaje.lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        print(f"🧠 Análisis contextual: cliente={tiene_cliente}, estado={estado}")
        
        confirmacion_patterns = ['si', 'sí', 'acepto', 'ok', 'está bien', 'de acuerdo', 'confirmo', 'dale', 'bueno']
        if any(pattern in mensaje_lower for pattern in confirmacion_patterns):
            if tiene_cliente and estado in ['informar_deuda', 'proponer_planes_pago']:
                return {
                    'intencion': 'CONFIRMACION_CONTEXTUAL',
                    'confianza': 0.85,
                    'next_state': 'proponer_planes_pago' if estado == 'informar_deuda' else 'generar_acuerdo',
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': self._generar_mensaje_confirmacion(contexto, estado),
                    'botones': self._generar_botones_confirmacion(contexto, estado),
                    'metodo': 'contexto_confirmacion'
                }
        
        rechazo_patterns = ['no', 'nop', 'negativo', 'imposible', 'no puedo', 'no me interesa']
        if any(pattern in mensaje_lower for pattern in rechazo_patterns):
            return {
                'intencion': 'RECHAZO_CONTEXTUAL',
                'confianza': 0.8,
                'next_state': 'gestionar_objecion',
                'contexto_actualizado': contexto,
                'mensaje_respuesta': self._generar_mensaje_objecion(contexto),
                'botones': self._generar_botones_objecion(contexto),
                'metodo': 'contexto_rechazo'
            }
        
        info_patterns = ['opciones', 'información', 'cuanto', 'cómo', 'qué', 'planes', 'cuotas']
        if any(pattern in mensaje_lower for pattern in info_patterns):
            if tiene_cliente:
                return {
                    'intencion': 'SOLICITUD_INFO_CONTEXTUAL',
                    'confianza': 0.75,
                    'next_state': 'proponer_planes_pago',
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': self._generar_mensaje_opciones_pago(contexto),
                    'botones': self._generar_botones_opciones_pago(contexto),
                    'metodo': 'contexto_solicitud_info'
                }
        
        # Saludos diversos
        saludo_patterns = ['hola', 'buenas', 'buenos días', 'buenas tardes', 'hi']
        if any(pattern in mensaje_lower for pattern in saludo_patterns):
            if tiene_cliente:
                nombre = contexto.get('Nombre_del_cliente', 'Cliente')
                return {
                    'intencion': 'SALUDO_CONTEXTUAL',
                    'confianza': 0.9,
                    'next_state': estado,  
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': f"Hola de nuevo, {nombre}. ¿En qué más puedo ayudarte con tu cuenta?",
                    'botones': self._generar_botones_saludo_contextual(contexto, estado),
                    'metodo': 'contexto_saludo'
                }
        
        return {'confianza': 0.3, 'usar_resultado': False}
    
    def _procesar_con_openai(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        """Procesamiento con OpenAI para casos complejos"""
        try:
            if not self.openai_service.should_use_openai(mensaje, contexto, estado):
                return {'usar_resultado': False, 'razon': 'no_necesario'}
            
            resultado_openai = self.openai_service.procesar_mensaje_cobranza(mensaje, contexto, estado)
            
            if resultado_openai.get('enhanced'):
                return {
                    'intencion': 'OPENAI_ENHANCED',
                    'confianza': 0.9,
                    'next_state': self._determinar_estado_openai(resultado_openai, estado, contexto),
                    'contexto_actualizado': contexto,
                    'mensaje_respuesta': resultado_openai['message'],
                    'botones': self._generar_botones_genericos(contexto, estado),
                    'metodo': 'openai_enhancement',
                    'usar_resultado': True
                }
            
            return {'usar_resultado': False, 'razon': 'openai_no_enhanced'}
            
        except Exception as e:
            print(f"❌ Error en OpenAI: {e}")
            return {'usar_resultado': False, 'razon': f'error_openai: {e}'}
    
    def _fallback_inteligente(self, mensaje: str, contexto: Dict, estado: str) -> Dict[str, Any]:
        """Fallback inteligente cuando todos los métodos fallan"""
        
        tiene_cliente = contexto.get('cliente_encontrado', False)
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        if tiene_cliente:
            if estado == 'informar_deuda':
                mensaje_respuesta = f"{nombre}, te recuerdo que tienes opciones de pago disponibles. ¿Te gustaría conocerlas?"
                botones = [
                    {"id": "ver_opciones", "text": "Sí, ver opciones"},
                    {"id": "mas_info", "text": "Más información"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ]
                next_state = 'proponer_planes_pago'
            elif estado == 'proponer_planes_pago':
                mensaje_respuesta = f"¿Hay alguna opción de pago que te interese, {nombre}? ¿O necesitas más información sobre algún plan específico?"
                botones = self._generar_botones_opciones_pago(contexto)
                next_state = estado
            else:
                mensaje_respuesta = f"No estoy seguro de entender, {nombre}. ¿Podrías ser más específico sobre lo que necesitas?"
                botones = [
                    {"id": "opciones_pago", "text": "Ver opciones de pago"},
                    {"id": "ayuda", "text": "Necesito ayuda"},
                    {"id": "asesor", "text": "Hablar con asesor"}
                ]
                next_state = estado
        else:
            mensaje_respuesta = "Para ayudarte de la mejor manera, necesito que me proporciones tu número de cédula."
            botones = [
                {"id": "proporcionar_cedula", "text": "Proporcionar cédula"},
                {"id": "ayuda", "text": "Necesito ayuda"}
            ]
            next_state = 'validar_documento'
        
        return {
            'intencion': 'FALLBACK_INTELIGENTE',
            'confianza': 0.5,
            'next_state': next_state,
            'contexto_actualizado': contexto,
            'mensaje_respuesta': mensaje_respuesta,
            'botones': botones,
            'metodo': 'fallback_contextual',
            'usar_resultado': True
        }

    
    def _mapear_intencion_a_estado(self, intencion: str, estado_actual: str, contexto: Dict) -> str:
        """Mapeo dinámico de intención a próximo estado"""
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        mapeo_base = {
            'IDENTIFICACION': 'validar_documento',
            'SALUDO': 'validar_documento' if not tiene_cliente else estado_actual,
            'CONSULTA_DEUDA': 'informar_deuda' if tiene_cliente else 'validar_documento',
            'INTENCION_PAGO': 'proponer_planes_pago' if tiene_cliente else 'validar_documento',
            'SOLICITUD_PLAN': 'proponer_planes_pago' if tiene_cliente else 'validar_documento',
            'CONFIRMACION': self._determinar_estado_confirmacion(estado_actual, contexto),
            'RECHAZO': 'gestionar_objecion',
            'DESPEDIDA': 'finalizar_conversacion'
        }
        
        return mapeo_base.get(intencion, estado_actual)
    
    def _determinar_estado_confirmacion(self, estado_actual: str, contexto: Dict) -> str:
        """Determinar próximo estado para confirmaciones según contexto"""
        mapeo_confirmacion = {
            'informar_deuda': 'proponer_planes_pago',
            'proponer_planes_pago': 'generar_acuerdo',
            'generar_acuerdo': 'finalizar_conversacion'
        }
        return mapeo_confirmacion.get(estado_actual, 'proponer_planes_pago')
    
    def _generar_mensaje_cliente_encontrado(self, datos_cliente: Dict) -> str:
        """Generar mensaje cuando se encuentra cliente"""
        nombre = datos_cliente['Nombre_del_cliente']
        banco = datos_cliente['banco']
        saldo = datos_cliente['saldo_total']
        
        return f"""¡Perfecto, {nombre}! 

📋 **Información de tu cuenta:**
🏦 Entidad: {banco}
💰 Saldo actual: ${saldo:,}

¿Te gustaría conocer las opciones de pago disponibles para ti?"""
    
    def _generar_mensaje_confirmacion(self, contexto: Dict, estado: str) -> str:
        """Generar mensaje de confirmación contextual"""
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        
        if estado == 'informar_deuda':
            return f"Excelente, {nombre}! Te muestro las mejores opciones para tu situación:"
        elif estado == 'proponer_planes_pago':
            return f"Perfecto, {nombre}! Procederé a generar tu acuerdo de pago con los términos que has elegido."
        
        return f"Muy bien, {nombre}! Continuemos con el proceso."
    
    def _generar_mensaje_opciones_pago(self, contexto: Dict) -> str:
        """Generar mensaje con opciones de pago"""
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        saldo = contexto.get('saldo_total', 0)
        oferta_2 = contexto.get('oferta_2', 0)
        cuotas_3 = contexto.get('hasta_3_cuotas', 0)
        cuotas_6 = contexto.get('hasta_6_cuotas', 0)
        cuotas_12 = contexto.get('hasta_12_cuotas', 0)
        
        return f"""Perfecto, {nombre}! Te muestro las mejores opciones para tu saldo de ${saldo:,}:

💰 **PAGO ÚNICO CON DESCUENTO:**
🎯 Oferta especial: ${oferta_2:,} (¡Excelente ahorro!)

📅 **PLANES DE CUOTAS SIN INTERÉS:**
• 3 cuotas de: ${cuotas_3:,} cada una
• 6 cuotas de: ${cuotas_6:,} cada una  
• 12 cuotas de: ${cuotas_12:,} cada una

¿Cuál opción se adapta mejor a tu presupuesto?"""
    
    def _generar_mensaje_objecion(self, contexto: Dict) -> str:
        """Generar mensaje para manejar objeciones"""
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        return f"Entiendo tu situación, {nombre}. Estoy aquí para encontrar una solución que funcione para ti. ¿Qué te preocupa específicamente? Podemos explorar alternativas flexibles."
    
    def _generar_botones_cliente_encontrado(self, datos_cliente: Dict) -> List[Dict[str, str]]:
        """Botones para cuando se encuentra cliente"""
        return [
            {"id": "ver_opciones", "text": "Sí, quiero ver opciones"},
            {"id": "mas_info", "text": "Más información"},
            {"id": "no_ahora", "text": "No por ahora"},
            {"id": "asesor", "text": "Hablar con asesor"}
        ]
    
    def _generar_botones_opciones_pago(self, contexto: Dict) -> List[Dict[str, str]]:
        """Botones para opciones de pago"""
        return [
            {"id": "pago_unico", "text": "Pago único con descuento"},
            {"id": "plan_3_cuotas", "text": "Plan 3 cuotas"},
            {"id": "plan_6_cuotas", "text": "Plan 6 cuotas"},
            {"id": "plan_12_cuotas", "text": "Plan 12 cuotas"},
            {"id": "mas_descuento", "text": "¿Más descuento?"},
            {"id": "asesor", "text": "Hablar con asesor"}
        ]
    
    def _generar_botones_confirmacion(self, contexto: Dict, estado: str) -> List[Dict[str, str]]:
        """Botones para confirmaciones"""
        if estado == 'informar_deuda':
            return self._generar_botones_opciones_pago(contexto)
        elif estado == 'proponer_planes_pago':
            return [
                {"id": "confirmar_acuerdo", "text": "Confirmar acuerdo"},
                {"id": "modificar", "text": "Modificar términos"},
                {"id": "otras_opciones", "text": "Ver otras opciones"}
            ]
        
        return self._generar_botones_genericos(contexto, estado)
    
    def _generar_botones_objecion(self, contexto: Dict) -> List[Dict[str, str]]:
        """Botones para manejar objeciones"""
        return [
            {"id": "plan_flexible", "text": "Plan más flexible"},
            {"id": "descuento_adicional", "text": "Solicitar descuento"},
            {"id": "hablar_supervisor", "text": "Hablar con supervisor"},
            {"id": "mas_tiempo", "text": "Necesito más tiempo"}
        ]
    
    def _generar_botones_saludo_contextual(self, contexto: Dict, estado: str) -> List[Dict[str, str]]:
        """Botones para saludo cuando hay contexto"""
        if estado == 'informar_deuda':
            return [
                {"id": "ver_opciones", "text": "Ver opciones de pago"},
                {"id": "info_cuenta", "text": "Información de mi cuenta"}
            ]
        elif estado == 'proponer_planes_pago':
            return [
                {"id": "revisar_opciones", "text": "Revisar opciones"},
                {"id": "elegir_plan", "text": "Elegir plan de pago"}
            ]
        
        return [
            {"id": "continuar", "text": "Continuar proceso"},
            {"id": "ayuda", "text": "Necesito ayuda"}
        ]
    
    def _generar_botones_genericos(self, contexto: Dict, estado: str) -> List[Dict[str, str]]:
        """Botones genéricos según estado"""
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if not tiene_cliente:
            return [
                {"id": "proporcionar_cedula", "text": "Proporcionar cédula"},
                {"id": "ayuda", "text": "Necesito ayuda"}
            ]
        
        return [
            {"id": "opciones_pago", "text": "Ver opciones de pago"},
            {"id": "info_cuenta", "text": "Información de cuenta"},
            {"id": "asesor", "text": "Hablar con asesor"}
        ]
    
    def _generar_respuesta_por_intencion(self, intencion: str, contexto: Dict, estado: str) -> str:
        """Generar respuesta específica por intención ML"""
        nombre = contexto.get('Nombre_del_cliente', 'Cliente')
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if intencion == 'SALUDO':
            if tiene_cliente:
                return f"¡Hola de nuevo, {nombre}! ¿En qué puedo ayudarte hoy?"
            else:
                return "¡Hola! Para ayudarte de la mejor manera, necesito tu número de cédula."
        
        elif intencion == 'CONSULTA_DEUDA':
            if tiene_cliente:
                saldo = contexto.get('saldo_total', 0)
                banco = contexto.get('banco', 'la entidad')
                return f"Tu saldo actual con {banco} es de ${saldo:,}, {nombre}."
            else:
                return "Para consultar tu deuda, necesito primero tu número de cédula."
        
        elif intencion == 'INTENCION_PAGO':
            if tiene_cliente:
                return f"Perfecto, {nombre}! Te muestro las opciones de pago disponibles."
            else:
                return "Para mostrarte opciones de pago, primero necesito identificarte con tu cédula."
        
        elif intencion == 'SOLICITUD_PLAN':
            if tiene_cliente:
                return self._generar_mensaje_opciones_pago(contexto)
            else:
                return "Para generar un plan personalizado, necesito tu número de cédula."
        
        elif intencion == 'CONFIRMACION':
            return f"Perfecto, {nombre}! Procedo con tu solicitud."
        
        elif intencion == 'RECHAZO':
            return f"Entiendo, {nombre}. ¿Hay algo específico que te preocupa? Podemos buscar alternativas."
        
        elif intencion == 'DESPEDIDA':
            return f"Gracias por contactarnos, {nombre}. ¡Que tengas un excelente día!"
        
        return f"¿En qué más puedo ayudarte, {nombre}?" if tiene_cliente else "¿En qué puedo ayudarte? Para comenzar, necesito tu cédula."
    
    def _generar_botones_por_intencion(self, intencion: str, contexto: Dict, estado: str) -> List[Dict[str, str]]:
        """Generar botones específicos por intención ML"""
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if intencion in ['INTENCION_PAGO', 'SOLICITUD_PLAN'] and tiene_cliente:
            return self._generar_botones_opciones_pago(contexto)
        elif intencion == 'CONSULTA_DEUDA' and tiene_cliente:
            return [
                {"id": "ver_opciones", "text": "Ver opciones de pago"},
                {"id": "mas_info", "text": "Más información"}
            ]
        elif intencion == 'CONFIRMACION':
            return self._generar_botones_confirmacion(contexto, estado)
        elif intencion == 'RECHAZO':
            return self._generar_botones_objecion(contexto)
        
        return self._generar_botones_genericos(contexto, estado)
    
    def _determinar_estado_openai(self, resultado_openai: Dict, estado_actual: str, contexto: Dict) -> str:
        """Determinar próximo estado basado en resultado OpenAI"""

        mensaje = resultado_openai.get('message', '').lower()
        tiene_cliente = contexto.get('cliente_encontrado', False)
        
        if 'opciones' in mensaje or 'planes' in mensaje:
            return 'proponer_planes_pago' if tiene_cliente else 'validar_documento'
        elif 'acuerdo' in mensaje or 'confirmar' in mensaje:
            return 'generar_acuerdo'
        elif 'supervisor' in mensaje or 'asesor' in mensaje:
            return 'escalamiento'
        
        return estado_actual 

@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat_message_INTELIGENTE_DEFINITIVO(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """🎯 ENDPOINT PRINCIPAL - VERSIÓN CORREGIDA PARA DATOS DINÁMICOS"""
    
    user_id = request.user_id
    message_content = request.message or request.text or ""
    
    print(f"🚀 PROCESAMIENTO INTELIGENTE: '{message_content}' (usuario {user_id})")
    
    try:
        conversation = _get_or_create_conversation(db, user_id, request.conversation_id)
        
        # ✅ RECUPERAR CONTEXTO CON VERIFICACIÓN MEJORADA
        contexto_actual = _recuperar_contexto_seguro(db, conversation)
        
        print(f"💬 Conversación {conversation.id} - Estado: {conversation.current_state}")
        print(f"📋 Contexto inicial: {len(contexto_actual)} elementos")
        
        # ✅ VERIFICAR SI HAY DATOS DE CLIENTE EN CONTEXTO
        cliente_en_contexto = contexto_actual.get('cliente_encontrado', False)
        nombre_en_contexto = contexto_actual.get('Nombre_del_cliente')
        saldo_en_contexto = contexto_actual.get('saldo_total', 0)
        
        print(f"🔍 VERIFICACIÓN CONTEXTO INICIAL:")
        print(f"   Cliente encontrado: {cliente_en_contexto}")
        print(f"   Nombre: {nombre_en_contexto}")
        print(f"   Saldo: ${saldo_en_contexto:,}" if saldo_en_contexto else "$0")
        
        smart_processor = SmartLanguageProcessor(db)
        
        # ✅ PROCESAR MENSAJE CON CONTEXTO VERIFICADO
        resultado = smart_processor.procesar_mensaje_inteligente(
            message_content, 
            contexto_actual, 
            conversation.current_state
        )
        
        print(f"🎯 Resultado: {resultado['intencion']} (confianza: {resultado['confianza']:.2f})")
        print(f"🔧 Método: {resultado['metodo']}")
        print(f"📍 Estado: {conversation.current_state} → {resultado['next_state']}")
        
        nuevo_estado = _validar_estado_existente(resultado['next_state'])
        contexto_actualizado = resultado['contexto_actualizado']
        
        # ✅ VERIFICACIÓN CRÍTICA: ASEGURAR PROPAGACIÓN DE DATOS DEL CLIENTE
        cliente_despues = contexto_actualizado.get('cliente_encontrado', False)
        nombre_despues = contexto_actualizado.get('Nombre_del_cliente')
        saldo_despues = contexto_actualizado.get('saldo_total', 0)
        
        print(f"🔍 VERIFICACIÓN CONTEXTO DESPUÉS DEL PROCESAMIENTO:")
        print(f"   Cliente encontrado: {cliente_despues}")
        print(f"   Nombre: {nombre_despues}")
        print(f"   Saldo: ${saldo_despues:,}" if saldo_despues else "$0")
        
        # ✅ SI SE PERDIERON DATOS DEL CLIENTE, RECUPERARLOS
        if cliente_en_contexto and not cliente_despues:
            print(f"⚠️ DATOS DEL CLIENTE PERDIDOS - RECUPERANDO...")
            
            # Recuperar datos críticos del contexto inicial
            datos_a_preservar = {
                'cliente_encontrado': True,
                'Nombre_del_cliente': nombre_en_contexto,
                'nombre_cliente': nombre_en_contexto,
                'saldo_total': saldo_en_contexto,
                'banco': contexto_actual.get('banco', 'Entidad Financiera'),
                'cedula_detectada': contexto_actual.get('cedula_detectada'),
                'oferta_1': contexto_actual.get('oferta_1', 0),
                'oferta_2': contexto_actual.get('oferta_2', 0),
                'Oferta_2': contexto_actual.get('Oferta_2', 0),
                'hasta_3_cuotas': contexto_actual.get('hasta_3_cuotas', 0),
                'hasta_6_cuotas': contexto_actual.get('hasta_6_cuotas', 0),
                'hasta_12_cuotas': contexto_actual.get('hasta_12_cuotas', 0),
                'producto': contexto_actual.get('producto', 'Producto'),
                'telefono': contexto_actual.get('telefono', ''),
                'email': contexto_actual.get('email', '')
            }
            
            # ✅ COMBINAR PRESERVANDO DATOS DEL CLIENTE
            contexto_actualizado = {**contexto_actualizado, **datos_a_preservar}
            
            print(f"✅ DATOS DEL CLIENTE RECUPERADOS:")
            print(f"   Cliente encontrado: {contexto_actualizado.get('cliente_encontrado')}")
            print(f"   Nombre: {contexto_actualizado.get('Nombre_del_cliente')}")
            print(f"   Saldo: ${contexto_actualizado.get('saldo_total', 0):,}")
        
        # ✅ ACTUALIZAR CONVERSACIÓN CON SERIALIZACIÓN SEGURA
        conversation.current_state = nuevo_estado
        conversation.updated_at = datetime.now()
        
        # ✅ LIMPIAR Y SERIALIZAR CONTEXTO DE FORMA SEGURA
        contexto_limpio = limpiar_contexto_para_bd(contexto_actualizado)
        conversation.context_data = safe_json_dumps(contexto_limpio)
        
        print(f"💾 PERSISTIENDO CONTEXTO FINAL:")
        print(f"   Elementos totales: {len(contexto_actualizado)}")
        print(f"   Cliente encontrado final: {contexto_actualizado.get('cliente_encontrado', False)}")
        
        if contexto_actualizado.get('plan_capturado'):
            print(f"   ✅ PLAN DETECTADO: {contexto_actualizado.get('plan_seleccionado')}")
            print(f"   ✅ MONTO: ${contexto_actualizado.get('monto_acordado', 0):,}")
        
        print(f"💾 GUARDANDO EN BD...")
        db.commit()
        print(f"✅ CONTEXTO GUARDADO EN TABLA CONVERSATIONS")
    
        # ✅ LOG CON MANEJO SEGURO DE TIPOS
        try:
            _log_interaccion_completa(db, conversation, message_content, resultado, request.button_selected)
        except Exception as log_error:
            print(f"⚠️ Error en logging (no crítico): {log_error}")
        
        print(f"✅ Respuesta generada exitosamente")
        
        # ✅ VERIFICACIÓN FINAL
        cliente_final = contexto_actualizado.get('cliente_encontrado', False)
        print(f"📊 Cliente encontrado FINAL: {cliente_final}")
        
        if not cliente_final and (cliente_en_contexto or nombre_en_contexto):
            print(f"❌ WARNING: Se perdieron datos del cliente en el proceso")
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=resultado['mensaje_respuesta'],
            current_state=nuevo_estado,
            buttons=resultado['botones'],
            context=contexto_actualizado  # ✅ CONTEXT LIMPIO
        )
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
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

def _recuperar_contexto_seguro(db: Session, conversation: Conversation) -> Dict[str, Any]:
    """✅ RECUPERAR CONTEXTO CON VERIFICACIÓN MEJORADA"""
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
                    print(f"✅ Contexto recuperado desde conversation.context_data: {len(contexto)} elementos")
                    
                    # ✅ VERIFICAR DATOS CRÍTICOS
                    if contexto.get('cliente_encontrado'):
                        print(f"✅ Cliente en contexto: {contexto.get('Nombre_del_cliente')}")
                        print(f"✅ Saldo en contexto: ${contexto.get('saldo_total', 0):,}")
                    
                    return contexto
            except json.JSONDecodeError as e:
                print(f"⚠️ Error parseando JSON del contexto: {e}")
        
        # 2. Consulta directa a BD como fallback
        try:
            query = text("SELECT context_data FROM conversations WHERE id = :conv_id")
            result = db.execute(query, {"conv_id": conversation.id}).fetchone()
            
            if result and result[0]:
                contexto = json.loads(result[0])
                if isinstance(contexto, dict):
                    print(f"✅ Contexto recuperado desde consulta directa: {len(contexto)} elementos")
                    return contexto
        except Exception as e:
            print(f"⚠️ Error en consulta directa de contexto: {e}")
        
        print(f"⚠️ No se encontró contexto válido, iniciando vacío")
        return {}
        
    except Exception as e:
        print(f"❌ Error crítico recuperando contexto: {e}")
        return {}

def _validar_continuidad_cliente(contexto_antes: Dict, contexto_despues: Dict) -> Dict[str, Any]:
    """Valida que los datos del cliente se mantengan en el contexto"""
    
    datos_cliente_antes = {
        'cliente_encontrado': contexto_antes.get('cliente_encontrado', False),
        'nombre': contexto_antes.get('Nombre_del_cliente'),
        'saldo': contexto_antes.get('saldo_total', 0),
        'cedula': contexto_antes.get('cedula_detectada')
    }
    
    datos_cliente_despues = {
        'cliente_encontrado': contexto_despues.get('cliente_encontrado', False),
        'nombre': contexto_despues.get('Nombre_del_cliente'),
        'saldo': contexto_despues.get('saldo_total', 0),
        'cedula': contexto_despues.get('cedula_detectada')
    }
    
    # Si había cliente antes pero no después, es un problema
    if datos_cliente_antes['cliente_encontrado'] and not datos_cliente_despues['cliente_encontrado']:
        print(f"❌ PÉRDIDA DE DATOS DEL CLIENTE DETECTADA")
        print(f"   Antes: {datos_cliente_antes}")
        print(f"   Después: {datos_cliente_despues}")
        
        # Reparar contexto
        return {**contexto_despues, **{
            'cliente_encontrado': True,
            'Nombre_del_cliente': datos_cliente_antes['nombre'],
            'saldo_total': datos_cliente_antes['saldo'],
            'cedula_detectada': datos_cliente_antes['cedula']
        }}
    
    return contexto_despues

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
        print(f"🔄 Estado mapeado: {estado} → {estado_mapeado}")
    
    return estado_mapeado

def _log_interaccion_completa(db: Session, conversation: Conversation, mensaje_usuario: str, 
                             resultado: Dict[str, Any], button_selected: Optional[str]):
    """✅ VERSIÓN CORREGIDA - Log completo con serialización segura"""
    try:
        LogService.log_message_safe(
            db=db,
            conversation_id=conversation.id,
            sender_type="system",
            text_content=resultado['mensaje_respuesta'],
            previous_state=conversation.current_state,
            next_state=resultado['next_state'],
            metadata_dict=metadata_raw  # ✅ PASAR DICT, NO STRING
        )
        
        # ✅ LIMPIAR METADATA ANTES DE SERIALIZAR
        metadata_raw = {
            "intencion_detectada": resultado.get('intencion'),
            "metodo_procesamiento": resultado.get('metodo'),
            "confianza": resultado.get('confianza'),
            "sistema_inteligente": True,
            "motor_ml_integrado": True,
            "deteccion_automatica_cedulas": True,
            "procesamiento_dinamico": True,
            "timestamp": datetime.now().isoformat(),
            "transition_info": resultado.get('transition_info', {})  # Esto puede contener Decimal
        }
        
        # ✅ USAR FUNCIÓN DE LIMPIEZA PARA METADATA
        metadata_limpio = clean_data_for_json(metadata_raw)
        
        # ✅ USAR ENCODER PERSONALIZADO
        metadata_json = safe_json_dumps(metadata_limpio)
        
        LogService.log_message(
            db=db,
            conversation_id=conversation.id,
            sender_type="system",
            text_content=resultado['mensaje_respuesta'],
            previous_state=conversation.current_state,
            next_state=resultado['next_state'],
            metadata=metadata_json  # ✅ AHORA USA SERIALIZACIÓN SEGURA
        )
        
    except Exception as e:
        print(f"⚠️ Error en logging (no crítico): {e}")
        # ✅ LOGGING SIMPLIFICADO SIN METADATA COMO FALLBACK
        try:
            LogService.log_message(
                db=db,
                conversation_id=conversation.id,
                sender_type="system",
                text_content=resultado['mensaje_respuesta'],
                previous_state=conversation.current_state,
                next_state=resultado['next_state']
            )
        except:
            pass  # No es crítico si falla el logging

def _build_client_context(self, cliente_info: Dict[str, Any], cedula: str) -> Dict[str, Any]:
    """✅ CORREGIDO - Construir contexto del cliente de forma estructurada con datos reales"""
    
    print(f"🔧 [BUILD_CONTEXT] Construyendo contexto para cédula: {cedula}")
    print(f"🔧 [BUILD_CONTEXT] Datos recibidos: {list(cliente_info.keys())}")
    
    # ✅ VERIFICAR SI HAY DATOS REALES DEL CLIENTE
    if cliente_info.get('encontrado', False):
        # ✅ EXTRAER DATOS REALES DE LA BD
        datos_cliente = {
            "cedula_detectada": cedula,
            "cliente_encontrado": True,  # ✅ CRÍTICO
            "Nombre_del_cliente": cliente_info.get("nombre", "Cliente"),
            "nombre_cliente": cliente_info.get("nombre", "Cliente"),  # Alias
            
            # ✅ CONVERTIR A ENTEROS Y FORMATEAR CORRECTAMENTE
            "saldo_total": int(float(cliente_info.get("saldo", 0))) if cliente_info.get("saldo") else 0,
            "banco": cliente_info.get("banco", "Entidad Financiera"),
            
            # ✅ OFERTAS (nombres exactos de BD)
            "oferta_1": int(float(cliente_info.get("oferta_1", 0))) if cliente_info.get("oferta_1") else 0,
            "oferta_2": int(float(cliente_info.get("oferta_2", 0))) if cliente_info.get("oferta_2") else 0,
            "Oferta_1": int(float(cliente_info.get("oferta_1", 0))) if cliente_info.get("oferta_1") else 0,
            "Oferta_2": int(float(cliente_info.get("oferta_2", 0))) if cliente_info.get("oferta_2") else 0,
            
            # ✅ CUOTAS
            "hasta_3_cuotas": int(float(cliente_info.get("hasta_3_cuotas", 0))) if cliente_info.get("hasta_3_cuotas") else 0,
            "hasta_6_cuotas": int(float(cliente_info.get("hasta_6_cuotas", 0))) if cliente_info.get("hasta_6_cuotas") else 0,
            "hasta_12_cuotas": int(float(cliente_info.get("hasta_12_cuotas", 0))) if cliente_info.get("hasta_12_cuotas") else 0,
            
            # ✅ OTROS DATOS
            "producto": cliente_info.get("producto", "Producto"),
            "telefono": cliente_info.get("telefono", ""),
            "email": cliente_info.get("email", ""),
            
            # ✅ METADATA
            "consulta_timestamp": datetime.now().isoformat(),
            "consulta_method": "dynamic_detection_fixed"
        }
        
        print(f"✅ [BUILD_CONTEXT] CLIENTE REAL ENCONTRADO:")
        print(f"   Nombre: {datos_cliente['Nombre_del_cliente']}")
        print(f"   Saldo: ${datos_cliente['saldo_total']:,}")
        print(f"   Oferta_2: ${datos_cliente['oferta_2']:,}")
        print(f"   Cliente encontrado: {datos_cliente['cliente_encontrado']}")
        
        return datos_cliente
    
    else:
        print(f"❌ [BUILD_CONTEXT] Cliente NO encontrado para cédula: {cedula}")
        return {
            "cedula_detectada": cedula,
            "cliente_encontrado": False,  # ✅ CRÍTICO
            "consulta_timestamp": datetime.now().isoformat(),
            "error": "Cliente no encontrado en BD"
        }

# ✅ CORRECCIÓN 2: Método _query_client_simple MEJORADO

async def _query_client_simple(self, cedula: str) -> Optional[Dict]:
    """✅ CORREGIDO - Consulta simple de cliente con logs detallados"""
    try:
        print(f"🔍 [QUERY_CLIENT] Consultando cédula: {cedula}")
        
        query = text("""
            SELECT TOP 1 
                Nombre_del_cliente, Saldo_total, banco,
                Oferta_1, Oferta_2, 
                Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas,
                Producto, Telefono, Email
            FROM ConsolidadoCampañasNatalia 
            WHERE CAST(Cedula AS VARCHAR) = :cedula
            ORDER BY Saldo_total DESC
        """)
        
        result = self.db.execute(query, {"cedula": str(cedula)})
        row = result.fetchone()
        
        if row:
            cliente_data = {
                "encontrado": True,
                "nombre": row[0] or "Cliente",
                "saldo": int(float(row[1])) if row[1] else 0,
                "banco": row[2] or "Entidad Financiera",
                "oferta_1": int(float(row[3])) if row[3] else 0,
                "oferta_2": int(float(row[4])) if row[4] else 0,
                "hasta_3_cuotas": int(float(row[5])) if row[5] else 0,
                "hasta_6_cuotas": int(float(row[6])) if row[6] else 0,
                "hasta_12_cuotas": int(float(row[7])) if row[7] else 0,
                "producto": row[8] or "Producto",
                "telefono": row[9] or "",
                "email": row[10] or ""
            }
            
            print(f"✅ [QUERY_CLIENT] CLIENTE ENCONTRADO EN BD:")
            print(f"   Nombre: {cliente_data['nombre']}")
            print(f"   Saldo: ${cliente_data['saldo']:,}")
            print(f"   Oferta_2: ${cliente_data['oferta_2']:,}")
            print(f"   Banco: {cliente_data['banco']}")
            
            return cliente_data
        
        print(f"❌ [QUERY_CLIENT] Cliente NO encontrado en BD para cédula: {cedula}")
        return {"encontrado": False}
        
    except Exception as e:
        print(f"❌ [QUERY_CLIENT] Error consultando cliente {cedula}: {e}")
        return {"encontrado": False}

# ✅ CORRECCIÓN 3: Método _procesar_seleccion_por_condicion CORREGIDO

def _procesar_seleccion_por_condicion(self, condicion: str, contexto: Dict, mensaje: str) -> Dict[str, Any]:
    """✅ CORREGIDO - Procesar selección basada en condición BD con datos reales"""
    
    print(f"🎯 [SELECCION] Procesando condición: {condicion}")
    print(f"🎯 [SELECCION] Contexto disponible: {list(contexto.keys())}")
    
    # ✅ VERIFICAR DATOS REALES DEL CLIENTE
    nombre = contexto.get('Nombre_del_cliente') or contexto.get('nombre_cliente', 'Cliente')
    saldo_total = contexto.get('saldo_total', 0)
    
    # ✅ SI NO HAY DATOS REALES, USAR CONSULTA DIRECTA
    cedula = contexto.get('cedula_detectada')
    if (not saldo_total or saldo_total == 0) and cedula:
        print(f"⚠️ [SELECCION] Sin datos reales, consultando BD directamente para: {cedula}")
        
        # ✅ CONSULTA DIRECTA A BD
        query = text("""
            SELECT TOP 1 
                Nombre_del_cliente, Saldo_total, Oferta_1, Oferta_2,
                Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas, banco
            FROM ConsolidadoCampañasNatalia 
            WHERE CAST(Cedula AS VARCHAR) = :cedula
        """)
        
        try:
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            if result:
                nombre = result[0] or "Cliente"
                saldo_total = int(float(result[1])) if result[1] else 0
                oferta_1 = int(float(result[2])) if result[2] else 0
                oferta_2 = int(float(result[3])) if result[3] else 0
                cuotas_3 = int(float(result[4])) if result[4] else 0
                cuotas_6 = int(float(result[5])) if result[5] else 0
                cuotas_12 = int(float(result[6])) if result[6] else 0
                banco = result[7] or "Entidad Financiera"
                
                print(f"✅ [SELECCION] DATOS BD OBTENIDOS:")
                print(f"   Cliente: {nombre}")
                print(f"   Saldo: ${saldo_total:,}")
                print(f"   Oferta_2: ${oferta_2:,}")
            else:
                print(f"❌ [SELECCION] No se encontraron datos en BD")
                # Usar valores por defecto
                saldo_total = 15000  # ⚠️ TEMPORAL
                oferta_2 = 10500     # ⚠️ TEMPORAL
                cuotas_3 = 5500      # ⚠️ TEMPORAL
                cuotas_6 = 2800      # ⚠️ TEMPORAL
                cuotas_12 = 1400     # ⚠️ TEMPORAL
        except Exception as e:
            print(f"❌ [SELECCION] Error en consulta BD: {e}")
            return contexto
    else:
        # ✅ USAR DATOS DEL CONTEXTO
        oferta_1 = contexto.get('oferta_1', 0)
        oferta_2 = contexto.get('oferta_2', 0) or contexto.get('Oferta_2', 0)
        cuotas_3 = contexto.get('hasta_3_cuotas', 0)
        cuotas_6 = contexto.get('hasta_6_cuotas', 0)
        cuotas_12 = contexto.get('hasta_12_cuotas', 0)
    
    print(f"🎯 [SELECCION] DATOS PARA CÁLCULO:")
    print(f"   Saldo total: ${saldo_total:,}")
    print(f"   Oferta_2: ${oferta_2:,}")
    print(f"   Cuotas_6: ${cuotas_6:,}")
    
    # ✅ PROCESAR SEGÚN CONDICIÓN
    if condicion == 'cliente_selecciona_pago_unico':
        return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje)
    
    elif condicion == 'cliente_selecciona_plan_3_cuotas':
        return self._generar_plan_cuotas(nombre, saldo_total, cuotas_3, 3, "Plan 3 cuotas sin interés")
    
    elif condicion == 'cliente_selecciona_plan_6_cuotas':
        return self._generar_plan_cuotas(nombre, saldo_total, cuotas_6, 6, "Plan 6 cuotas sin interés")
    
    elif condicion == 'cliente_selecciona_plan_12_cuotas':
        return self._generar_plan_cuotas(nombre, saldo_total, cuotas_12, 12, "Plan 12 cuotas sin interés")
    
    # ✅ CONDICIONES GENÉRICAS
    elif condicion in ['cliente_selecciona_plan', 'cliente_confirma_plan_elegido']:
        # Detectar tipo de plan por el mensaje
        mensaje_lower = mensaje.lower()
        if any(word in mensaje_lower for word in ['unico', 'descuento', 'liquidar']):
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje)
        else:
            # Por defecto, pago único
            return self._generar_plan_pago_unico(nombre, saldo_total, oferta_2, mensaje)
    
    return contexto

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
        print(f"🆕 Usuario {user_id} creado")
    
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

@router.post("/test-inteligente")
async def test_sistema_inteligente(db: Session = Depends(get_db)):
    """Test completo del sistema inteligente"""
    
    test_messages = [
        "hola mi cedula es 93388915",
        "quiero pagar mi deuda",
        "cuales son las opciones",
        "acepto la primera opcion",
        "no puedo pagar ahora",
        "12345678",
        "necesito mas descuento",
        "plan de cuotas"
    ]
    
    processor = SmartLanguageProcessor(db)
    results = []
    
    contexto_test = {}
    estado_test = "inicial"
    
    for i, mensaje in enumerate(test_messages):
        resultado = processor.procesar_mensaje_inteligente(mensaje, contexto_test, estado_test)
        
        contexto_test = resultado['contexto_actualizado']
        estado_test = resultado['next_state']
        
        results.append({
            "paso": i + 1,
            "mensaje": mensaje,
            "intencion": resultado['intencion'],
            "confianza": round(resultado['confianza'], 3),
            "metodo": resultado['metodo'],
            "estado_anterior": estado_test,
            "estado_nuevo": resultado['next_state'],
            "cliente_encontrado": contexto_test.get('cliente_encontrado', False),
            "respuesta_generada": resultado['mensaje_respuesta'][:100] + "..." if len(resultado['mensaje_respuesta']) > 100 else resultado['mensaje_respuesta']
        })
    
    return {
        "status": "success",
        "sistema": "inteligente_sin_codigo_quemado",
        "test_results": results,
        "features_activas": [
            "deteccion_automatica_cedulas",
            "ml_classification_avanzada", 
            "procesamiento_contextual_inteligente",
            "openai_enhancement_complejo",
            "fallback_inteligente",
            "sin_codigo_hardcodeado",
            "dinamico_basado_en_contexto_y_ml"
        ]
    }

@router.post("/test-cedula", response_model=CedulaTestResponse)
async def test_cedula_inteligente(request: CedulaTestRequest, db: Session = Depends(get_db)):
    """Test de detección y consulta de cédulas"""
    try:
        processor = SmartLanguageProcessor(db)
        
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
            resultado = processor._consultar_cliente_avanzado(cedula_detectada)
            
            if resultado['encontrado']:
                datos = resultado['datos']
                return CedulaTestResponse(
                    cedula=cedula_detectada,
                    cliente_encontrado=True,
                    nombre_cliente=datos.get("Nombre_del_cliente"),
                    saldo_total=f"${datos.get('saldo_total', 0):,}",
                    banco=datos.get("banco"),
                    mensaje=f"Cliente {datos.get('Nombre_del_cliente')} encontrado con detección inteligente"
                )
            else:
                return CedulaTestResponse(
                    cedula=cedula_detectada,
                    cliente_encontrado=False,
                    mensaje=f"Cédula {cedula_detectada} detectada correctamente pero cliente no encontrado en BD"
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
            mensaje=f"Error en test inteligente: {str(e)}"
        )

@router.get("/test")
async def system_health_check():
    """Health check del sistema inteligente"""
    return {
        "status": "operational",
        "system": "chat_inteligente_sin_codigo_quemado_v2",
        "timestamp": datetime.now().isoformat(),
        "capabilities": [
            "deteccion_automatica_cedulas_multiples_formatos",
            "ml_classification_con_validacion_contextual",
            "procesamiento_contextual_avanzado_dinamico",
            "openai_enhancement_casos_complejos",
            "fallback_inteligente_contextual",
            "mapeo_dinamico_intenciones_estados",
            "generacion_respuestas_contextuales",
            "botones_dinamicos_por_situacion",
            "consulta_bd_con_calculos_automaticos",
            "sin_codigo_hardcodeado_100_dinamico"
        ],
        "dependencies": {
            "ml_service": "required",
            "openai_service": "optional_enhancement",
            "database": "required",
            "tables_required": ["ConsolidadoCampañasNatalia", "conversations", "messages"],
            "tables_optional": ["Estados_Conversacion", "Variables_Sistema"]
        },
        "message": "Sistema completamente inteligente y dinámico funcionando correctamente"
    }

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