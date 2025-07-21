import re
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VariableService:
    """✅ SERVICIO DE VARIABLES 100% DINÁMICO - SIN VALORES HARDCODEADOS"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def resolver_variables(self, texto: str, contexto: Dict[str, Any] = None) -> str:
        """✅ RESOLVER VARIABLES COMPLETAMENTE DINÁMICO"""
        if not texto:
            return ""
            
        if contexto is None:
            contexto = {}
            
        try:
            logger.info(f"🔧 [RESOLVER] Resolviendo variables dinámicamente")
            
            # ✅ VERIFICAR SI HAY DATOS REALES DEL CLIENTE
            tiene_datos_reales = (
                contexto.get("cliente_encontrado", False) and 
                contexto.get("saldo_total", 0) > 0 and
                contexto.get("Nombre_del_cliente")
            )
            
            if not tiene_datos_reales:
                logger.info(f"⚠️ [RESOLVER] Sin datos reales del cliente - usando texto base")
                return self._resolver_sin_datos_cliente(texto)
            
            logger.info(f"✅ [RESOLVER] Datos reales disponibles:")
            logger.info(f"   Cliente: {contexto.get('Nombre_del_cliente')}")
            logger.info(f"   Saldo: ${contexto.get('saldo_total', 0):,}")
            
            # ✅ RESOLVER CON DATOS REALES
            patron = r'\{\{([^}]+)\}\}'
            
            def reemplazar_variable(match):
                nombre_variable = match.group(1).strip()
                valor = self._resolver_variable_real(nombre_variable, contexto)
                logger.info(f"   🎯 [RESOLVER] {{{{{nombre_variable}}}}} → {valor}")
                return valor
            
            texto_resuelto = re.sub(patron, reemplazar_variable, texto)
            logger.info(f"✅ [RESOLVER] Variables resueltas con datos reales")
            return texto_resuelto
            
        except Exception as e:
            logger.error(f"❌ [RESOLVER] Error: {e}")
            return texto
    
    def _resolver_sin_datos_cliente(self, texto: str) -> str:
        """✅ RESOLVER CUANDO NO HAY DATOS REALES"""
        try:
            # ✅ ELIMINAR VARIABLES NO RESUELTAS EN LUGAR DE USAR VALORES HARDCODEADOS
            patron = r'\{\{([^}]+)\}\}'
            
            def reemplazar_variable_vacia(match):
                nombre_variable = match.group(1).strip()
                
                # ✅ VARIABLES QUE PUEDEN TENER VALORES GENÉRICOS
                if nombre_variable in ["Nombre_del_cliente", "nombre_cliente"]:
                    return "Cliente"
                elif "fecha" in nombre_variable.lower():
                    return self._get_fecha_dinamica(nombre_variable)
                else:
                    # ✅ ELIMINAR VARIABLES SIN DATOS EN LUGAR DE HARDCODEAR
                    return ""
            
            texto_limpio = re.sub(patron, reemplazar_variable_vacia, texto)
            
            # ✅ LIMPIAR LÍNEAS VACÍAS RESULTANTES
            lineas = texto_limpio.split('\n')
            lineas_limpias = []
            
            for linea in lineas:
                linea_limpia = linea.strip()
                # ✅ ELIMINAR LÍNEAS QUE SOLO TIENEN SIGNOS $ O ESTÁN VACÍAS
                if linea_limpia and not re.match(r'^[\$\s\:]+$', linea_limpia):
                    lineas_limpias.append(linea_limpia)
            
            resultado = '\n'.join(lineas_limpias)
            
            # ✅ SI EL RESULTADO ESTÁ VACÍO, DAR MENSAJE GENÉRICO
            if not resultado.strip():
                return "Para continuar, necesito tu número de cédula."
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error resolviendo sin datos: {e}")
            return "Para ayudarte, proporciona tu número de cédula."
    
    def _resolver_variable_real(self, nombre: str, contexto: Dict[str, Any]) -> str:
        """✅ RESOLVER VARIABLE CON DATOS REALES ÚNICAMENTE"""
        
        # ✅ 1. VERIFICACIÓN DIRECTA
        if nombre in contexto:
            valor = contexto[nombre]
            if valor is not None and valor != 0:
                return self._formatear_valor_dinamico(valor, nombre)
        
        # ✅ 2. MAPEO DE ALIAS
        alias_mapping = {
            "oferta_2": ["Oferta_2", "OFERTA_2"],
            "Oferta_2": ["oferta_2", "OFERTA_2"],
            "nombre_cliente": ["Nombre_del_cliente"],
            "Nombre_del_cliente": ["nombre_cliente"],
            "saldo_total": ["Saldo_total"]
        }
        
        if nombre in alias_mapping:
            for alias in alias_mapping[nombre]:
                if alias in contexto and contexto[alias] is not None and contexto[alias] != 0:
                    valor = contexto[alias]
                    return self._formatear_valor_dinamico(valor, nombre)
        
        # ✅ 3. BÚSQUEDA CASE-INSENSITIVE
        for key, value in contexto.items():
            if key.lower() == nombre.lower() and value is not None and value != 0:
                return self._formatear_valor_dinamico(value, nombre)
        
        # ✅ 4. VARIABLES CALCULADAS DINÁMICAMENTE
        valor_calculado = self._calcular_variable_dinamica(nombre, contexto)
        if valor_calculado:
            return valor_calculado
        
        # ✅ 5. SIN VALOR - DEVOLVER VACÍO (NO HARDCODEADO)
        logger.warning(f"❌ [VARIABLE] {nombre} no encontrado - devolviendo vacío")
        return ""
    
    def _formatear_valor_dinamico(self, valor: Any, tipo_variable: str) -> str:
        """✅ FORMATEAR VALOR DINÁMICAMENTE"""
        try:
            if valor is None or valor == 0:
                return ""
            
            # ✅ VARIABLES MONETARIAS
            if any(keyword in tipo_variable.lower() for keyword in 
                ['saldo', 'oferta', 'capital', 'interes', 'cuota', 'pago', 'monto']):
                return self._formatear_moneda_dinamica(valor)
            
            # ✅ VARIABLES DE TEXTO
            return str(valor).strip()
            
        except Exception as e:
            logger.error(f"❌ Error formateando valor {valor}: {e}")
            return str(valor) if valor else ""
    
    def _formatear_moneda_dinamica(self, valor: Any) -> str:
        """✅ FORMATEAR MONEDA SIN VALORES HARDCODEADOS"""
        try:
            if isinstance(valor, str):
                if "$" in valor:
                    valor_limpio = valor.replace(",", "").replace("$", "").strip()
                    if "." in valor_limpio:
                        valor_limpio = valor_limpio.split(".")[0]
                    valor = float(valor_limpio) if valor_limpio else 0
                else:
                    valor = float(valor.replace(",", "").strip()) if valor else 0
            
            # ✅ SOLO FORMATEAR SI HAY VALOR REAL
            if isinstance(valor, (int, float)) and valor > 0:
                return f"${int(valor):,}"
            else:
                return ""  # ✅ VACÍO EN LUGAR DE $0
                
        except Exception as e:
            logger.error(f"❌ Error formateando moneda {valor}: {e}")
            return ""
    
    def _calcular_variable_dinamica(self, nombre: str, datos: Dict[str, Any]) -> Optional[str]:
        """✅ CALCULAR VARIABLES DINÁMICAMENTE SOLO CON DATOS REALES"""
        try:
            # ✅ FECHAS (SIEMPRE DISPONIBLES)
            if nombre == "fecha_limite":
                fecha_limite = datetime.now() + timedelta(days=30)
                return fecha_limite.strftime("%d de %B de %Y")
                
            elif nombre == "fecha_hoy":
                return datetime.now().strftime("%d de %B de %Y")
            
            # ✅ CÁLCULOS SOLO SI HAY DATOS REALES
            saldo = datos.get("saldo_total", 0)
            if saldo <= 0:
                return None  # ✅ NO CALCULAR SIN DATOS REALES
            
            # ✅ DESCUENTOS CALCULADOS CON DATOS REALES
            if nombre.startswith("descuento_"):
                if "3_cuotas" in nombre:
                    cuotas_val = datos.get("hasta_3_cuotas", 0)
                    if cuotas_val > 0:
                        total_cuotas = cuotas_val * 3
                        descuento = ((saldo - total_cuotas) / saldo) * 100
                        return f"{descuento:.0f}%"
                elif "6_cuotas" in nombre:
                    cuotas_val = datos.get("hasta_6_cuotas", 0)
                    if cuotas_val > 0:
                        total_cuotas = cuotas_val * 6
                        descuento = ((saldo - total_cuotas) / saldo) * 100
                        return f"{descuento:.0f}%"
            
            # ✅ PAGOS CALCULADOS CON DATOS REALES
            elif nombre == "pago_flexible":
                pago = saldo * 0.15
                return self._formatear_moneda_dinamica(pago)
                
            elif nombre == "pago_minimo":
                pago = saldo * 0.10
                return self._formatear_moneda_dinamica(pago)
                
            elif nombre == "ahorro_maximo":
                oferta_1 = datos.get("oferta_1", 0)
                if oferta_1 > 0:
                    ahorro = saldo - oferta_1
                    return self._formatear_moneda_dinamica(ahorro)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculando variable {nombre}: {e}")
            return None
    
    def _get_fecha_dinamica(self, nombre_variable: str) -> str:
        """✅ OBTENER FECHAS DINÁMICAS"""
        if nombre_variable == "fecha_limite":
            fecha_limite = datetime.now() + timedelta(days=30)
            return fecha_limite.strftime("%d de %B de %Y")
        elif nombre_variable == "fecha_hoy":
            return datetime.now().strftime("%d de %B de %Y")
        elif nombre_variable == "mes_actual":
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            return meses[datetime.now().month - 1]
        else:
            return ""
    
    def consultar_cliente_directo(self, cedula: str) -> Dict[str, Any]:
        """✅ NUEVO - Consulta directa de cliente para variables"""
        try:
            if not cedula:
                return {}
                
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
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                return {
                    "cliente_encontrado": True,
                    "Nombre_del_cliente": result[0],
                    "saldo_total": int(float(result[1])) if result[1] else 0,
                    "banco": result[2],
                    "oferta_1": int(float(result[3])) if result[3] else 0,
                    "oferta_2": int(float(result[4])) if result[4] else 0,
                    "hasta_3_cuotas": int(float(result[5])) if result[5] else 0,
                    "hasta_6_cuotas": int(float(result[6])) if result[6] else 0,
                    "hasta_12_cuotas": int(float(result[7])) if result[7] else 0,
                    "producto": result[8],
                    "telefono": result[9],
                    "email": result[10]
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error consultando cliente directo: {e}")
            return {}

def crear_variable_service(db: Session) -> VariableService:
    """Factory para crear instancia corregida del servicio de variables"""
    return VariableService(db)