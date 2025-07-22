"""
🤖 OPENAI SERVICE CORREGIDO PARA VERSIÓN v1.0+
- Compatibilidad con nuevas versiones de openai
- Manejo robusto de errores de inicialización
- Sin parámetros deprecated
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from datetime import datetime
import hashlib
from app.services.cache_service import cache_service, cache_result

load_dotenv()
logger = logging.getLogger(__name__)

class OpenAICobranzaService:
    """Servicio OpenAI optimizado específicamente para gestión de cobranza"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.disponible = False
        
        # ✅ CONFIGURACIÓN PARA 80% DE USO
        self.USE_OPENAI_PERCENTAGE = 80  # 80% de los casos usarán OpenAI
        self.MIN_CONFIDENCE_THRESHOLD = 0.3  # Umbral mínimo para activar OpenAI
        
        # ✅ PROMPTS ESPECIALIZADOS EN COBRANZA
        self.cobranza_prompts = {
            "system_base": """Eres un especialista en gestión de cobranza profesional y empático de Systemgroup. 

CARACTERÍSTICAS PRINCIPALES:
- Siempre mantén un tono profesional pero humano
- Enfócate en encontrar soluciones viables para el cliente
- Usa técnicas de persuasión ética y empática
- Personaliza cada respuesta con los datos del cliente
- Evita ser agresivo o amenazante
- Siempre ofrece alternativas flexibles

INFORMACIÓN EMPRESA:
- Empresa: Systemgroup
- Función: Gestión de obligaciones financieras
- Objetivo: Encontrar acuerdos de pago beneficiosos para ambas partes""",
            
            "negociacion": """Estás en una negociación de deuda. El cliente {nombre} tiene una deuda de ${saldo:,} con {banco}.

ESTRATEGIA DE NEGOCIACIÓN:
1. Reconoce la situación del cliente
2. Presenta las ofertas de manera atractiva
3. Enfatiza los beneficios y ahorros
4. Crea urgencia sin presionar
5. Ofrece flexibilidad en los términos

OFERTAS DISPONIBLES:
- Pago único: ${oferta_unica:,} (Ahorro: ${ahorro:,})
- Plan cuotas: {cuotas} pagos de ${valor_cuota:,}
- Pago flexible: Desde ${pago_minimo:,}

Genera una respuesta persuasiva y empática.""",
            
            "objecion": """El cliente {nombre} ha puesto una objeción: "{objecion}"

TÉCNICAS PARA MANEJAR OBJECIONES:
1. Escucha activa: "Entiendo que..."
2. Valida su preocupación
3. Reframe: Presenta la situación de manera positiva
4. Ofrece alternativas específicas
5. Busca compromiso parcial

RESPUESTA: Genera una respuesta que maneje la objeción de manera empática y ofrezca soluciones.""",
            
            "cierre": """Es momento de cerrar el acuerdo con {nombre}.

TÉCNICAS DE CIERRE:
1. Resumen de beneficios
2. Crear urgencia apropiada
3. Simplificar la decisión
4. Asumir la venta
5. Ofrecer garantías

Genera un cierre persuasivo pero respetuoso.""",
            
            "seguimiento": """Necesitas hacer seguimiento a {nombre} que no ha respondido.

ESTRATEGIA DE SEGUIMIENTO:
1. Reconocer la demora sin juzgar
2. Reafirmar la oferta
3. Ofrecer asistencia adicional
4. Mantener la puerta abierta
5. Proporcionar alternativas de contacto

Genera un mensaje de seguimiento profesional."""
        }
        
        # ✅ INICIALIZAR OPENAI CON MANEJO ROBUSTO
        self._initialize_openai_client()
    
    def _initialize_openai_client(self):
        """✅ INICIALIZACIÓN CORREGIDA PARA OPENAI v1.0+"""
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY no configurada")
            print("⚠️ OPENAI_API_KEY no encontrada en variables de entorno")
            return
        
        try:
            # ✅ IMPORTAR Y VERIFICAR VERSIÓN
            import openai
            logger.info(f"📦 OpenAI version: {getattr(openai, '__version__', 'unknown')}")
            
            # ✅ INICIALIZACIÓN COMPATIBLE CON v1.0+
            from openai import OpenAI
            
            # ✅ CONFIGURACIÓN SIMPLE SIN PARÁMETROS DEPRECATED
            self.client = OpenAI(
                api_key=self.api_key,
                # ✅ Eliminar parámetros deprecated como 'proxies'
                timeout=30.0,  # Timeout en segundos
                max_retries=2  # Número de reintentos
            )
            
            # ✅ TEST DE CONEXIÓN BÁSICO
            test_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente de prueba."},
                    {"role": "user", "content": "Di 'test exitoso' en una palabra."}
                ],
                max_tokens=5,
                temperature=0
            )
            
            if test_response and test_response.choices:
                self.disponible = True
                logger.info("✅ OpenAI Cobranza Service inicializado y probado")
                print("🤖 OpenAI optimizado para COBRANZA activado")
                print(f"🔑 API Key configurada: {self.api_key[:8]}...{self.api_key[-4:]}")
            else:
                logger.error("❌ Test de OpenAI falló - respuesta vacía")
                print("❌ Test de OpenAI falló")
                
        except ImportError as e:
            logger.error(f"❌ Error importando OpenAI: {e}")
            print(f"❌ Error: Instalar openai con: pip install openai>=1.0.0")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando OpenAI: {e}")
            print(f"❌ Error inicializando OpenAI: {e}")
            
            # ✅ DIAGNÓSTICO DETALLADO
            self._diagnostic_openai_error(e)
    
    def _diagnostic_openai_error(self, error: Exception):
        """✅ DIAGNÓSTICO DETALLADO DE ERRORES DE OPENAI"""
        error_str = str(error).lower()
        
        print(f"\n🔍 DIAGNÓSTICO DE ERROR OPENAI:")
        print(f"   Error: {error}")
        print(f"   Tipo: {type(error).__name__}")
        
        # ✅ DIAGNÓSTICOS ESPECÍFICOS
        if "proxies" in error_str:
            print(f"   🔧 SOLUCIÓN: Actualizar librería openai")
            print(f"   📦 Ejecutar: pip install --upgrade openai>=1.0.0")
            
        elif "api_key" in error_str or "unauthorized" in error_str:
            print(f"   🔑 PROBLEMA: API Key inválida o faltante")
            print(f"   🔧 SOLUCIÓN: Verificar OPENAI_API_KEY en .env")
            
        elif "timeout" in error_str or "connection" in error_str:
            print(f"   🌐 PROBLEMA: Conectividad")
            print(f"   🔧 SOLUCIÓN: Verificar conexión a internet")
            
        elif "rate" in error_str or "quota" in error_str:
            print(f"   💰 PROBLEMA: Límites de API")
            print(f"   🔧 SOLUCIÓN: Verificar créditos en OpenAI")
            
        else:
            print(f"   ❓ Error desconocido - revisar documentación OpenAI")
        
        print(f"   📚 Docs: https://platform.openai.com/docs")
        print()
    
    def enhance_response(self, enhancement_prompt: str, context: Dict[str, Any]) -> Optional[str]:
        """✅ NUEVO: Mejorar respuesta específica con IA"""
        
        try:
            if not self.disponible:
                return None
            
            # ✅ MENSAJE ESPECÍFICO PARA MEJORA DE RESPUESTAS
            messages = [
                {
                    "role": "system",
                    "content": """Eres un asistente especializado en mejorar respuestas de sistemas de cobranza.
                    
                    OBJETIVOS:
                    - Hacer las respuestas más empáticas y profesionales
                    - Incluir información específica del cliente cuando sea relevante
                    - Mantener el tono de negociación de deudas
                    - Ser conciso pero completo
                    - Usar emojis apropiados para el contexto
                    
                    RESTRICCIONES:
                    - NO inventar información que no esté en el contexto
                    - NO cambiar números, fechas o datos específicos
                    - Máximo 200 palabras
                    - Mantener estructura similar a la respuesta base"""
                },
                {
                    "role": "user", 
                    "content": enhancement_prompt
                }
            ]
            
            # ✅ LLAMADA OPTIMIZADA PARA MEJORA
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Modelo más económico para mejoras
                messages=messages,
                max_tokens=300,  # Respuestas cortas
                temperature=0.7,  # Algo de creatividad pero controlada
                timeout=10  # Timeout corto
            )
            
            enhanced_text = response.choices[0].message.content.strip()
            
            # ✅ VALIDAR RESPUESTA MEJORADA
            if enhanced_text and len(enhanced_text) > 10:
                self._record_usage("response_enhancement", True)
                return enhanced_text
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error mejorando respuesta: {e}")
            self._record_usage("response_enhancement", False)
            return None

    def should_use_openai(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> bool:
        """
        ✅ DECISOR INTELIGENTE - 80% de uso en casos relevantes
        """
        
        if not self.disponible:
            return False
        
        # 1. CASOS DONDE SIEMPRE USAR OPENAI (Alta prioridad)
        casos_alta_prioridad = [
            # Estados críticos de negociación
            estado in ["proponer_planes_pago", "evaluar_intencion_pago", "gestionar_objecion", "generar_acuerdo"],
            
            # Cliente con datos (personalización)
            contexto.get("Nombre_del_cliente") and contexto.get("saldo_total", 0) > 0,
            
            # Mensajes complejos que requieren manejo empático
            any(palabra in mensaje.lower() for palabra in [
                "no puedo", "difícil", "problema", "crisis", "desempleo", 
                "porque", "pero", "sin embargo", "explicar", "no entiendo"
            ]),
            
            # Objeciones o resistencias
            any(palabra in mensaje.lower() for palabra in [
                "no me interesa", "muy caro", "no tengo", "imposible", 
                "no reconozco", "ya pagué", "no es mío"
            ]),
            
            # Solicitudes de información o negociación
            any(palabra in mensaje.lower() for palabra in [
                "descuento", "rebaja", "plan", "cuotas", "facilidades",
                "opciones", "alternativas", "ayuda", "asesor"
            ])
        ]
        
        # 2. CASOS DONDE NO USAR OPENAI (Evitar sobreuso)
        casos_baja_prioridad = [
            # Mensajes muy cortos o básicos
            len(mensaje.strip()) < 3,
            
            # Solo números (probablemente cédulas)
            mensaje.strip().isdigit(),
            
            # Estados técnicos
            estado in ["inicial", "validar_documento", "cliente_no_encontrado", "fin"],
            
            # Respuestas muy simples
            mensaje.lower().strip() in ["si", "sí", "no", "ok", "hola", "adiós"]
        ]
        
        # 3. LÓGICA DE DECISIÓN
        if any(casos_alta_prioridad):
            uso_openai = 95  # 95% probabilidad
        elif any(casos_baja_prioridad):
            uso_openai = 20   # 20% probabilidad  
        else:
            uso_openai = self.USE_OPENAI_PERCENTAGE  # 80% por defecto
        
        # 4. DECISIÓN FINAL ALEATORIA
        import random
        decision = random.randint(1, 100) <= uso_openai
        
        if decision:
            logger.info(f"🤖 OpenAI activado ({uso_openai}% probabilidad) para: '{mensaje[:30]}...'")
        else:
            logger.info(f"⚡ Usando ML/Reglas ({100-uso_openai}% probabilidad) para: '{mensaje[:30]}...'")
        
        return decision
    
    def procesar_mensaje_cobranza(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> Dict[str, Any]:
        """
        ✅ PROCESADOR PRINCIPAL - Manejo inteligente con prompts de cobranza
        """
        
        if not self.should_use_openai(mensaje, contexto, estado):
            return {"enhanced": False, "reason": "openai_not_selected"}
        
        if not self.disponible:
            return {"enhanced": False, "reason": "openai_not_available"}
        
        try:
            # 1. DETECTAR TIPO DE INTERACCIÓN
            tipo_interaccion = self._detectar_tipo_interaccion(mensaje, contexto, estado)
            
            # 2. GENERAR RESPUESTA ESPECIALIZADA
            respuesta_openai = self._generar_respuesta_especializada(
                mensaje, contexto, estado, tipo_interaccion
            )
            
            # 3. VALIDAR Y MEJORAR
            respuesta_final = self._validar_y_mejorar_respuesta(respuesta_openai, contexto)
            
            return {
                "enhanced": True,
                "message": respuesta_final,
                "tipo_interaccion": tipo_interaccion,
                "method": "openai_cobranza_especializado"
            }
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento OpenAI: {e}")
            return {"enhanced": False, "reason": f"error: {e}"}
    
    def _detectar_tipo_interaccion(self, mensaje: str, contexto: Dict[str, Any], estado: str) -> str:
        """Detecta el tipo de interacción para aplicar prompt específico"""
        
        mensaje_lower = mensaje.lower()
        
        # NEGOCIACIÓN ACTIVA
        if any(palabra in mensaje_lower for palabra in ["opciones", "descuento", "rebaja", "plan", "cuotas"]):
            return "negociacion"
        
        # MANEJO DE OBJECIONES
        elif any(palabra in mensaje_lower for palabra in ["no puedo", "imposible", "muy caro", "no tengo"]):
            return "objecion"
        
        # CIERRE DE ACUERDO
        elif estado in ["generar_acuerdo", "confirmar_plan_elegido"] or "acepto" in mensaje_lower:
            return "cierre"
        
        # SEGUIMIENTO
        elif estado in ["manejo_timeout", "mensaje_reenganche"]:
            return "seguimiento"
        
        # PRESENTACIÓN/INFORMACIÓN
        elif estado in ["informar_deuda", "presentacion", "consultar_deuda_directa"]:
            return "presentacion"
        
        # DEFAULT: Negociación general
        return "negociacion"
    
    def _generar_respuesta_especializada(self, mensaje: str, contexto: Dict[str, Any], 
                                       estado: str, tipo: str) -> str:
        """Genera respuesta usando prompts especializados en cobranza"""
        
        if not self.client:
            raise Exception("Cliente OpenAI no inicializado")
        
        # Extraer datos del contexto
        nombre = contexto.get("Nombre_del_cliente", "Cliente")
        saldo = contexto.get("saldo_total", 0)
        banco = contexto.get("banco", "la entidad financiera")
        oferta_unica = contexto.get("oferta_2", 0)
        cuotas_6 = contexto.get("hasta_6_cuotas", 0)
        
        # Calcular datos adicionales
        ahorro = saldo - oferta_unica if saldo > oferta_unica else 0
        pago_minimo = saldo * 0.1 if saldo > 0 else 0
        
        # Seleccionar prompt base
        if tipo in self.cobranza_prompts:
            prompt_template = self.cobranza_prompts[tipo]
        else:
            prompt_template = self.cobranza_prompts["negociacion"]
        
        # Personalizar prompt
        if tipo == "negociacion":
            prompt_content = prompt_template.format(
                nombre=nombre,
                saldo=saldo,
                banco=banco,
                oferta_unica=oferta_unica,
                ahorro=ahorro,
                cuotas=6,
                valor_cuota=cuotas_6,
                pago_minimo=pago_minimo
            )
        elif tipo == "objecion":
            prompt_content = prompt_template.format(
                nombre=nombre,
                objecion=mensaje
            )
        elif tipo == "cierre":
            prompt_content = prompt_template.format(nombre=nombre)
        elif tipo == "seguimiento":
            prompt_content = prompt_template.format(nombre=nombre)
        else:
            prompt_content = f"Cliente {nombre} en situación: {tipo}. Mensaje: {mensaje}"
        
        # Crear contexto completo
        contexto_completo = f"""DATOS DEL CLIENTE:
- Nombre: {nombre}
- Deuda total: ${saldo:,}
- Banco: {banco}
- Estado conversación: {estado}

OFERTAS DISPONIBLES:
- Pago único: ${oferta_unica:,} (Ahorro: ${ahorro:,})
- Plan 6 cuotas: ${cuotas_6:,} cada una
- Mínimo sugerido: ${pago_minimo:,}

MENSAJE DEL CLIENTE: "{mensaje}"

{prompt_content}

INSTRUCCIONES ADICIONALES:
- Máximo 200 palabras
- Tono profesional pero empático
- Incluir cifras específicas del cliente
- Enfocar en beneficios y soluciones
- Evitar amenazas o presión excesiva

RESPUESTA OPTIMIZADA:"""
        
        # ✅ LLAMAR A OPENAI CON NUEVA API
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.cobranza_prompts["system_base"]},
                    {"role": "user", "content": contexto_completo}
                ],
                temperature=0.7,  # Balance entre creatividad y consistencia
                max_tokens=250,
                # ✅ Eliminar parámetros deprecated
                # presence_penalty=0.1,  # Algunos modelos no soportan esto
                # frequency_penalty=0.1   # Algunos modelos no soportan esto
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Error llamando OpenAI API: {e}")
            # ✅ FALLBACK INTELIGENTE
            return f"Entiendo tu situación, {nombre}. Permíteme revisar las mejores opciones para tu caso. Un asesor te contactará pronto para ofrecerte la mejor solución."
    
    def _validar_y_mejorar_respuesta(self, respuesta: str, contexto: Dict[str, Any]) -> str:
        """Valida y mejora la respuesta de OpenAI"""
        
        if not respuesta or len(respuesta.strip()) < 10:
            return "Permíteme revisar tu situación para ofrecerte la mejor opción."
        
        # Palabras/frases prohibidas en cobranza
        palabras_prohibidas = [
            "amenaza", "demanda", "embargo", "reporte centrales",
            "abogados", "juicio", "consecuencias legales"
        ]
        
        respuesta_lower = respuesta.lower()
        for palabra in palabras_prohibidas:
            if palabra in respuesta_lower:
                logger.warning(f"⚠️ Palabra prohibida detectada: {palabra}")
                return "Estoy aquí para ayudarte a encontrar la mejor solución para tu situación financiera."
        
        # Validar que mantenga información del cliente
        nombre = contexto.get("Nombre_del_cliente", "")
        if nombre and nombre not in respuesta and len(nombre) > 2:
            # Agregar nombre al inicio si no está presente
            respuesta = f"{nombre}, {respuesta}"
        
        # Asegurar que termine con pregunta o call-to-action
        finales_apropiados = ["?", "¿", "contáctame", "conversemos", "te parece"]
        if not any(final in respuesta.lower() for final in finales_apropiados):
            respuesta += " ¿Te gustaría conocer más detalles?"
        
        return respuesta
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del uso de OpenAI"""
        return {
            "service": "OpenAI Cobranza Optimizado v1.0+",
            "disponible": self.disponible,
            "uso_configurado": f"{self.USE_OPENAI_PERCENTAGE}%",
            "prompts_especializados": len(self.cobranza_prompts),
            "tipos_interaccion": ["negociacion", "objecion", "cierre", "seguimiento", "presentacion"],
            "api_key_configured": bool(self.api_key),
            "client_initialized": self.client is not None
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """✅ NUEVO - Test de conexión a OpenAI"""
        if not self.disponible:
            return {
                "success": False,
                "error": "Servicio no disponible",
                "recommendations": [
                    "Verificar OPENAI_API_KEY en .env",
                    "Actualizar librería: pip install --upgrade openai>=1.0.0",
                    "Verificar créditos en OpenAI Dashboard"
                ]
            }
        
        try:
            test_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Responde solo 'OK' si me puedes escuchar"}
                ],
                max_tokens=5,
                temperature=0
            )
            
            if test_response.choices and "ok" in test_response.choices[0].message.content.lower():
                return {
                    "success": True,
                    "message": "Conexión OpenAI exitosa",
                    "model": "gpt-3.5-turbo",
                    "response": test_response.choices[0].message.content
                }
            else:
                return {
                    "success": False,
                    "error": "Respuesta inesperada de OpenAI",
                    "response": test_response.choices[0].message.content if test_response.choices else "No response"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recommendations": [
                    "Verificar API Key",
                    "Revisar créditos OpenAI",
                    "Verificar conectividad"
                ]
            }


# ✅ FACTORY FUNCTION MEJORADA
def crear_openai_cobranza_service() -> OpenAICobranzaService:
    """Factory para crear servicio OpenAI optimizado para cobranza"""
    return OpenAICobranzaService()

# ✅ INSTANCIA GLOBAL CON INICIALIZACIÓN SEGURA
try:
    openai_cobranza_service = OpenAICobranzaService()
    openai_service = openai_cobranza_service  # Alias para compatibilidad
    print("✅ OpenAI Service inicializado globalmente")
except Exception as e:
    print(f"❌ Error inicializando OpenAI Service global: {e}")
    
    # ✅ FALLBACK - Crear servicio dummy
    class DummyOpenAIService:
        def __init__(self):
            self.disponible = False
        
        def should_use_openai(self, *args, **kwargs):
            return False
        
        def procesar_mensaje_cobranza(self, *args, **kwargs):
            return {"enhanced": False, "reason": "service_not_available"}
        
        def get_stats(self):
            return {"service": "OpenAI Dummy", "disponible": False}
        
        def test_connection(self):
            return {"success": False, "error": "Service not initialized"}
    
    openai_cobranza_service = DummyOpenAIService()
    openai_service = openai_cobranza_service