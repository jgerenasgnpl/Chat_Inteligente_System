import re
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime, timedelta
import hashlib
from app.services.cache_service import cache_service, cache_result

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
        ✅ VERSIÓN CORREGIDA - Resolver variables con consulta fresh forzada
        """
        if not texto:
            return ""
            
        if contexto is None:
            contexto = {}
            
        try:
            print(f"🔧 [RESOLVER] Resolviendo variables en: {texto[:100]}...")
            print(f"📋 [RESOLVER] Contexto disponible: {list(contexto.keys())}")
            
            # ✅ DETECTAR CÉDULA PARA FORZAR CONSULTA FRESH
            cedula = (
                contexto.get("cedula_detectada") or 
                contexto.get("cedula") or
                self._extraer_cedula_contexto(contexto)
            )
            
            # ✅ SI HAY CÉDULA, FORZAR CONSULTA FRESH
            if cedula and len(str(cedula)) >= 7:
                print(f"🔍 [RESOLVER] Cédula detectada: {cedula}, forzando consulta fresh")
                datos_fresh = self._consultar_todos_datos_cliente(str(cedula))
                
                if datos_fresh.get("encontrado", False):
                    print(f"✅ [RESOLVER] Datos fresh obtenidos:")
                    print(f"   Cliente: {datos_fresh.get('Nombre_del_cliente', 'N/A')}")
                    print(f"   Saldo: ${datos_fresh.get('Saldo_total', 0):,.0f}")
                    print(f"   Oferta_2: ${datos_fresh.get('Oferta_2', 0):,.0f}")
                    
                    # COMBINAR datos fresh con contexto existente
                    contexto.update(datos_fresh)
                else:
                    print(f"❌ [RESOLVER] No se encontraron datos fresh para cédula: {cedula}")
            
            # ✅ PRIORIZAR DATOS DEL CONTEXTO
            datos_combinados = self._combinar_datos_contexto_y_sistema_FIXED(contexto)
            
            # Buscar y reemplazar variables {{variable}}
            patron = r'\{\{([^}]+)\}\}'
            
            
            def reemplazar_variable(match):
                nombre_variable = match.group(1).strip()
                valor = self._resolver_variable_individual(nombre_variable, datos_combinados)
                print(f"   🎯 [RESOLVER] {{{{{nombre_variable}}}}} → {valor}")
                return valor
            
            texto_resuelto = re.sub(patron, reemplazar_variable, texto)
            
            print(f"✅ [RESOLVER] Variables resueltas correctamente")
            return texto_resuelto
            
        except Exception as e:
            logger.error(f"❌ [RESOLVER] Error resolviendo variables: {e}")
            print(f"❌ [RESOLVER] Error resolviendo variables: {e}")
            return texto
    
    def _extraer_cedula_contexto(self, contexto: Dict[str, Any]) -> Optional[str]:
        """✅ EXTRAER CÉDULA DEL CONTEXTO"""
        try:
            # Buscar en diferentes campos
            campos_cedula = [
                "cedula_detectada", "cedula", "documento", 
                "Cedula", "cedula_cliente", "user_cedula"
            ]
            
            for campo in campos_cedula:
                valor = contexto.get(campo)
                if valor and len(str(valor)) >= 7:
                    return str(valor)
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extrayendo cédula del contexto: {e}")
            return None

    def _combinar_datos_contexto_y_sistema_FIXED(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """✅ VERSIÓN CORREGIDA - Prioridad ABSOLUTA a datos del cliente"""
        try:
            print(f"🔧 [COMBINAR] Iniciando combinación de datos...")
            
            # 1. Verificar si hay datos REALES del cliente
            tiene_cliente = bool(
                contexto.get("cliente_encontrado") and 
                contexto.get("saldo_total", 0) > 0 and
                contexto.get("Nombre_del_cliente")
            )
            
            print(f"🔧 [COMBINAR] Cliente encontrado resultado: {tiene_cliente}")
            
            if tiene_cliente:
                print(f"✅ [COMBINAR] USANDO DATOS REALES DEL CLIENTE")
                
                # ✅ USAR SOLO DATOS REALES - NO MEZCLAR CON SISTEMA
                datos_finales = contexto.copy()  # ✅ PRIORIDAD ABSOLUTA AL CONTEXTO
                
                # Solo agregar valores por defecto para campos vacíos
                if not datos_finales.get("banco"):
                    datos_finales["banco"] = "Entidad Financiera"
                    
                return datos_finales
            else:
                print(f"⚠️ [COMBINAR] Sin datos reales - usando sistema por defecto")
                variables_sistema = self._cargar_variables_sistema()
                return {**variables_sistema, **contexto}
                
        except Exception as e:
            print(f"❌ [COMBINAR] Error: {e}")
            return contexto
    
    def _consulta_directa_bd(self, cedula: str) -> Optional[Dict[str, Any]]:
        """✅ NUEVO - Consulta directa a BD cuando faltan datos"""
        try:
            if not cedula:
                return None
                
            print(f"🔍 [CONSULTA_DIRECTA] Consultando BD para cédula: {cedula}")
            
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente, Saldo_total, 
                    Oferta_1, Oferta_2,
                    Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas,
                    banco
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                datos = {
                    "nombre": result[0] or "Cliente",
                    "saldo": int(float(result[1])) if result[1] else 0,
                    "oferta_1": int(float(result[2])) if result[2] else 0,
                    "oferta_2": int(float(result[3])) if result[3] else 0,
                    "cuotas_3": int(float(result[4])) if result[4] else 0,
                    "cuotas_6": int(float(result[5])) if result[5] else 0,
                    "cuotas_12": int(float(result[6])) if result[6] else 0,
                    "banco": result[7] or "Entidad Financiera"
                }
                
                print(f"✅ [CONSULTA_DIRECTA] Datos obtenidos de BD:")
                print(f"   Nombre: {datos['nombre']}")
                print(f"   Saldo: ${datos['saldo']:,}")
                print(f"   Oferta_2: ${datos['oferta_2']:,}")
                
                return datos
            
            print(f"❌ [CONSULTA_DIRECTA] No se encontraron datos para cédula: {cedula}")
            return None
            
        except Exception as e:
            print(f"❌ [CONSULTA_DIRECTA] Error: {e}")
            return None

    def _extraer_cedula_contexto(self, contexto: Dict[str, Any]) -> Optional[str]:
        """✅ MEJORADO - Extraer cédula del contexto con múltiples fuentes"""
        try:
            # ✅ BUSCAR EN MÚLTIPLES CAMPOS
            campos_cedula = [
                "cedula_detectada", "cedula", "documento", 
                "Cedula", "CEDULA", "cedula_cliente", "user_cedula",
                "numero_documento", "doc", "identification"
            ]
            
            for campo in campos_cedula:
                valor = contexto.get(campo)
                if valor and len(str(valor)) >= 7:
                    cedula_str = str(valor).strip()
                    if cedula_str.isdigit() and 7 <= len(cedula_str) <= 12:
                        print(f"✅ [EXTRAER_CEDULA] Cédula encontrada en campo '{campo}': {cedula_str}")
                        return cedula_str
            
            # ✅ BUSCAR EN VALORES ANIDADOS
            for key, value in contexto.items():
                if isinstance(value, (str, int)) and len(str(value)) >= 7:
                    valor_str = str(value).strip()
                    if valor_str.isdigit() and 7 <= len(valor_str) <= 12:
                        print(f"✅ [EXTRAER_CEDULA] Cédula encontrada en valor '{key}': {valor_str}")
                        return valor_str
            
            print(f"❌ [EXTRAER_CEDULA] No se encontró cédula en contexto")
            print(f"❌ [EXTRAER_CEDULA] Campos disponibles: {list(contexto.keys())}")
            return None
            
        except Exception as e:
            print(f"⚠️ [EXTRAER_CEDULA] Error extrayendo cédula: {e}")
            return None

    def _convertir_a_entero(self, valor):
        """✅ MEJORADO - Convierte valor a entero manejando Decimal y otros tipos"""
        try:
            if valor is None or valor == "":
                return 0
            
            # ✅ MANEJAR TIPO DECIMAL ESPECÍFICAMENTE
            from decimal import Decimal
            if isinstance(valor, Decimal):
                return int(valor)
            
            # Si ya es entero
            if isinstance(valor, int):
                return valor
                
            # Si es string, limpiar y convertir
            if isinstance(valor, str):
                # Remover caracteres no numéricos excepto punto y coma
                valor_limpio = re.sub(r'[^\d.,]', '', str(valor))
                if valor_limpio:
                    # Manejar decimales y comas
                    valor_limpio = valor_limpio.replace(',', '')
                    return int(float(valor_limpio))
                return 0
                
            # Si es float
            if isinstance(valor, float):
                return int(valor)
                
            # ✅ CUALQUIER OTRO TIPO NUMÉRICO
            try:
                return int(float(str(valor)))
            except:
                return 0
                
        except (ValueError, TypeError) as e:
            print(f"⚠️ Error convirtiendo '{valor}' a entero: {e}")
            return 0
        
    def _obtener_oferta_directa_bd(self, cedula: str) -> Optional[int]:
        """Consulta directa a BD para obtener oferta correcta"""
        try:
            if not cedula:
                return None
                
            from sqlalchemy import text
            from app.db.session import engine
            
            query = text("""
                SELECT TOP 1 Oferta_2
                FROM [turnosvirtuales_dev].[dbo].[ConsolidadoCampañasNatalia]
                WHERE Cedula = :cedula
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {"cedula": cedula})
                row = result.fetchone()
                if row and row[0]:
                    return self._convertir_a_entero(row[0])
            
            return None
        except Exception as e:
            logger.error(f"❌ Error consultando oferta directa: {e}")
            return None
    
    def _resolver_variable_individual(self, nombre: str, datos_combinados: Dict[str, Any]) -> str:
        """✅ CORREGIDO: Resolución robusta de variables"""
        
        print(f"🔧 [VARIABLE] Resolviendo: {{{{{nombre}}}}}")
        
        # 1. Verificación directa
        if nombre in datos_combinados:
            valor = datos_combinados[nombre]
            try:
                valor_formateado = self._formatear_valor_sin_decimales(valor, nombre)
                print(f"✅ [VARIABLE] {nombre} directo: {valor} → {valor_formateado}")
                return valor_formateado
            except Exception as e:
                print(f"⚠️ Error formateando {nombre}: {e}")
                return str(valor) if valor is not None else ""
        
        # 2. Mapeo de alias críticos
        alias_mapping = {
            "oferta_2": ["Oferta_2", "OFERTA_2", "oferta_especial_2"],
            "Oferta_2": ["oferta_2", "OFERTA_2", "oferta_especial_2"],
            "nombre_cliente": ["Nombre_del_cliente", "cliente_nombre"],
            "Nombre_del_cliente": ["nombre_cliente", "cliente_nombre"],
            "saldo_total": ["Saldo_total", "SALDO_TOTAL", "saldo"]
        }
        
        if nombre in alias_mapping:
            for alias in alias_mapping[nombre]:
                if alias in datos_combinados:
                    valor = datos_combinados[alias]
                    try:
                        valor_formateado = self._formatear_valor_sin_decimales(valor, nombre)
                        print(f"✅ [VARIABLE] {nombre} via alias {alias}: {valor} → {valor_formateado}")
                        return valor_formateado
                    except Exception as e:
                        print(f"⚠️ Error formateando alias {alias}: {e}")
        
        # 3. Búsqueda case-insensitive
        for key, value in datos_combinados.items():
            if key.lower() == nombre.lower():
                try:
                    valor_formateado = self._formatear_valor_sin_decimales(value, nombre)
                    print(f"✅ [VARIABLE] {nombre} case-insensitive: {valor_formateado}")
                    return valor_formateado
                except Exception as e:
                    print(f"⚠️ Error en case-insensitive: {e}")
        
        # 4. Valor por defecto
        valor_defecto = self._get_valor_por_defecto(nombre)
        print(f"❌ [VARIABLE] {nombre} NO ENCONTRADO - usando defecto: {valor_defecto}")
        return valor_defecto

# =========================================
# NUEVO MÉTODO: _formatear_valor_sin_decimales
# =========================================
    def _formatear_valor_sin_decimales(self, valor: Any, tipo_variable: str) -> str:
        """✅ FORMATEAR VALOR SIN DECIMALES"""
        try:
            if valor is None:
                return self._get_valor_por_defecto(tipo_variable)
            
            # Variables monetarias - FORMATO SIN DECIMALES
            if any(keyword in tipo_variable.lower() for keyword in 
                ['saldo', 'oferta', 'capital', 'interes', 'cuota', 'pago', 'monto']):
                return self._formatear_moneda_sin_decimales(valor)
            
            # Variables de texto
            return str(valor)
            
        except Exception as e:
            logger.error(f"❌ Error formateando valor {valor}: {e}")
            return str(valor)

# =========================================
# NUEVO MÉTODO: _formatear_moneda_sin_decimales
# =========================================

    def _formatear_moneda_sin_decimales(self, valor: Any) -> str:
        """✅ FORMATEAR MONEDA SIN DECIMALES"""
        try:
            if isinstance(valor, str):
                # Si ya tiene formato de moneda, re-formatear sin decimales
                if "$" in valor:
                    valor_limpio = valor.replace(",", "").replace("$", "").strip()
                    if "." in valor_limpio:
                        valor_limpio = valor_limpio.split(".")[0]  # Remover decimales
                    valor = float(valor_limpio) if valor_limpio else 0
                else:
                    valor = float(valor.replace(",", "").strip()) if valor else 0
            
            if isinstance(valor, (int, float)) and valor > 0:
                # ✅ FORMATO SIN DECIMALES
                return f"${int(valor):,}"
            else:
                return f"${0:,}"
                
        except Exception as e:
            logger.error(f"❌ Error formateando moneda {valor}: {e}")
            return str(valor)
    
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
        """✅ CONSULTA CORREGIDA - Campos exactos de la BD"""
        if not cedula:
            return {}
            
        try:
            # ✅ USAR NOMBRES EXACTOS DE LA BD
            query = text("""
                SELECT TOP 1 
                    Nombre_del_cliente,
                    Cedula,
                    Saldo_total,
                    Oferta_1,
                    Oferta_2,        -- ✅ NOMBRE EXACTO DE LA BD
                    Oferta_3,
                    Oferta_4,
                    banco,
                    Producto,
                    Hasta_3_cuotas,
                    Hasta_6_cuotas,
                    Hasta_12_cuotas,
                    Hasta_18_cuotas,
                    Capital,
                    Intereses,
                    Telefono,
                    Email
                FROM ConsolidadoCampañasNatalia 
                WHERE CAST(Cedula AS VARCHAR) = :cedula
                ORDER BY Saldo_total DESC
            """)
            
            result = self.db.execute(query, {"cedula": str(cedula)}).fetchone()
            
            if result:
                # ✅ MAPEO CORRECTO CON LOGS DE VERIFICACIÓN
                datos = {
                    "encontrado": True,
                    "nombre_cliente": result[0] or "Cliente",
                    "Nombre_del_cliente": result[0] or "Cliente",  # ✅ AMBOS FORMATOS
                    "cedula_detectada": result[1] or cedula,
                    "saldo_total": int(float(result[2])) if result[2] else 0,
                    
                    # ✅ OFERTAS CON NOMBRES CORRECTOS
                    "oferta_1": int(float(result[3])) if result[3] else 0,
                    "oferta_2": int(float(result[4])) if result[4] else 0,  # ✅ CRÍTICO
                    "Oferta_2": int(float(result[4])) if result[4] else 0,  # ✅ ALIAS
                    "oferta_3": int(float(result[5])) if result[5] else 0,
                    "oferta_4": int(float(result[6])) if result[6] else 0,
                    
                    "banco": result[7] or "Entidad Financiera",
                    "producto": result[8] or "Producto",
                    
                    # ✅ CUOTAS
                    "hasta_3_cuotas": int(float(result[9])) if result[9] else 0,
                    "hasta_6_cuotas": int(float(result[10])) if result[10] else 0,
                    "hasta_12_cuotas": int(float(result[11])) if result[11] else 0,
                    "hasta_18_cuotas": int(float(result[12])) if result[12] else 0,
                    
                    "capital": int(float(result[13])) if result[13] else 0,
                    "intereses": int(float(result[14])) if result[14] else 0,
                    "telefono": result[15] or "",
                    "email": result[16] or "",
                    
                    # ✅ METADATA
                    "cliente_encontrado": True,
                    "consulta_timestamp": datetime.now().isoformat()
                }
                
                # ✅ LOG DE VERIFICACIÓN CRÍTICO
                print(f"✅ CONSULTA BD EXITOSA:")
                print(f"   Cliente: {datos['nombre_cliente']}")
                print(f"   Saldo: ${datos['saldo_total']:,}")
                print(f"   Oferta_1: ${datos['oferta_1']:,}")
                print(f"   Oferta_2: ${datos['oferta_2']:,}")  # ✅ VERIFICAR
                print(f"   Banco: {datos['banco']}")
                
                return datos
            else:
                print(f"❌ Cliente no encontrado para cédula: {cedula}")
                return {"encontrado": False}
                
        except Exception as e:
            print(f"❌ Error consultando cliente {cedula}: {e}")
            return {"encontrado": False, "error": str(e)}
    
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

class VariableServiceWithCache(VariableService):
    """Variable Service con Redis Cache"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.cache = cache_service
    
    def resolver_variables(self, texto: str, contexto: Dict[str, Any] = None) -> str:
        """Resolución de variables con cache"""
        
        if not texto:
            return ""
        
        if contexto is None:
            contexto = {}
        
        # 1. Generar hash del contexto
        context_hash = self._generate_context_hash(contexto)
        
        # 2. Verificar cache
        cached_result = self.cache.get_cached_resolved_variables(texto, context_hash)
        if cached_result:
            logger.debug(f"🎯 Variables Cache HIT")
            return cached_result
        
        # 3. Resolver variables normalmente
        logger.debug(f"💾 Variables Cache MISS - resolviendo")
        result = super().resolver_variables(texto, contexto)
        
        # 4. Guardar en cache
        self.cache.cache_resolved_variables(texto, context_hash, result, ttl=1800)  # 30 minutos
        logger.debug(f"💾 Variables resueltas guardadas en cache")
        
        return result
    
    def _generate_context_hash(self, contexto: Dict[str, Any]) -> str:
        """Generar hash del contexto para cache de variables"""
        # Solo elementos relevantes para variables
        relevant_fields = [
            "Nombre_del_cliente", "saldo_total", "banco", 
            "oferta_1", "oferta_2", "hasta_3_cuotas", 
            "hasta_6_cuotas", "hasta_12_cuotas"
        ]
        
        relevant_context = {
            field: contexto.get(field) 
            for field in relevant_fields 
            if field in contexto
        }
        
        context_str = json.dumps(relevant_context, sort_keys=True, default=str)
        return hashlib.md5(context_str.encode()).hexdigest()[:16]
    
    def _consultar_todos_datos_cliente(self, cedula: str) -> Dict[str, Any]:
        """Consulta con invalidación de cache"""
        
        # Si hay datos frescos, invalidar cache
        result = super()._consultar_todos_datos_cliente(cedula)
        
        if result.get("encontrado"):
            # Invalidar cache del cliente para forzar actualización
            self.cache.invalidate_client_cache(cedula)
            logger.debug(f"🗑️ Cache cliente {cedula} invalidado por consulta fresh")
        
        return result
    
def crear_variable_service(db: Session) -> VariableService:
    """Factory para crear instancia corregida del servicio de variables"""
    return VariableService(db)