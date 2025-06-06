import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

class OpenAIService:
    """Servicio para integración con OpenAI GPT"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.disponible = False
        
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                self.disponible = True
                logger.info("✅ OpenAI Service inicializado correctamente")
            except ImportError:
                logger.warning("⚠️ OpenAI library no instalada. Instalar con: pip install openai")
            except Exception as e:
                logger.error(f"❌ Error inicializando OpenAI: {e}")
        else:
            logger.warning("⚠️ OPENAI_API_KEY no encontrada en variables de entorno")
    
    def humanizar_respuesta(self, mensaje_original: str, contexto: Dict[str, Any]) -> str:
        """
        Humaniza una respuesta usando GPT
        
        Args:
            mensaje_original: Mensaje a humanizar
            contexto: Contexto de la conversación
            
        Returns:
            Mensaje humanizado o mensaje original si hay error
        """
        if not self.disponible or not self.client:
            logger.debug("OpenAI no disponible, devolviendo mensaje original")
            return mensaje_original
        
        try:
            # Extraer información del contexto
            nombre = contexto.get("Nombre_del_cliente", contexto.get("nombre_cliente", "Cliente"))
            banco = contexto.get("banco", "Entidad Financiera")
            saldo = contexto.get("saldo_total", 0)
            estado = contexto.get("estado_actual", "negociación")
            intencion = contexto.get("intencion_detectada", "")
            
            # Crear prompt optimizado para cobranza
            prompt = self._crear_prompt_cobranza(mensaje_original, {
                "nombre": nombre,
                "banco": banco, 
                "saldo": saldo,
                "estado": estado,
                "intencion": intencion
            })
            
            # Llamar a GPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un asistente de negociación de deudas profesional, empático y efectivo. Tu objetivo es ayudar a los clientes a encontrar soluciones de pago viables manteniendo un tono amigable pero profesional."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=400,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            mensaje_humanizado = response.choices[0].message.content.strip()
            
            # Validar que la respuesta sea apropiada
            if self._validar_respuesta(mensaje_humanizado):
                logger.info(f"🤖 GPT humanizó mensaje exitosamente")
                return mensaje_humanizado
            else:
                logger.warning("⚠️ Respuesta GPT no pasó validación, usando original")
                return mensaje_original
                
        except Exception as e:
            logger.error(f"❌ Error humanizando con GPT: {e}")
            return mensaje_original
    
    def _crear_prompt_cobranza(self, mensaje: str, contexto: Dict[str, Any]) -> str:
        """Crea prompt optimizado para cobranza"""
        
        nombre = contexto.get("nombre", "Cliente")
        banco = contexto.get("banco", "Entidad Financiera")
        saldo = contexto.get("saldo", 0)
        estado = contexto.get("estado", "negociación")
        intencion = contexto.get("intencion", "")
        
        # Formatear saldo
        if isinstance(saldo, (int, float)) and saldo > 0:
            saldo_formatted = f"${saldo:,.0f}"
        elif isinstance(saldo, str) and "$" in saldo:
            saldo_formatted = saldo
        else:
            saldo_formatted = "un monto pendiente"
        
        prompt = f"""
Humaniza este mensaje de negociación de deudas manteniendo la información clave:

MENSAJE ORIGINAL:
{mensaje}

CONTEXTO DEL CLIENTE:
- Nombre: {nombre}
- Entidad: {banco}
- Saldo: {saldo_formatted}
- Estado conversación: {estado}
- Intención detectada: {intencion}

INSTRUCCIONES:
1. Mantén toda la información específica (montos, opciones, descuentos)
2. Usa un tono empático pero profesional
3. Personaliza con el nombre del cliente cuando sea apropiado
4. Mantén las opciones numeradas si existen
5. Conserva emojis y formato si ayudan a la claridad
6. NO inventes información nueva
7. Máximo 300 palabras
8. Enfócate en soluciones, no en problemas

RESPUESTA HUMANIZADA:"""
        
        return prompt
    
    def _validar_respuesta(self, respuesta: str) -> bool:
        """Valida que la respuesta GPT sea apropiada"""
        if not respuesta or len(respuesta.strip()) < 10:
            return False
        
        # Palabras/frases que no deberían aparecer
        palabras_prohibidas = [
            "no puedo ayudar",
            "lo siento, no puedo",
            "asistente de ia",
            "modelo de lenguaje",
            "openai",
            "gpt"
        ]
        
        respuesta_lower = respuesta.lower()
        for palabra in palabras_prohibidas:
            if palabra in respuesta_lower:
                return False
        
        return True
    
    def detectar_intencion_avanzada(self, mensaje: str, contexto: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Detecta intención usando GPT (complemento al ML)
        
        Args:
            mensaje: Mensaje del usuario
            contexto: Contexto opcional
            
        Returns:
            Diccionario con intención detectada y confianza
        """
        if not self.disponible:
            return {"intencion": "DESCONOCIDA", "confianza": 0.0, "metodo": "gpt_no_disponible"}
        
        try:
            prompt = f"""
Analiza la intención del siguiente mensaje en el contexto de cobranza/negociación:

MENSAJE: "{mensaje}"

Clasifica en una de estas categorías:
- CONSULTA_DEUDA: Cliente pregunta por su deuda
- INTENCION_PAGO: Cliente quiere pagar o conocer opciones
- SOLICITUD_PLAN: Cliente busca plan de pagos o descuentos
- CONFIRMACION: Cliente acepta o confirma algo
- RECHAZO: Cliente rechaza o no puede pagar
- OBJECION: Cliente pone excusas o dificultades
- IDENTIFICACION: Cliente proporciona datos personales
- SALUDO: Saludos o inicio de conversación
- DESPEDIDA: Cliente se despide
- DESCONOCIDA: No se puede clasificar

Responde SOLO con: CATEGORIA|CONFIANZA_0_A_1|RAZON_BREVE

Ejemplo: SOLICITUD_PLAN|0.85|Cliente menciona cuotas y descuentos
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de intenciones para cobranza. Responde solo en el formato solicitado."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            resultado = response.choices[0].message.content.strip()
            partes = resultado.split("|")
            
            if len(partes) >= 3:
                return {
                    "intencion": partes[0].strip(),
                    "confianza": float(partes[1].strip()),
                    "razon": partes[2].strip(),
                    "metodo": "gpt"
                }
            
        except Exception as e:
            logger.error(f"Error en detección GPT: {e}")
        
        return {"intencion": "DESCONOCIDA", "confianza": 0.0, "metodo": "gpt_error"}
    
    def generar_respuesta_empatica(self, situacion_cliente: str, contexto: Dict[str, Any]) -> str:
        """
        Genera respuesta empática para situaciones difíciles
        
        Args:
            situacion_cliente: Descripción de la situación (ej: "sin trabajo")
            contexto: Contexto del cliente
            
        Returns:
            Respuesta empática personalizada
        """
        if not self.disponible:
            return "Entiendo tu situación. ¿Te gustaría que exploremos opciones flexibles que se adapten a tu capacidad actual?"
        
        try:
            nombre = contexto.get("Nombre_del_cliente", "")
            saldo = contexto.get("saldo_total", 0)
            
            prompt = f"""
El cliente {nombre} está en una situación difícil: {situacion_cliente}
Tiene una deuda de {saldo} y necesita una respuesta empática pero constructiva.

Genera una respuesta que:
1. Muestre empatía genuina por su situación
2. Ofrezca esperanza y soluciones
3. Proponga alternativas flexibles
4. Mantenga profesionalismo
5. Máximo 150 palabras
6. Evite sonar robótica o artificial

Situación del cliente: {situacion_cliente}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un consejero financiero empático especializado en encontrar soluciones para personas en dificultades económicas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando respuesta empática: {e}")
            return "Entiendo tu situación. Estoy aquí para ayudarte a encontrar una solución que funcione para ti."

# Instancia global del servicio
openai_service = OpenAIService()

def crear_openai_service() -> OpenAIService:
    """Factory para crear instancia del servicio OpenAI"""
    return openai_service