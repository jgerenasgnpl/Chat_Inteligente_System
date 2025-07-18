"""
🚀 SCRIPT DE AUTOMATIZACIÓN COMPLETA
Sistema de entrenamiento y actualización automática
Ejecutar: python automation_training_script.py
"""

import os
import sys
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import urllib.parse

# Configurar logging
# Primero, crea el handler de archivo sin problemas de codificación para emojis
file_handler = logging.FileHandler('logs/training_automation.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Luego, crea el StreamHandler y especifica la codificación UTF-8
# Es importante que sys.stdout esté configurado para manejar UTF-8 si es posible en el entorno.
# Si el terminal no lo soporta, los emojis aún podrían no mostrarse,
# pero el error de Python se resolverá.
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Intenta establecer la codificación para el StreamHandler.
# En Python 3.9+, puedes pasar 'encoding' directamente a StreamHandler.
# Para versiones anteriores o para mayor compatibilidad, puedes hacerlo así:
try:
    # Python 3.9+ supports 'encoding' parameter directly
    stream_handler = logging.StreamHandler(sys.stdout, encoding='utf-8')
except TypeError:
    # For older Python versions, set it manually (less robust)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    stream_handler.encoding = 'utf-8' # Esto es lo más importante para el stream_handler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        file_handler,
        stream_handler # Usa el handler con UTF-8 configurado
    ]
)
logger = logging.getLogger(__name__)

class TrainingAutomationSystem:
    """Sistema completo de automatización para entrenamiento y actualización"""
    
    def __init__(self):
        self.db_engine = self._create_db_connection()
        self.session = None
        self.stats = {
            'training_data_added': 0,
            'states_updated': 0,
            'model_retrained': False,
            'errors': []
        }
        
        # Crear directorios necesarios
        self._create_directories()
    
    def _create_directories(self):
        """Crear directorios necesarios"""
        directories = [
            'data/training',
            'data/exports',
            'logs',
            'models',
            'backups'
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _create_db_connection(self):
        """Crear conexión a la base de datos"""
        try:
            # Configuración de conexión (ajustar según tu entorno)
            odbc_str = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=172.18.79.20,1433;"
                "DATABASE=turnosvirtuales_dev;"
                "Trusted_Connection=yes;"
            )
            params = urllib.parse.quote_plus(odbc_str)
            
            engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={params}",
                pool_pre_ping=True,
                echo=False
            )
            
            logger.info("✅ Conexión a base de datos establecida")
            return engine
            
        except Exception as e:
            logger.error(f"❌ Error conectando a BD: {e}")
            raise
    
    def run_complete_automation(self):
        """🚀 EJECUTAR AUTOMATIZACIÓN COMPLETA"""
        try:
            logger.info("🚀 Iniciando automatización completa del sistema")
            
            # Crear sesión
            Session = sessionmaker(bind=self.db_engine)
            self.session = Session()
            
            # PASO 1: Generar datos de entrenamiento adicionales
            logger.info("📚 PASO 1: Generando datos de entrenamiento adicionales")
            self._generate_additional_training_data()
            
            # PASO 2: Actualizar estados de conversación
            logger.info("⚙️ PASO 2: Actualizando estados de conversación")
            self._update_conversation_states()
            
            # PASO 3: Configurar variables del sistema
            logger.info("🔧 PASO 3: Configurando variables del sistema")
            self._configure_system_variables()
            
            # PASO 4: Verificar y reparar integridad
            logger.info("🔍 PASO 4: Verificando integridad del sistema")
            self._verify_system_integrity()
            
            # PASO 5: Reentrenar modelo ML
            logger.info("🧠 PASO 5: Reentrenando modelo ML")
            self._retrain_ml_model()
            
            # PASO 6: Generar reporte final
            logger.info("📊 PASO 6: Generando reporte final")
            report = self._generate_final_report()
            
            # Cerrar sesión
            self.session.close()
            
            logger.info("🎉 Automatización completada exitosamente")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error en automatización: {e}")
            if self.session:
                self.session.rollback()
                self.session.close()
            raise
    
    def _generate_additional_training_data(self):
        """📚 Generar datos adicionales de entrenamiento"""
        try:
            # Datos de entrenamiento expandidos específicos para cobranza
            training_data = [
                # IDENTIFICACION - Variaciones de cédulas
                ("mi cedula es 12345678", "IDENTIFICACION", 1.0),
                ("documento 93388915", "IDENTIFICACION", 1.0),
                ("cc 1020428633", "IDENTIFICACION", 1.0),
                ("soy el 12345678", "IDENTIFICACION", 1.0),
                ("tengo la cedula 93388915", "IDENTIFICACION", 1.0),
                ("es 12345678", "IDENTIFICACION", 1.0),
                ("cédula: 93388915", "IDENTIFICACION", 1.0),
                ("identificacion 1020428633", "IDENTIFICACION", 1.0),
                
                # CONSULTA_DEUDA - Variaciones de consultas
                ("cuanto debo", "CONSULTA_DEUDA", 1.0),
                ("cual es mi deuda", "CONSULTA_DEUDA", 1.0),
                ("cuanto tengo pendiente", "CONSULTA_DEUDA", 1.0),
                ("mi saldo", "CONSULTA_DEUDA", 1.0),
                ("información de mi cuenta", "CONSULTA_DEUDA", 1.0),
                ("estado de mi deuda", "CONSULTA_DEUDA", 1.0),
                ("saldo pendiente", "CONSULTA_DEUDA", 1.0),
                ("que debo", "CONSULTA_DEUDA", 1.0),
                
                # INTENCION_PAGO - Variaciones de intención de pago
                ("quiero pagar", "INTENCION_PAGO", 1.0),
                ("necesito pagar", "INTENCION_PAGO", 1.0),
                ("como puedo pagar", "INTENCION_PAGO", 1.0),
                ("voy a pagar", "INTENCION_PAGO", 1.0),
                ("realizar pago", "INTENCION_PAGO", 1.0),
                ("cancelar deuda", "INTENCION_PAGO", 1.0),
                ("liquidar", "INTENCION_PAGO", 1.0),
                ("pagar mi cuenta", "INTENCION_PAGO", 1.0),
                
                # SOLICITUD_PLAN - Variaciones de solicitud de planes
                ("opciones de pago", "SOLICITUD_PLAN", 1.0),
                ("planes de pago", "SOLICITUD_PLAN", 1.0),
                ("facilidades", "SOLICITUD_PLAN", 1.0),
                ("cuotas", "SOLICITUD_PLAN", 1.0),
                ("descuento", "SOLICITUD_PLAN", 1.0),
                ("rebaja", "SOLICITUD_PLAN", 1.0),
                ("que opciones tengo", "SOLICITUD_PLAN", 1.0),
                ("planes disponibles", "SOLICITUD_PLAN", 1.0),
                
                # CONFIRMACION - Variaciones de confirmación
                ("si acepto", "CONFIRMACION", 1.0),
                ("está bien", "CONFIRMACION", 1.0),
                ("de acuerdo", "CONFIRMACION", 1.0),
                ("ok", "CONFIRMACION", 1.0),
                ("perfecto", "CONFIRMACION", 1.0),
                ("confirmo", "CONFIRMACION", 1.0),
                ("si me parece bien", "CONFIRMACION", 1.0),
                ("acepto la propuesta", "CONFIRMACION", 1.0),
                
                # RECHAZO - Variaciones de rechazo
                ("no puedo", "RECHAZO", 1.0),
                ("no me interesa", "RECHAZO", 1.0),
                ("imposible", "RECHAZO", 1.0),
                ("no tengo dinero", "RECHAZO", 1.0),
                ("muy caro", "RECHAZO", 1.0),
                ("no me conviene", "RECHAZO", 1.0),
                ("no acepto", "RECHAZO", 1.0),
                ("no gracias", "RECHAZO", 1.0),
                
                # SALUDO - Variaciones de saludo
                ("hola", "SALUDO", 1.0),
                ("buenos días", "SALUDO", 1.0),
                ("buenas tardes", "SALUDO", 1.0),
                ("buenas noches", "SALUDO", 1.0),
                ("que tal", "SALUDO", 1.0),
                ("como estas", "SALUDO", 1.0),
                ("buen día", "SALUDO", 1.0),
                ("hi", "SALUDO", 1.0),
                
                # DESPEDIDA - Variaciones de despedida
                ("gracias", "DESPEDIDA", 1.0),
                ("muchas gracias", "DESPEDIDA", 1.0),
                ("hasta luego", "DESPEDIDA", 1.0),
                ("adios", "DESPEDIDA", 1.0),
                ("chao", "DESPEDIDA", 1.0),
                ("nos vemos", "DESPEDIDA", 1.0),
                ("que tengas buen día", "DESPEDIDA", 1.0),
                ("bye", "DESPEDIDA", 1.0),
                
                # CASOS MIXTOS
                ("hola quiero pagar mi deuda", "INTENCION_PAGO", 1.0),
                ("buenos días, cuanto debo", "CONSULTA_DEUDA", 1.0),
                ("si quiero ver las opciones", "SOLICITUD_PLAN", 1.0),
                ("no puedo pagar todo de una", "RECHAZO", 1.0),
                ("acepto el plan de cuotas", "CONFIRMACION", 1.0),
                ("gracias por la información", "DESPEDIDA", 1.0),
            ]
            
            # Insertar datos
            for texto, intencion, confianza in training_data:
                # Verificar duplicados
                check_query = text("""
                    SELECT COUNT(*) FROM datos_entrenamiento 
                    WHERE texto_mensaje = :texto AND intencion_real = :intencion
                """)
                
                exists = self.session.execute(check_query, {
                    'texto': texto,
                    'intencion': intencion
                }).scalar()
                
                if exists == 0:
                    # Insertar nuevo
                    insert_query = text("""
                        INSERT INTO datos_entrenamiento 
                        (texto_mensaje, intencion_real, confianza_etiqueta, 
                         fecha_registro, feedback_usuario, validado)
                        VALUES (:texto, :intencion, :confianza, GETDATE(), 'correcto', 1)
                    """)
                    
                    self.session.execute(insert_query, {
                        'texto': texto,
                        'intencion': intencion,
                        'confianza': confianza
                    })
                    
                    self.stats['training_data_added'] += 1
            
            self.session.commit()
            logger.info(f"✅ Agregados {self.stats['training_data_added']} ejemplos de entrenamiento")
            
        except Exception as e:
            logger.error(f"❌ Error generando datos de entrenamiento: {e}")
            self.session.rollback()
            self.stats['errors'].append(f"Training data generation: {e}")
    
    def _update_conversation_states(self):
        """⚙️ Actualizar estados de conversación críticos"""
        try:
            # Estados críticos con templates mejorados
            critical_states = [
                {
                    'nombre': 'informar_deuda',
                    'mensaje_template': '''¡Perfecto, {{Nombre_del_cliente}}! 

📋 **Información de tu cuenta:**
🏦 Entidad: {{banco}}
💰 Saldo actual: ${{saldo_total}}

¿Te gustaría conocer las opciones de pago disponibles para ti?''',
                    'estado_siguiente_default': 'evaluar_intencion_pago',
                    'timeout_segundos': 1800
                },
                {
                    'nombre': 'proponer_planes_pago',
                    'mensaje_template': '''Excelente, {{Nombre_del_cliente}}! Te muestro las mejores opciones para tu saldo de ${{saldo_total}}:

💰 **PAGO ÚNICO CON DESCUENTO:**
🎯 Oferta especial: ${{oferta_2}} (¡Excelente ahorro!)

📅 **PLANES DE CUOTAS SIN INTERÉS:**
• 3 cuotas de: ${{hasta_3_cuotas}} cada una
• 6 cuotas de: ${{hasta_6_cuotas}} cada una  
• 12 cuotas de: ${{hasta_12_cuotas}} cada una

¿Cuál opción se adapta mejor a tu presupuesto?''',
                    'estado_siguiente_default': 'espera_eleccion_plan',
                    'timeout_segundos': 1800
                },
                {
                    'nombre': 'gestionar_objecion',
                    'mensaje_template': '''Entiendo tu situación, {{Nombre_del_cliente}}. 

Estoy aquí para encontrar una solución que funcione para ti. ¿Qué te preocupa específicamente? 

Podemos revisar:
• Planes más flexibles
• Descuentos adicionales  
• Fechas de pago convenientes
• Opciones de emergencia''',
                    'estado_siguiente_default': 'proponer_planes_pago',
                    'timeout_segundos': 1800
                },
                {
                    'nombre': 'cliente_no_encontrado',
                    'mensaje_template': '''No encontré información para esa cédula en nuestro sistema. 

Por favor verifica el número o si es correcto, un especialista te contactará para ayudarte.''',
                    'estado_siguiente_default': 'validar_documento',
                    'timeout_segundos': 1800
                }
            ]
            
            # Actualizar cada estado
            for state in critical_states:
                update_query = text("""
                    UPDATE Estados_Conversacion 
                    SET mensaje_template = :mensaje,
                        estado_siguiente_default = :estado_default,
                        timeout_segundos = :timeout,
                        fecha_actualizacion = GETDATE()
                    WHERE nombre = :nombre
                """)
                
                result = self.session.execute(update_query, {
                    'nombre': state['nombre'],
                    'mensaje': state['mensaje_template'],
                    'estado_default': state['estado_siguiente_default'],
                    'timeout': state['timeout_segundos']
                })
                
                if result.rowcount > 0:
                    self.stats['states_updated'] += 1
                    logger.info(f"✅ Estado actualizado: {state['nombre']}")
            
            self.session.commit()
            logger.info(f"✅ Actualizados {self.stats['states_updated']} estados de conversación")
            
        except Exception as e:
            logger.error(f"❌ Error actualizando estados: {e}")
            self.session.rollback()
            self.stats['errors'].append(f"States update: {e}")
    
    def _configure_system_variables(self):
        """🔧 Configurar variables del sistema"""
        try:
            # Variables críticas del sistema
            system_variables = [
                {
                    'nombre': 'nombre_empresa',
                    'descripcion': 'Nombre de la empresa',
                    'valor_por_defecto': 'Systemgroup',
                    'formato_visualizacion': '{0}'
                },
                {
                    'nombre': 'telefono_contacto',
                    'descripcion': 'Teléfono de contacto',
                    'valor_por_defecto': '601-756-0385',
                    'formato_visualizacion': '{0}'
                },
                {
                    'nombre': 'email_contacto',
                    'descripcion': 'Email de contacto',
                    'valor_por_defecto': 'contacto@systemgroup.com',
                    'formato_visualizacion': '{0}'
                },
                {
                    'nombre': 'horario_atencion',
                    'descripcion': 'Horario de atención',
                    'valor_por_defecto': '8:00 AM - 6:00 PM',
                    'formato_visualizacion': '{0}'
                },
                {
                    'nombre': 'pago_minimo_porcentaje',
                    'descripcion': 'Porcentaje mínimo de pago',
                    'valor_por_defecto': '10',
                    'formato_visualizacion': '{0}%'
                }
            ]
            
            # Verificar si existe tabla Variables_Sistema
            check_table = text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'Variables_Sistema'
            """)
            
            table_exists = self.session.execute(check_table).scalar()
            
            if table_exists == 0:
                # Crear tabla si no existe
                create_table = text("""
                    CREATE TABLE Variables_Sistema (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nombre NVARCHAR(100) NOT NULL,
                        descripcion NVARCHAR(255),
                        valor_por_defecto NVARCHAR(500),
                        formato_visualizacion NVARCHAR(100),
                        activo BIT DEFAULT 1,
                        fecha_creacion DATETIME DEFAULT GETDATE(),
                        fecha_actualizacion DATETIME DEFAULT GETDATE()
                    )
                """)
                self.session.execute(create_table)
                logger.info("✅ Tabla Variables_Sistema creada")
            
            # Insertar/actualizar variables
            for variable in system_variables:
                # Verificar si existe
                check_query = text("""
                    SELECT COUNT(*) FROM Variables_Sistema WHERE nombre = :nombre
                """)
                
                exists = self.session.execute(check_query, {
                    'nombre': variable['nombre']
                }).scalar()
                
                if exists == 0:
                    # Insertar nueva
                    insert_query = text("""
                        INSERT INTO Variables_Sistema 
                        (nombre, descripcion, valor_por_defecto, formato_visualizacion, activo)
                        VALUES (:nombre, :descripcion, :valor, :formato, 1)
                    """)
                    
                    self.session.execute(insert_query, {
                        'nombre': variable['nombre'],
                        'descripcion': variable['descripcion'],
                        'valor': variable['valor_por_defecto'],
                        'formato': variable['formato_visualizacion']
                    })
                    
                    logger.info(f"✅ Variable agregada: {variable['nombre']}")
            
            self.session.commit()
            logger.info("✅ Variables del sistema configuradas")
            
        except Exception as e:
            logger.error(f"❌ Error configurando variables: {e}")
            self.session.rollback()
            self.stats['errors'].append(f"Variables configuration: {e}")
    
    def _verify_system_integrity(self):
        """🔍 Verificar integridad del sistema"""
        try:
            # Verificar integridad de estados
            integrity_query = text("""
                SELECT 
                    nombre,
                    estado_siguiente_default,
                    CASE 
                        WHEN estado_siguiente_default IN (
                            SELECT nombre FROM Estados_Conversacion WHERE activo = 1
                        ) OR estado_siguiente_default IN ('fin', 'finalizar_conversacion')
                        THEN 'VÁLIDO' 
                        ELSE 'INVÁLIDO' 
                    END as estado_validacion
                FROM Estados_Conversacion 
                WHERE activo = 1
                    AND estado_siguiente_default IS NOT NULL
            """)
            
            integrity_results = self.session.execute(integrity_query).fetchall()
            
            invalid_states = [row for row in integrity_results if row[2] == 'INVÁLIDO']
            
            if invalid_states:
                logger.warning(f"⚠️ Estados con referencias inválidas: {len(invalid_states)}")
                for state in invalid_states:
                    logger.warning(f"   - {state[0]} → {state[1]}")
            else:
                logger.info("✅ Integridad de estados verificada")
            
            # Verificar estadísticas de datos de entrenamiento
            training_stats = text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT intencion_real) as intenciones,
                    AVG(CAST(confianza_etiqueta as FLOAT)) as confianza_promedio
                FROM datos_entrenamiento
                WHERE validado = 1
            """)
            
            stats_result = self.session.execute(training_stats).fetchone()
            
            logger.info(f"📊 Estadísticas de entrenamiento:")
            logger.info(f"   - Total ejemplos: {stats_result[0]}")
            logger.info(f"   - Intenciones: {stats_result[1]}")
            logger.info(f"   - Confianza promedio: {stats_result[2]:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Error verificando integridad: {e}")
            self.stats['errors'].append(f"Integrity verification: {e}")
    
    def _retrain_ml_model(self):
        """🧠 Reentrenar modelo ML"""
        try:
            # Ejecutar script de entrenamiento
            logger.info("🔄 Iniciando reentrenamiento del modelo ML...")
            
            # Ejecutar entrenamiento usando el sistema existente
            os.system("python ejecutar_entrenamiento.py --auto")
            
            # Verificar que el modelo se creó
            models_dir = Path("models")
            if models_dir.exists():
                model_files = list(models_dir.glob("*.joblib"))
                if model_files:
                    latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
                    logger.info(f"✅ Modelo entrenado: {latest_model.name}")
                    self.stats['model_retrained'] = True
                else:
                    logger.warning("⚠️ No se encontraron archivos de modelo")
            else:
                logger.warning("⚠️ Directorio de modelos no existe")
            
        except Exception as e:
            logger.error(f"❌ Error reentrenando modelo: {e}")
            self.stats['errors'].append(f"Model retraining: {e}")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """📊 Generar reporte final"""
        try:
            # Estadísticas finales
            final_stats = {
                'timestamp': datetime.now().isoformat(),
                'training_data_added': self.stats['training_data_added'],
                'states_updated': self.stats['states_updated'],
                'model_retrained': self.stats['model_retrained'],
                'errors_count': len(self.stats['errors']),
                'errors': self.stats['errors']
            }
            
            # Obtener estadísticas de la BD
            db_stats_query = text("""
                SELECT 
                    (SELECT COUNT(*) FROM datos_entrenamiento WHERE validado = 1) as total_training,
                    (SELECT COUNT(*) FROM Estados_Conversacion WHERE activo = 1) as total_states,
                    (SELECT COUNT(*) FROM Variables_Sistema WHERE activo = 1) as total_variables,
                    (SELECT COUNT(DISTINCT intencion_real) FROM datos_entrenamiento) as total_intentions
            """)
            
            db_stats = self.session.execute(db_stats_query).fetchone()
            
            final_stats.update({
                'total_training_examples': db_stats[0] if db_stats else 0,
                'total_active_states': db_stats[1] if db_stats else 0,
                'total_variables': db_stats[2] if db_stats else 0,
                'total_intentions': db_stats[3] if db_stats else 0
            })
            
            # Guardar reporte
            report_path = f"data/exports/automation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(final_stats, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Reporte guardado en: {report_path}")
            
            # Mostrar resumen
            logger.info("📋 RESUMEN DE AUTOMATIZACIÓN:")
            logger.info(f"   ✅ Datos de entrenamiento agregados: {final_stats['training_data_added']}")
            logger.info(f"   ✅ Estados actualizados: {final_stats['states_updated']}")
            logger.info(f"   ✅ Modelo reentrenado: {final_stats['model_retrained']}")
            logger.info(f"   ✅ Total ejemplos de entrenamiento: {final_stats['total_training_examples']}")
            logger.info(f"   ✅ Total estados activos: {final_stats['total_active_states']}")
            logger.info(f"   ✅ Total intenciones: {final_stats['total_intentions']}")
            
            if final_stats['errors_count'] > 0:
                logger.warning(f"   ⚠️ Errores encontrados: {final_stats['errors_count']}")
            
            return final_stats
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return {'error': str(e)}

def main():
    """🚀 Función principal"""
    try:
        print("🚀 Sistema de Automatización de Entrenamiento")
        print("=" * 50)
        
        # Crear sistema de automatización
        automation = TrainingAutomationSystem()
        
        # Ejecutar automatización completa
        report = automation.run_complete_automation()
        
        print("\n🎉 AUTOMATIZACIÓN COMPLETADA EXITOSAMENTE")
        print(f"📊 Reporte generado con {report.get('total_training_examples', 0)} ejemplos")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error en automatización: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())