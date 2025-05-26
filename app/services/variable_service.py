"""
Servicio para manejar variables del sistema - VERSIÓN CORREGIDA
"""

import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class VariableService:
    """Servicio para resolver variables del sistema"""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache_variables = {}
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutos
        
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
            if nombre == "saldo_total":
                # Obtener saldo real del contexto o BD
                return self._formatear_moneda(contexto.get("saldo", 15000))
                
            elif nombre == "oferta_2":
                saldo = float(contexto.get("saldo", 15000))
                oferta = saldo * 0.5  # 50% de descuento para plan 2 cuotas
                return self._formatear_moneda(oferta)
                
            elif nombre == "pago_flexible":
                saldo = float(contexto.get("saldo", 15000))
                pago = saldo * 0.15  # 15% como pago inicial
                return self._formatear_moneda(pago)
                
            elif nombre == "cliente_nombre":
                return contexto.get("nombre_cliente", "Cliente")
                
            elif nombre == "entidad_financiera":
                return contexto.get("entidad", "Entidad Financiera")
                
            elif nombre == "descuento_disponible":
                return f"{contexto.get('descuento', 15)}%"
                
            elif nombre == "cuota_mensual":
                saldo = float(contexto.get("saldo", 15000))
                cuotas = int(contexto.get("num_cuotas", 6))
                cuota = saldo / cuotas
                return self._formatear_moneda(cuota)
                
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.error(f"Error calculando variable {nombre}: {e}")
            
        return None
    
    def _formatear_moneda(self, valor: float) -> str:
        """Formatea un valor como moneda"""
        try:
            return f"${valor:,.0f}"
        except:
            return f"${valor}"
    
    def _get_valor_por_defecto(self, nombre: str) -> str:
        """Devuelve valor por defecto para variables no encontradas"""
        
        valores_defecto = {
            "saldo_total": "$15,000",
            "oferta_2": "$7,500", 
            "pago_flexible": "$2,250",
            "cliente_nombre": "Cliente",
            "entidad_financiera": "Entidad Financiera",
            "descuento_disponible": "15%",
            "cuota_mensual": "$2,500"
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
                "saldo_total": "Saldo total de la deuda",
                "oferta_2": "Oferta plan 2 cuotas", 
                "pago_flexible": "Pago inicial flexible",
                "cliente_nombre": "Nombre del cliente",
                "entidad_financiera": "Entidad financiera",
                "descuento_disponible": "Descuento disponible",
                "cuota_mensual": "Cuota mensual estimada"
            }
            
            return {**variables_sistema, **variables_dinamicas}
            
        except Exception as e:
            logger.error(f"Error obteniendo variables disponibles: {e}")
            return {}

def crear_variable_service(db: Session) -> VariableService:
    """Factory para crear instancia del servicio de variables"""
    return VariableService(db)