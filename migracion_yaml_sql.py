# migracion_yaml_sql.py
"""
Script para migrar base_conocimiento.yaml a las tablas SQL
UBICACIÓN: Al mismo nivel que main.py
EJECUTAR: python migracion_yaml_sql.py

REQUISITOS:
1. Tener instalado: pip install sqlalchemy pyodbc pyyaml
2. Configurar DATABASE_URL abajo
3. Tener base_conocimiento.yaml en el mismo directorio
4. Haber creado las tablas SQL primero
"""

import yaml
import json
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from datetime import datetime
import urllib.parse

# Agregar el directorio del proyecto al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ===============================================
# CONFIGURACIÓN DE BASE DE DATOS - CORREGIDA
# ===============================================

# Configuración de conexión a SQL Server
SERVER = "172.18.79.20,1433"
DATABASE = "turnosvirtuales_dev"
TRUSTED_CONNECTION = True  # Si usas autenticación de Windows
USERNAME = None  # Solo si no usas Trusted_Connection
PASSWORD = None  # Solo si no usas Trusted_Connection

def crear_session():
    """Crea sesión de base de datos"""
    try:
        if TRUSTED_CONNECTION:
            # Conexión con autenticación de Windows
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SERVER};"
                f"DATABASE={DATABASE};"
                f"Trusted_Connection=yes;"
            )
            # URL encode la cadena de conexión
            params = urllib.parse.quote_plus(connection_string)
            database_url = f"mssql+pyodbc:///?odbc_connect={params}"
            
        else:
            # Conexión con usuario y contraseña
            if not USERNAME or not PASSWORD:
                raise ValueError("Se requiere USERNAME y PASSWORD si no se usa Trusted_Connection")
            
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={SERVER};"
                f"DATABASE={DATABASE};"
                f"UID={USERNAME};"
                f"PWD={PASSWORD};"
            )
            params = urllib.parse.quote_plus(connection_string)
            database_url = f"mssql+pyodbc:///?odbc_connect={params}"
        
        print(f"🔗 Conectando a: {SERVER}/{DATABASE}")
        
        # Crear engine con configuración optimizada
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False  # Cambiar a True para debug SQL
        )
        
        # Probar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
        
    except Exception as e:
        print(f"❌ Error creando sesión de BD: {e}")
        print("💡 Verificaciones:")
        print(f"   - Servidor accesible: {SERVER}")
        print(f"   - Base de datos existe: {DATABASE}")
        print(f"   - ODBC Driver 17 instalado")
        print(f"   - Permisos de acceso correctos")
        raise

class MigradorYamlSQL:
    """
    Migra base_conocimiento.yaml a tablas SQL
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.estados_migrados = 0
        self.errores = []
    
    def ejecutar_migracion_completa(self):
        """
        Migración completa del YAML a SQL
        """
        print("🚀 INICIANDO MIGRACIÓN YAML → SQL")
        print("="*50)
        
        try:
            # 1. Verificar que existan las tablas
            if not self._verificar_tablas():
                print("❌ Faltan tablas necesarias. Ejecuta primero el SQL de creación de tablas.")
                return False
            
            # 2. Cargar YAML
            print("📋 Cargando base_conocimiento.yaml...")
            with open("base_conocimiento.yaml", "r", encoding="utf-8") as f:
                kb = yaml.safe_load(f)
            
            print(f"✅ YAML cargado con {len(kb)} elementos")
            
            # 3. Migrar cada sección
            self._migrar_estados(kb)
            self._migrar_variables_sistema(kb.get('variables', {}))
            self._migrar_metadatos(kb.get('metadatos', {}))
            
            # 4. Verificar migración
            self._verificar_migracion_exitosa()
            
            print("\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print(f"📊 Estados migrados: {self.estados_migrados}")
            if self.errores:
                print(f"⚠️ Errores encontrados: {len(self.errores)}")
                for error in self.errores:
                    print(f"   - {error}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error crítico durante migración: {e}")
            self.db.rollback()
            return False
    
    def _verificar_tablas(self) -> bool:
        """Verifica que existan las tablas necesarias"""
        tablas_requeridas = [
            'Estados_Conversacion', 
            'Opciones_Estado', 
            'Variables_Sistema',
            'Configuracion_Global'
        ]
        
        try:
            tablas_encontradas = []
            tablas_faltantes = []
            
            for tabla in tablas_requeridas:
                query = text("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = :tabla_nombre
                """)
                
                resultado = self.db.execute(query, {"tabla_nombre": tabla}).scalar()
                if resultado > 0:
                    tablas_encontradas.append(tabla)
                else:
                    tablas_faltantes.append(tabla)
            
            print(f"✅ Tablas encontradas: {len(tablas_encontradas)}")
            for tabla in tablas_encontradas:
                print(f"   ✓ {tabla}")
            
            if tablas_faltantes:
                print(f"❌ Tablas faltantes: {len(tablas_faltantes)}")
                for tabla in tablas_faltantes:
                    print(f"   ✗ {tabla}")
                return False
            
            print("✅ Todas las tablas requeridas existen")
            return True
            
        except Exception as e:
            print(f"❌ Error verificando tablas: {e}")
            return False
    
    def verificar_nombres_tablas(self):
        """Verifica los nombres correctos de las tablas existentes"""
        try:
            query = text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND TABLE_NAME IN ('conversation', 'conversations', 'messages', 'message')
                ORDER BY TABLE_NAME
            """)
            
            resultado = self.db.execute(query).fetchall()
            print("📋 Tablas de conversación encontradas:")
            for tabla in resultado:
                print(f"   - {tabla[0]}")
            
            return resultado
            
        except Exception as e:
            print(f"❌ Error verificando tablas: {e}")
            return []
    
    def _migrar_estados(self, kb: dict):
        """Migra estados de conversación"""
        print("📋 Migrando estados de conversación...")
        
        for estado_nombre, estado_config in kb.items():
            # Saltar metadatos y variables
            if estado_nombre in ['metadatos', 'variables', 'fin']:
                continue
                
            if not isinstance(estado_config, dict):
                continue
            
            try:
                # Preparar datos del estado
                mensaje_template = estado_config.get('message', '')
                accion = estado_config.get('action')
                condicion = estado_config.get('condition')
                
                # Determinar estados siguientes
                estado_siguiente_true = estado_config.get('true_next')
                estado_siguiente_false = estado_config.get('false_next')
                estado_siguiente_default = estado_config.get('next')
                
                # Insertar/actualizar estado
                upsert_estado = text("""
                    IF NOT EXISTS (SELECT 1 FROM Estados_Conversacion WHERE nombre = :nombre)
                    BEGIN
                        INSERT INTO Estados_Conversacion (
                            nombre, mensaje_template, accion, condicion,
                            estado_siguiente_true, estado_siguiente_false, 
                            estado_siguiente_default, activo
                        )
                        VALUES (:nombre, :mensaje, :accion, :condicion,
                                :true_next, :false_next, :default_next, 1)
                    END
                    ELSE
                    BEGIN
                        UPDATE Estados_Conversacion 
                        SET mensaje_template = :mensaje,
                            accion = :accion,
                            condicion = :condicion,
                            estado_siguiente_true = :true_next,
                            estado_siguiente_false = :false_next,
                            estado_siguiente_default = :default_next,
                            fecha_actualizacion = GETDATE()
                        WHERE nombre = :nombre
                    END
                """)
                
                self.db.execute(upsert_estado, {
                    "nombre": estado_nombre,
                    "mensaje": mensaje_template,
                    "accion": accion,
                    "condicion": condicion,
                    "true_next": estado_siguiente_true,
                    "false_next": estado_siguiente_false,
                    "default_next": estado_siguiente_default
                })
                
                # Migrar opciones específicas si existen
                self._migrar_opciones_estado(estado_nombre, estado_config)
                
                self.estados_migrados += 1
                print(f"   ✅ {estado_nombre}")
                
            except Exception as e:
                error_msg = f"Error migrando estado {estado_nombre}: {e}"
                self.errores.append(error_msg)
                print(f"   ❌ {error_msg}")
        
        self.db.commit()
        print(f"✅ {self.estados_migrados} estados migrados exitosamente")
    
    def _migrar_opciones_estado(self, estado_nombre: str, estado_config: dict):
        """Migra opciones/botones de estados específicos"""
        
        # Estados que tienen opciones predefinidas
        if estado_nombre == "proponer_planes_pago":
            opciones = [
                {"id": "1", "texto": "Pago único con descuento", "orden": 1},
                {"id": "2", "texto": "Plan en 2 cuotas sin interés", "orden": 2},
                {"id": "3", "texto": "Plan en 6 cuotas", "orden": 3}
            ]
            
            for opcion in opciones:
                insert_opcion = text("""
                    IF NOT EXISTS (SELECT 1 FROM Opciones_Estado 
                                  WHERE estado_nombre = :estado AND opcion_id = :opcion_id)
                    BEGIN
                        INSERT INTO Opciones_Estado (
                            estado_nombre, opcion_id, texto_boton, orden_visualizacion, activo
                        )
                        VALUES (:estado, :opcion_id, :texto, :orden, 1)
                    END
                """)
                
                self.db.execute(insert_opcion, {
                    "estado": estado_nombre,
                    "opcion_id": opcion["id"],
                    "texto": opcion["texto"],
                    "orden": opcion["orden"]
                })
        
        # Migrar opciones dinámicas del YAML si existen
        if "options" in estado_config:
            orden = 1
            for opcion_key, opcion_data in estado_config["options"].items():
                insert_opcion = text("""
                    IF NOT EXISTS (SELECT 1 FROM Opciones_Estado 
                                  WHERE estado_nombre = :estado AND opcion_id = :opcion_id)
                    BEGIN
                        INSERT INTO Opciones_Estado (
                            estado_nombre, opcion_id, texto_boton, estado_destino, orden_visualizacion, activo
                        )
                        VALUES (:estado, :opcion_id, :texto, :destino, :orden, 1)
                    END
                """)
                
                self.db.execute(insert_opcion, {
                    "estado": estado_nombre,
                    "opcion_id": opcion_key,
                    "texto": opcion_key.replace("_", " ").title(),
                    "destino": opcion_data.get("next", estado_nombre),
                    "orden": orden
                })
                orden += 1
    
    def _migrar_variables_sistema(self, variables: dict):
        """Migra variables del sistema"""
        print("🔧 Migrando variables del sistema...")
        
        variables_migradas = 0
        
        for variable, valor_default in variables.items():
            try:
                # Determinar formato basado en el nombre
                formato = self._determinar_formato_variable(variable)
                
                insert_variable = text("""
                    IF NOT EXISTS (SELECT 1 FROM Variables_Sistema WHERE nombre = :nombre)
                    BEGIN
                        INSERT INTO Variables_Sistema (
                            nombre, formato_visualizacion, valor_por_defecto, descripcion
                        )
                        VALUES (:nombre, :formato, :valor_default, :descripcion)
                    END
                    ELSE
                    BEGIN
                        UPDATE Variables_Sistema
                        SET formato_visualizacion = :formato,
                            valor_por_defecto = :valor_default,
                            descripcion = :descripcion
                        WHERE nombre = :nombre
                    END
                """)
                
                self.db.execute(insert_variable, {
                    "nombre": variable,
                    "formato": formato,
                    "valor_default": str(valor_default),
                    "descripcion": f"Variable migrada desde YAML: {variable}"
                })
                
                variables_migradas += 1
                
            except Exception as e:
                error_msg = f"Error migrando variable {variable}: {e}"
                self.errores.append(error_msg)
        
        print(f"✅ {variables_migradas} variables migradas")
    
    def _migrar_metadatos(self, metadatos: dict):
        """Migra metadatos como configuración global"""
        print("📊 Migrando metadatos...")
        
        parametros_migrados = 0
        
        # Migrar información del sector
        if "sector" in metadatos:
            self._insertar_config_global("sector_negocio", metadatos["sector"], "Sector de negocio del sistema")
            parametros_migrados += 1
        
        if "producto" in metadatos:
            self._insertar_config_global("tipo_producto", metadatos["producto"], "Tipo de producto manejado")
            parametros_migrados += 1
        
        if "estrategia" in metadatos:
            self._insertar_config_global("estrategia_cobranza", metadatos["estrategia"], "Estrategia de cobranza empleada")
            parametros_migrados += 1
        
        # Migrar KPIs como JSON
        if "kpis" in metadatos:
            kpis_json = json.dumps(metadatos["kpis"])
            self._insertar_config_global("kpis_sistema", kpis_json, "KPIs del sistema en formato JSON", "json")
            parametros_migrados += 1
        
        # Migrar variables clave como JSON
        if "variables_clave" in metadatos:
            variables_json = json.dumps(metadatos["variables_clave"])
            self._insertar_config_global("variables_clave", variables_json, "Variables clave del sistema en formato JSON", "json")
            parametros_migrados += 1
        
        print(f"✅ {parametros_migrados} parámetros de configuración migrados")
    
    def _insertar_config_global(self, parametro: str, valor: str, descripcion: str, tipo: str = "string"):
        """Inserta parámetro en configuración global"""
        try:
            insert_config = text("""
                IF NOT EXISTS (SELECT 1 FROM Configuracion_Global WHERE nombre_parametro = :parametro)
                BEGIN
                    INSERT INTO Configuracion_Global (
                        nombre_parametro, valor, tipo_dato, descripcion, activo
                    )
                    VALUES (:parametro, :valor, :tipo, :descripcion, 1)
                END
                ELSE
                BEGIN
                    UPDATE Configuracion_Global 
                    SET valor = :valor, 
                        tipo_dato = :tipo,
                        descripcion = :descripcion,
                        fecha_actualizacion = GETDATE()
                    WHERE nombre_parametro = :parametro
                END
            """)
            
            self.db.execute(insert_config, {
                "parametro": parametro,
                "valor": valor,
                "tipo": tipo,
                "descripcion": descripcion
            })
            
        except Exception as e:
            self.errores.append(f"Error insertando config {parametro}: {e}")
    
    def _determinar_formato_variable(self, nombre_variable: str) -> str:
        """Determina el formato de visualización de una variable"""
        nombre_lower = nombre_variable.lower()
        
        if any(x in nombre_lower for x in ["saldo", "oferta", "capital", "monto", "valor"]):
            return "${:,.0f}"
        elif "fecha" in nombre_lower:
            return "%d/%m/%Y"
        elif "porcentaje" in nombre_lower or "%" in nombre_lower:
            return "{:.1f}%"
        else:
            return "{0}"  # Formato simple
    
    def _verificar_migracion_exitosa(self):
        """Verifica que la migración fue exitosa"""
        print("🔍 Verificando migración...")
        
        try:
            # Contar estados en BD
            query_estados = text("SELECT COUNT(*) FROM Estados_Conversacion WHERE activo = 1")
            estados_bd = self.db.execute(query_estados).scalar()
            
            # Contar variables
            query_variables = text("SELECT COUNT(*) FROM Variables_Sistema")
            variables_bd = self.db.execute(query_variables).scalar()
            
            # Contar configuración
            query_config = text("SELECT COUNT(*) FROM Configuracion_Global WHERE activo = 1")
            config_bd = self.db.execute(query_config).scalar()
            
            print(f"📊 Resultados migración:")
            print(f"   - Estados: {estados_bd}")
            print(f"   - Variables: {variables_bd}")
            print(f"   - Configuración: {config_bd}")
            
            if estados_bd >= 4:  # Al menos los estados básicos
                print("✅ Migración verificada exitosamente")
                return True
            else:
                print("⚠️ Verificar migración - pocos estados migrados")
                return False
                
        except Exception as e:
            print(f"❌ Error verificando migración: {e}")
            return False

def main():
    """
    Función principal para ejecutar la migración
    """
    print("🔧 MIGRADOR YAML → SQL")
    print("="*30)
    
    # Verificar que existe el archivo YAML
    if not os.path.exists("base_conocimiento.yaml"):
        print("❌ No se encuentra base_conocimiento.yaml en el directorio actual")
        print(f"📁 Directorio actual: {os.getcwd()}")
        return
    
    # Crear sesión de BD
    try:
        db = crear_session()
        print("✅ Conexión a base de datos establecida")
    except Exception as e:
        print(f"❌ Error conectando a base de datos: {e}")
        return
    
    # Verificar nombres de tablas existentes
    migrador = MigradorYamlSQL(db)
    print("\n🔍 Verificando tablas existentes...")
    migrador.verificar_nombres_tablas()
    
    # Preguntar si continuar
    continuar = input("\n¿Continuar con la migración? (s/n): ").lower().strip()
    if continuar != 's':
        print("❌ Migración cancelada por el usuario")
        db.close()
        return
    
    try:
        exito = migrador.ejecutar_migracion_completa()
        
        if exito:
            print("\n🎉 ¡MIGRACIÓN COMPLETADA!")
            print("📋 Próximos pasos:")
            print("1. Probar el sistema con configuración SQL")
            print("2. Ajustar estados desde Admin Panel (cuando esté listo)")
            print("3. Una vez estable, respaldar y eliminar base_conocimiento.yaml")
            print("\n🚀 Para probar:")
            print("   python main.py")
            print("   curl -X POST localhost:8000/api/v1/chat/message -d '{\"user_id\": 1, \"message\": \"hola\"}'")
        else:
            print("\n❌ Migración falló. Revisa los errores anteriores.")
            
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            db.close()
        except:
            pass

if __name__ == "__main__":
    main()