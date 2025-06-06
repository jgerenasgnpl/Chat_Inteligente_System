import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VariableService:
    """Servicio CORREGIDO para resolver variables del sistema"""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache_variables = {}
        self._cache_timestamp = None
        self._cache_duration = 300 
        
    def resolver_variables(self, texto: str, contexto: Dict[str, Any] = None) -> str:
        """
        ✅ VERSIÓN CORREGIDA - Resuelve variables usando contexto PRIMERO, BD después
        
        Args:
            texto: Texto con variables a resolver
            contexto: Contexto con datos del cliente
            
        Returns:
            Texto con variables resueltas
        """
        if not texto:
            return ""
            
        if contexto is None:
            contexto = {}
            
        try:
            print(f"🔧 Resolviendo variables en: {texto[:100]}...")
            print(f"📋 Contexto disponible: {list(contexto.keys())}")
            
            # ✅ PRIORIZAR DATOS DEL CONTEXTO
            datos_combinados = self._combinar_datos_contexto_y_sistema(contexto)
            
            # Buscar y reemplazar variables {{variable}}
            patron = r'\{\{([^}]+)\}\}'
            
            def reemplazar_variable(match):
                nombre_variable = match.group(1).strip()
                valor = self._resolver_variable_individual_corregida(nombre_variable, datos_combinados)
                print(f"   {{{{{nombre_variable}}}}} → {valor}")
                return valor
            
            texto_resuelto = re.sub(patron, reemplazar_variable, texto)
            
            print(f"✅ Variables resueltas correctamente")
            return texto_resuelto
            
        except Exception as e:
            logger.error(f"Error resolviendo variables: {e}")
            print(f"❌ Error resolviendo variables: {e}")
            return texto
    
    def _combinar_datos_contexto_y_sistema(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """✅ NUEVO - Combina datos del contexto con variables del sistema"""
        try:
            # 1. Cargar variables del sistema
            variables_sistema = self._cargar_variables_sistema()
            
            # 2. Extraer datos del contexto
            datos_cliente = {}
            
            # Verificar si hay datos directos en el contexto
            if "Nombre_del_cliente" in contexto:
                datos_cliente.update({
                    "nombre_cliente": contexto.get("Nombre_del_cliente", "Cliente"),
                    "saldo_total": contexto.get("saldo_total", 0),
                    "banco": contexto.get("banco", "Entidad Financiera"),
                    "cedula": contexto.get("cedula_detectada", ""),
                    "capital": contexto.get("capital", 0),
                    "intereses": contexto.get("intereses", 0),
                    "producto": contexto.get("producto", "Producto"),
                    "campana": contexto.get("campana", "General"),
                    "telefono": contexto.get("telefono", ""),
                    "email": contexto.get("email", ""),
                    
                    # ✅ OFERTAS DESDE CONTEXTO
                    "oferta_1": contexto.get("oferta_1", 0),
                    "oferta_2": contexto.get("oferta_2", 0),
                    "oferta_3": contexto.get("oferta_3", 0),
                    "oferta_4": contexto.get("oferta_4", 0),
                    
                    # ✅ CUOTAS DESDE CONTEXTO
                    "hasta_3_cuotas": contexto.get("hasta_3_cuotas", 0),
                    "hasta_6_cuotas": contexto.get("hasta_6_cuotas", 0),
                    "hasta_12_cuotas": contexto.get("hasta_12_cuotas", 0),
                    "hasta_18_cuotas": contexto.get("hasta_18_cuotas", 0),
                })
                
                print(f"✅ Datos del cliente extraídos del contexto:")
                print(f"   Nombre: {datos_cliente.get('nombre_cliente')}")
                print(f"   Saldo: {datos_cliente.get('saldo_total')}")
                print(f"   Ofertas: {datos_cliente.get('oferta_1')}, {datos_cliente.get('oferta_2')}")
                print(f"   Cuotas: {datos_cliente.get('hasta_3_cuotas')}, {datos_cliente.get('hasta_6_cuotas')}")
            
            # 3. Si no hay datos en contexto, intentar obtener cédula para consultar
            elif contexto.get("cedula_detectada"):
                cedula = contexto["cedula_detectada"]
                print(f"🔍 Consultando datos para cédula: {cedula}")
                datos_cliente = self._consultar_todos_datos_cliente(cedula)
            
            # 4. Combinar todo
            datos_finales = {**variables_sistema, **datos_cliente, **contexto}
            
            print(f"🔧 Datos combinados: {len(datos_finales)} variables disponibles")
            return datos_finales
            
        except Exception as e:
            logger.error(f"Error combinando datos: {e}")
            return contexto
    
    def _resolver_variable_individual(self, nombre: str, datos_combinados: Dict[str, Any]) -> str:
        """✅ VERSIÓN CORREGIDA - Resuelve variable individual"""
        
        # 1. Verificar si existe directamente en los datos
        if nombre in datos_combinados:
            valor = datos_combinados[nombre]
            return self._formatear_valor(valor, nombre)
        
        # 2. Mapeo de alias para compatibilidad
        alias_mapping = {
            "cliente_nombre": "nombre_cliente",
            "entidad_financiera": "banco",
            "entidad": "banco",
            "deuda_total": "saldo_total",
            "cedula_cliente": "cedula",
            "cedula_detectada": "cedula",
        }
        
        if nombre in alias_mapping:
            nombre_real = alias_mapping[nombre]
            if nombre_real in datos_combinados:
                valor = datos_combinados[nombre_real]
                return self._formatear_valor(valor, nombre)
        
        # 3. Variables calculadas dinámicamente
        valor_calculado = self._calcular_variable_dinamica_corregida(nombre, datos_combinados)
        if valor_calculado is not None:
            return str(valor_calculado)
        
        # 4. Valor por defecto
        return self._get_valor_por_defecto(nombre)
    
    def _formatear_valor(self, valor: Any, tipo_variable: str) -> str:
        """Formatea un valor según el tipo de variable"""
        try:
            if valor is None:
                return self._get_valor_por_defecto(tipo_variable)
            
            # Variables monetarias
            if any(keyword in tipo_variable.lower() for keyword in 
                   ['saldo', 'oferta', 'capital', 'interes', 'cuota', 'pago', 'monto']):
                return self._formatear_moneda(valor)
            
            # Variables de texto
            return str(valor)
            
        except Exception as e:
            logger.error(f"Error formateando valor {valor}: {e}")
            return str(valor)
    
    def _formatear_moneda(self, valor: Any) -> str:
        """Formatea valor como moneda"""
        try:
            if isinstance(valor, str):
                # Si ya tiene formato de moneda, devolverlo
                if "$" in valor:
                    return valor
                # Intentar convertir string a número
                valor_limpio = valor.replace(",", "").replace("$", "").strip()
                if valor_limpio.replace(".", "").isdigit():
                    valor = float(valor_limpio)
                else:
                    return valor
            
            if isinstance(valor, (int, float)) and valor > 0:
                return f"${valor:,.0f}"
            else:
                return f"${0:,.0f}"
                
        except Exception as e:
            logger.error(f"Error formateando moneda {valor}: {e}")
            return str(valor)
    
    def _calcular_variable_dinamica(self, nombre: str, datos: Dict[str, Any]) -> Optional[str]:
        """✅ VERSIÓN CORREGIDA - Calcula variables dinámicas"""
        try:
            # ===== FECHAS =====
            if nombre == "fecha_limite":
                fecha_limite = datetime.now() + timedelta(days=30)
                return fecha_limite.strftime("%d de %B de %Y")
                
            elif nombre == "fecha_hoy":
                return datetime.now().strftime("%d de %B de %Y")
                
            elif nombre == "mes_actual":
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                return meses[datetime.now().month - 1]
            
            # ===== DESCUENTOS CALCULADOS =====
            elif nombre.startswith("descuento_"):
                saldo = self._extraer_numero(datos.get("saldo_total", 0))
                if "3_cuotas" in nombre:
                    cuotas_val = self._extraer_numero(datos.get("hasta_3_cuotas", 0))
                    if saldo > 0 and cuotas_val > 0:
                        total_cuotas = cuotas_val * 3
                        descuento = ((saldo - total_cuotas) / saldo) * 100
                        return f"{descuento:.0f}%"
                    return "40%"
                elif "6_cuotas" in nombre:
                    cuotas_val = self._extraer_numero(datos.get("hasta_6_cuotas", 0))
                    if saldo > 0 and cuotas_val > 0:
                        total_cuotas = cuotas_val * 6
                        descuento = ((saldo - total_cuotas) / saldo) * 100
                        return f"{descuento:.0f}%"
                    return "30%"
                elif "12_cuotas" in nombre:
                    cuotas_val = self._extraer_numero(datos.get("hasta_12_cuotas", 0))
                    if saldo > 0 and cuotas_val > 0:
                        total_cuotas = cuotas_val * 12
                        descuento = ((saldo - total_cuotas) / saldo) * 100
                        return f"{descuento:.0f}%"
                    return "20%"
            
            # ===== PAGOS ESPECIALES =====
            elif nombre == "pago_flexible":
                saldo = self._extraer_numero(datos.get("saldo_total", 0))
                if saldo > 0:
                    pago = saldo * 0.15  # 15% del saldo
                    return self._formatear_moneda(pago)
                    
            elif nombre == "pago_minimo":
                saldo = self._extraer_numero(datos.get("saldo_total", 0))
                if saldo > 0:
                    pago = saldo * 0.10  # 10% del saldo
                    return self._formatear_moneda(pago)
                    
            elif nombre == "ahorro_maximo":
                saldo = self._extraer_numero(datos.get("saldo_total", 0))
                oferta_1 = self._extraer_numero(datos.get("oferta_1", 0))
                if saldo > 0 and oferta_1 > 0:
                    ahorro = saldo - oferta_1
                    return self._formatear_moneda(ahorro)
                    
            elif nombre == "cuota_mensual":
                # Cuota por defecto en 6 cuotas
                saldo = self._extraer_numero(datos.get("saldo_total", 0))
                if saldo > 0:
                    cuota = saldo / 6
                    return self._formatear_moneda(cuota)
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculando variable {nombre}: {e}")
            return None
    
    def _consultar_todos_datos_cliente(self, cedula: str) -> Dict[str, Any]:
        """✅ NUEVO - Consulta TODOS los datos del cliente de una vez"""
        if not cedula:
            return {}
            
        try:
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Cedula, Telefono, Email,
                    Saldo_total, Capital, Intereses, 
                    Oferta_1, Oferta_2, Oferta_3, Oferta_4,
                    banco, Producto, NumerodeObligacion, Campaña,
                    Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas, Hasta_18_cuotas
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                datos = {
                    "nombre_cliente": result[0] or "Cliente",
                    "cedula": result[1] or cedula,
                    "telefono": result[2] or "",
                    "email": result[3] or "",
                    "saldo_total": float(result[4]) if result[4] else 0,
                    "capital": float(result[5]) if result[5] else 0,
                    "intereses": float(result[6]) if result[6] else 0,
                    "oferta_1": float(result[7]) if result[7] else 0,
                    "oferta_2": float(result[8]) if result[8] else 0,
                    "oferta_3": float(result[9]) if result[9] else 0,
                    "oferta_4": float(result[10]) if result[10] else 0,
                    "banco": result[11] or "Entidad Financiera",
                    "producto": result[12] or "Producto",
                    "numero_obligacion": result[13] or "",
                    "campana": result[14] or "General",
                    "hasta_3_cuotas": float(result[15]) if result[15] else 0,
                    "hasta_6_cuotas": float(result[16]) if result[16] else 0,
                    "hasta_12_cuotas": float(result[17]) if result[17] else 0,
                    "hasta_18_cuotas": float(result[18]) if result[18] else 0,
                }
                
                print(f"✅ Datos completos del cliente consultados desde BD")
                return datos
            else:
                print(f"❌ Cliente con cédula {cedula} no encontrado en BD")
                return {}
                
        except Exception as e:
            logger.error(f"Error consultando cliente {cedula}: {e}")
            return {}
    
    def _cargar_variables_sistema(self) -> Dict[str, str]:
        """Carga variables del sistema desde la base de datos"""
        import time
        current_time = time.time()
        
        if (self._cache_variables and 
            self._cache_timestamp and 
            current_time - self._cache_timestamp < self._cache_duration):
            return self._cache_variables
        
        try:
            query = text("""
                SELECT nombre, valor_por_defecto, formato_visualizacion
                FROM Variables_Sistema
                WHERE activo = 1
                ORDER BY nombre
            """)
            
            result = self.db.execute(query)
            variables = {}
            
            for row in result:
                nombre = row[0]
                valor = row[1] or ""
                formato = row[2] or "{0}"
                
                try:
                    if formato == "{0}":
                        variables[nombre] = str(valor)
                    else:
                        variables[nombre] = formato.format(valor)
                except:
                    variables[nombre] = str(valor)
            
            self._cache_variables = variables
            self._cache_timestamp = current_time
            
            return variables
            
        except Exception as e:
            logger.error(f"Error cargando variables del sistema: {e}")
            return {}
    
    def _extraer_numero(self, valor_str: Any) -> float:
        """Extrae el número de una cadena con formato monetario"""
        if not valor_str:
            return 0.0
            
        try:
            if isinstance(valor_str, (int, float)):
                return float(valor_str)
            
            numero_limpio = str(valor_str).replace('$', '').replace(',', '').replace(' ', '')
            return float(numero_limpio)
        except:
            return 0.0
    
    def _get_valor_por_defecto(self, nombre: str) -> str:
        """Devuelve valor por defecto para variables no encontradas"""
        valores_defecto = {
            "saldo_total": "$0",
            "nombre_cliente": "Cliente", 
            "cliente_nombre": "Cliente",
            "banco": "Entidad Financiera",
            "entidad_financiera": "Entidad Financiera",
            "cedula": "",
            "capital": "$0",
            "intereses": "$0",
            "producto": "Producto",
            "telefono": "",
            "email": "",
            "campana": "General",
            
            # Ofertas
            "oferta_1": "$0",
            "oferta_2": "$0", 
            "oferta_3": "$0",
            "oferta_4": "$0",
            
            # Cuotas
            "hasta_3_cuotas": "$0",
            "hasta_6_cuotas": "$0",
            "hasta_12_cuotas": "$0",
            "hasta_18_cuotas": "$0",
            "cuota_mensual": "$0",
            
            # Pagos especiales
            "pago_flexible": "$0",
            "pago_minimo": "$0",
            "ahorro_maximo": "$0",
            
            # Descuentos
            "descuento_3_cuotas": "40%",
            "descuento_6_cuotas": "30%",
            "descuento_12_cuotas": "20%",
            
            # Fechas
            "fecha_limite": "30 días",
            "fecha_hoy": datetime.now().strftime("%d/%m/%Y"),
            "mes_actual": datetime.now().strftime("%B")
        }
        
        return valores_defecto.get(nombre, f"[{nombre}]")
    
    def probar_variables_con_contexto(self, contexto_prueba: Dict[str, Any]) -> Dict[str, str]:
        """Método para probar resolución de variables"""
        variables_test = [
            "saldo_total", "nombre_cliente", "oferta_1", "oferta_2", 
            "hasta_3_cuotas", "hasta_6_cuotas", "hasta_12_cuotas",
            "descuento_3_cuotas", "pago_flexible", "ahorro_maximo"
        ]
        
        resultados = {}
        for var in variables_test:
            texto_test = f"{{{{{var}}}}}"
            resultado = self.resolver_variables(texto_test, contexto_prueba)
            resultados[var] = resultado
            
        return resultados

def crear_variable_service(db: Session) -> VariableService:
    """Factory para crear instancia corregida del servicio de variables"""
    return VariableService(db)