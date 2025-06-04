import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VariableService:
    """Servicio para resolver variables del sistema"""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache_variables = {}
        self._cache_timestamp = None
        self._cache_duration = 300 
        
    def resolver_variables(self, texto: str, contexto: Dict[str, Any] = None) -> str:
        """
        Resuelve todas las variables {{variable}} en un texto
        
        Args:
            texto: Texto con variables a resolver
            contexto: Contexto adicional con valores específicos
            
        Returns:
            Texto con variables resueltas
        """
        if not texto:
            return ""
            
        if contexto is None:
            contexto = {}
            
        try:
            # Cargar variables del sistema
            variables_sistema = self._cargar_variables_sistema()
            
            # Combinar variables del sistema con contexto
            todas_las_variables = {**variables_sistema, **contexto}
            
            # Buscar y reemplazar variables {{variable}}
            patron = r'\{\{([^}]+)\}\}'
            
            def reemplazar_variable(match):
                nombre_variable = match.group(1).strip()
                return self._resolver_variable_individual(nombre_variable, todas_las_variables)
            
            texto_resuelto = re.sub(patron, reemplazar_variable, texto)
            
            logger.debug(f"Variables resueltas: {texto[:50]}... -> {texto_resuelto[:50]}...")
            return texto_resuelto
            
        except Exception as e:
            logger.error(f"Error resolviendo variables: {e}")
            # Devolver texto original si hay error
            return texto
    
    def _cargar_variables_sistema(self) -> Dict[str, str]:
        """Carga variables del sistema desde la base de datos"""
        
        # Verificar cache
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
                
                # Aplicar formato si es necesario
                try:
                    if formato == "{0}":
                        variables[nombre] = str(valor)
                    elif "${" in formato:
                        # Formato monetario
                        valor_numerico = float(valor) if valor.replace('.', '').replace(',', '').isdigit() else 0
                        variables[nombre] = formato.format(valor_numerico)
                    elif "%" in formato:
                        # Formato porcentaje
                        valor_numerico = float(valor) if valor.replace('.', '').isdigit() else 0
                        variables[nombre] = formato.format(valor_numerico)
                    else:
                        variables[nombre] = formato.format(valor)
                        
                except (ValueError, TypeError):
                    variables[nombre] = str(valor)
            
            # Actualizar cache
            self._cache_variables = variables
            self._cache_timestamp = current_time
            
            logger.info(f"Variables del sistema cargadas: {len(variables)}")
            return variables
            
        except Exception as e:
            logger.error(f"Error cargando variables del sistema: {e}")
            return {}
    
    def _resolver_variable_individual(self, nombre: str, variables: Dict[str, Any]) -> str:
        """Resuelve una variable individual"""
        
        # Verificar si la variable existe
        if nombre in variables:
            valor = variables[nombre]
            logger.debug(f"Variable {nombre} resuelta: {valor}")
            return str(valor)
        
        # Variables calculadas dinámicamente
        valor_calculado = self._calcular_variable_dinamica(nombre, variables)
        if valor_calculado is not None:
            return str(valor_calculado)
        
        # Si no se encuentra, devolver placeholder o valor por defecto
        logger.warning(f"Variable no encontrada: {nombre}")
        return self._get_valor_por_defecto(nombre)
    
    def _calcular_variable_dinamica(self, nombre: str, contexto: Dict[str, Any]) -> Optional[str]:
        """Calcula variables dinámicas basadas en lógica de negocio"""
        
        try:
            # Obtener cédula para consultar BD
            cedula = contexto.get("cedula", contexto.get("cedula_detectada", ""))
            
            # Obtener datos base del cliente
            cliente_info = contexto.get("cliente", {})
            if isinstance(cliente_info, dict):
                nombre_cliente = cliente_info.get("nombre", "Cliente")
                campana = cliente_info.get("campana", "General")
                banco = cliente_info.get("banco", "Entidad Financiera")
            else:
                nombre_cliente = "Cliente"
                campana = "General"
                banco = "Entidad Financiera"
            
            # ===== VARIABLES BÁSICAS =====
            if nombre == "saldo_total":
                return self._consultar_campo_cliente(cedula, "Saldo_total")
                
            elif nombre == "nombre_cliente" or nombre == "cliente_nombre":
                return self._consultar_campo_cliente(cedula, "Nombre_del_cliente") or nombre_cliente
                
            elif nombre == "entidad_financiera" or nombre == "banco":
                return self._consultar_campo_cliente(cedula, "banco") or banco
                
            elif nombre == "campana":
                return self._consultar_campo_cliente(cedula, "Campaña") or campana
                
            elif nombre == "cedula":
                return str(cedula)
            
            # ===== OFERTAS DE PAGO (CONSULTAR DE BD) =====
            elif nombre == "oferta_1":
                return self._consultar_campo_cliente(cedula, "Oferta_1")
                
            elif nombre == "oferta_2":
                return self._consultar_campo_cliente(cedula, "Oferta_2")
                
            elif nombre == "oferta_3":
                return self._consultar_campo_cliente(cedula, "Oferta_3")
                
            elif nombre == "oferta_4":
                return self._consultar_campo_cliente(cedula, "Oferta_4")
            
            # ===== VALORES DE CUOTAS (CONSULTAR DE BD) =====
            elif nombre == "hasta_3_cuotas":
                return self._consultar_campo_cliente(cedula, "Hasta_3_cuotas")
                
            elif nombre == "hasta_6_cuotas":
                return self._consultar_campo_cliente(cedula, "Hasta_6_cuotas")
                
            elif nombre == "hasta_12_cuotas":
                return self._consultar_campo_cliente(cedula, "Hasta_12_cuotas")
                
            elif nombre == "hasta_18_cuotas":
                return self._consultar_campo_cliente(cedula, "Hasta_18_cuotas")
            
            # ===== OTROS CAMPOS DE BD =====
            elif nombre == "capital":
                return self._consultar_campo_cliente(cedula, "Capital")
                
            elif nombre == "intereses":
                return self._consultar_campo_cliente(cedula, "Intereses")
                
            elif nombre == "producto":
                return self._consultar_campo_cliente(cedula, "Producto")
                
            elif nombre == "telefono":
                return self._consultar_campo_cliente(cedula, "Telefono")
                
            elif nombre == "ultimos_digitos":
                return self._consultar_campo_cliente(cedula, "Ultimos_digitos")
            
            # ===== DESCUENTOS CALCULADOS (si no están en BD) =====
            elif nombre == "descuento_3_cuotas":
                return self._calcular_descuento_cuotas(cedula, 3)
                
            elif nombre == "descuento_6_cuotas":
                return self._calcular_descuento_cuotas(cedula, 6)
                
            elif nombre == "descuento_12_cuotas":
                return self._calcular_descuento_cuotas(cedula, 12)
            
            # ===== FECHAS =====
            elif nombre == "fecha_limite":
                # Fecha límite: 30 días desde hoy
                fecha_limite = datetime.now() + timedelta(days=30)
                return fecha_limite.strftime("%d de %B de %Y")
                
            elif nombre == "fecha_hoy":
                return datetime.now().strftime("%d de %B de %Y")
                
            elif nombre == "mes_actual":
                meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                return meses[datetime.now().month - 1]
            
            # ===== VARIABLES DE NEGOCIACIÓN CALCULADAS =====
            elif nombre == "pago_flexible":
                # Pago inicial flexible: 10% del saldo
                saldo_str = self._consultar_campo_cliente(cedula, "Saldo_total")
                if saldo_str:
                    saldo = self._extraer_numero(saldo_str)
                    pago = saldo * 0.10
                    return self._formatear_moneda(pago)
                return self._get_valor_por_defecto(nombre)
                
            elif nombre == "pago_minimo":
                # Pago mínimo: 10% del saldo
                saldo_str = self._consultar_campo_cliente(cedula, "Saldo_total")
                if saldo_str:
                    saldo = self._extraer_numero(saldo_str)
                    pago = saldo * 0.1
                    return self._formatear_moneda(pago)
                return self._get_valor_por_defecto(nombre)
                
            elif nombre == "ahorro_maximo":
                # Calcular ahorro máximo basado en ofertas reales
                saldo_str = self._consultar_campo_cliente(cedula, "Saldo_total")
                oferta1_str = self._consultar_campo_cliente(cedula, "Oferta_1")
                if saldo_str and oferta1_str:
                    saldo = self._extraer_numero(saldo_str)
                    oferta = self._extraer_numero(oferta1_str)
                    ahorro = saldo - oferta
                    return self._formatear_moneda(ahorro)
                return self._get_valor_por_defecto(nombre)
            
            # ===== VARIABLES DE CONTEXTO =====
            elif nombre == "descuento_disponible":
                # Descuento por defecto
                descuento = contexto.get('descuento', 40)
                return f"{descuento}%"
                
            elif nombre == "cuota_mensual":
                # Cuota mensual genérica (6 cuotas por defecto)
                cuotas = int(contexto.get("num_cuotas", 6))
                saldo_str = self._consultar_campo_cliente(cedula, "Saldo_total")
                if saldo_str:
                    saldo = self._extraer_numero(saldo_str)
                    cuota = saldo / cuotas
                    return self._formatear_moneda(cuota)
                return self._get_valor_por_defecto(nombre)
                
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.error(f"Error calculando variable {nombre}: {e}")
            
        return None
    
    def _consultar_campo_cliente(self, cedula: str, campo: str) -> Optional[str]:
        """
        Consulta un campo específico del cliente en la tabla ConsolidadoCampañasNatalia
        
        Args:
            cedula: Cédula del cliente
            campo: Nombre del campo a consultar
            
        Returns:
            Valor del campo formateado, None si no se encuentra
        """
        if not cedula or not campo:
            return None
            
        try:
            # Query para obtener el campo específico
            query = text(f"""
                SELECT TOP 1 [{campo}]
                FROM ConsolidadoCampañasNatalia 
                WHERE Cedula = :cedula
            """)
            
            result = self.db.execute(query, {"cedula": cedula})
            row = result.fetchone()
            
            if row and row[0] is not None:
                valor = row[0]
                
                # Formatear según el tipo de campo
                if campo in ["Saldo_total", "Capital", "Intereses", "Oferta_1", "Oferta_2", "Oferta_3", "Oferta_4", 
                           "Hasta_3_cuotas", "Hasta_6_cuotas", "Hasta_12_cuotas", "Hasta_18_cuotas"]:
                    # Campos monetarios
                    if isinstance(valor, (int, float)):
                        return self._formatear_moneda(float(valor))
                    elif isinstance(valor, str) and valor.replace('.', '').replace(',', '').isdigit():
                        return self._formatear_moneda(float(valor.replace(',', '')))
                    else:
                        return str(valor)
                else:
                    # Campos de texto
                    return str(valor).strip()
                    
            return None
            
        except Exception as e:
            logger.error(f"Error consultando campo {campo} para cédula {cedula}: {e}")
            return None
    
    def _calcular_descuento_cuotas(self, cedula: str, num_cuotas: int) -> str:
        """
        Calcula el descuento basado en los valores reales de BD
        
        Args:
            cedula: Cédula del cliente
            num_cuotas: Número de cuotas
            
        Returns:
            Porcentaje de descuento
        """
        try:
            saldo_str = self._consultar_campo_cliente(cedula, "Saldo_total")
            cuota_str = self._consultar_campo_cliente(cedula, f"Hasta_{num_cuotas}_cuotas")
            
            if saldo_str and cuota_str:
                saldo = self._extraer_numero(saldo_str)
                cuota = self._extraer_numero(cuota_str)
                
                if saldo > 0 and cuota > 0:
                    total_a_pagar = cuota * num_cuotas
                    descuento = ((saldo - total_a_pagar) / saldo) * 100
                    return f"{descuento:.0f}%"
                    
        except Exception as e:
            logger.error(f"Error calculando descuento para {num_cuotas} cuotas: {e}")
            
        # Valores por defecto si no se puede calcular
        descuentos_defecto = {3: "40%", 6: "30%", 12: "20%"}
        return descuentos_defecto.get(num_cuotas, "15%")
    
    def _extraer_numero(self, valor_str: str) -> float:
        """
        Extrae el número de una cadena con formato monetario
        
        Args:
            valor_str: String con formato como "$1,234.56" o "1234.56"
            
        Returns:
            Valor numérico float
        """
        if not valor_str:
            return 0.0
            
        try:
            # Remover símbolos monetarios y espacios
            numero_limpio = str(valor_str).replace('$', '').replace(',', '').replace(' ', '')
            return float(numero_limpio)
        except (ValueError, TypeError):
            return 0.0
    
    def _formatear_moneda(self, valor: float) -> str:
        """Formatea un valor como moneda colombiana"""
        try:
            # Formatear como peso colombiano
            return f"${valor:,.0f}"
        except:
            return f"${valor}"
    
    def _get_valor_por_defecto(self, nombre: str) -> str:
        """Devuelve valor por defecto para variables no encontradas"""
        
        valores_defecto = {
            # Variables básicas
            "saldo_total": "$0",
            "nombre_cliente": "Cliente",
            "cliente_nombre": "Cliente",
            "entidad_financiera": "Entidad Financiera",
            "banco": "Entidad Financiera",
            "campana": "General",
            "cedula": "",
            "capital": "$0",
            "intereses": "$0",
            "producto": "Producto",
            "telefono": "",
            "ultimos_digitos": "",
            
            # Ofertas (serán consultadas de BD)
            "oferta_1": "$0",
            "oferta_2": "$0",
            "oferta_3": "$0",
            "oferta_4": "$0",
            
            # Descuentos (calculados dinámicamente)
            "descuento_3_cuotas": "40%",
            "descuento_6_cuotas": "30%",
            "descuento_12_cuotas": "20%",
            "descuento_disponible": "40%",
            
            # Cuotas (serán consultadas de BD)
            "hasta_3_cuotas": "$0",
            "hasta_6_cuotas": "$0",
            "hasta_12_cuotas": "$0",
            "hasta_18_cuotas": "$0",
            "cuota_mensual": "$0",
            
            # Pagos calculados
            "pago_flexible": "$0",
            "pago_minimo": "$0",
            "ahorro_maximo": "$0",
            
            # Fechas
            "fecha_limite": "30 días",
            "fecha_hoy": datetime.now().strftime("%d/%m/%Y"),
            "mes_actual": datetime.now().strftime("%B")
        }
        
        return valores_defecto.get(nombre, f"[{nombre}]")
    
    def registrar_variable_contexto(self, nombre: str, valor: Any, conversation_id: int):
        """Registra una variable en el contexto de la conversación"""
        try:
            # Aquí podrías guardar variables específicas de conversación
            # Por ahora solo logueamos
            logger.info(f"Variable contexto registrada: {nombre}={valor} para conversación {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error registrando variable contexto: {e}")
    
    def obtener_variables_disponibles(self) -> Dict[str, str]:
        """Obtiene lista de todas las variables disponibles"""
        try:
            variables_sistema = self._cargar_variables_sistema()
            
            # Agregar variables dinámicas
            variables_dinamicas = {
                # Variables básicas
                "saldo_total": "Saldo total de la deuda",
                "nombre_cliente": "Nombre del cliente",
                "cliente_nombre": "Nombre del cliente (alias)",
                "entidad_financiera": "Entidad financiera",
                "banco": "Banco (alias)",
                "campana": "Campaña actual",
                "cedula": "Cédula del cliente detectada",
                "capital": "Capital de la deuda",
                "intereses": "Intereses de la deuda",
                "producto": "Producto financiero",
                "telefono": "Teléfono del cliente",
                "ultimos_digitos": "Últimos dígitos de la cuenta",
                
                # Ofertas de pago único
                "oferta_1": "Oferta 1 de pago único",
                "oferta_2": "Oferta 2 de pago único",
                "oferta_3": "Oferta 3 de pago único",
                "oferta_4": "Oferta 4 de pago único",
                
                # Descuentos por cuotas
                "descuento_3_cuotas": "Descuento para 3 cuotas",
                "descuento_6_cuotas": "Descuento para 6 cuotas",
                "descuento_12_cuotas": "Descuento para 12 cuotas",
                
                # Valores de cuotas
                "hasta_3_cuotas": "Valor cuota en plan 3 cuotas",
                "hasta_6_cuotas": "Valor cuota en plan 6 cuotas", 
                "hasta_12_cuotas": "Valor cuota en plan 12 cuotas",
                "hasta_18_cuotas": "Valor cuota en plan 18 cuotas",
                "cuota_mensual": "Cuota mensual estimada",
                
                # Pagos especiales
                "pago_flexible": "Pago inicial flexible (15%)",
                "pago_minimo": "Pago mínimo requerido (10%)",
                "ahorro_maximo": "Máximo ahorro disponible",
                
                # Fechas
                "fecha_limite": "Fecha límite de la oferta",
                "fecha_hoy": "Fecha actual",
                "mes_actual": "Mes actual",
                
                # Variables de contexto
                "descuento_disponible": "Descuento disponible"
            }
            
            return {**variables_sistema, **variables_dinamicas}
            
        except Exception as e:
            logger.error(f"Error obteniendo variables disponibles: {e}")
            return {}
    
    def probar_variables(self, contexto_prueba: Dict[str, Any] = None) -> Dict[str, str]:
        """Método para probar resolución de variables (útil para debugging)"""
        if contexto_prueba is None:
            contexto_prueba = {
                "cedula_detectada": "1020428633",  # Cédula de ejemplo
                "cliente": {
                    "nombre": "JONATHAN RAMIREZ",
                    "campana": "Campaña Test"
                }
            }
        
        variables_test = [
            "saldo_total", "nombre_cliente", "oferta_1", "oferta_2", "oferta_3",
            "hasta_3_cuotas", "hasta_6_cuotas", "hasta_12_cuotas",
            "descuento_3_cuotas", "descuento_6_cuotas", 
            "fecha_limite", "pago_flexible", "ahorro_maximo",
            "capital", "intereses", "producto"
        ]
        
        resultados = {}
        cedula = contexto_prueba.get("cedula_detectada", "")
        
        logger.info(f"Probando variables para cédula: {cedula}")
        
        for var in variables_test:
            texto_test = f"{{{{{var}}}}}"
            resultado = self.resolver_variables(texto_test, contexto_prueba)
            resultados[var] = resultado
            logger.debug(f"Variable {var}: {resultado}")
            
        return resultados
    
    def probar_con_cedula(self, cedula: str) -> Dict[str, str]:
        """
        Probar variables con una cédula específica
        
        Args:
            cedula: Cédula del cliente a probar
            
        Returns:
            Diccionario con resultados de las variables
        """
        contexto = {
            "cedula_detectada": cedula,
            "cliente": {
                "nombre": "Cliente Test"
            }
        }
        
        return self.probar_variables(contexto)

def crear_variable_service(db: Session) -> VariableService:
    """Factory para crear instancia del servicio de variables"""
    return VariableService(db)