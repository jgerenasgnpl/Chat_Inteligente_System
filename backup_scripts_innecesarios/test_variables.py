"""
Script para probar que la resolución de variables funciona correctamente
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.variable_service import VariableService
import pyodbc
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuración de conexión
SERVER = "172.18.79.20,1433"
DATABASE = "turnosvirtuales_dev"

def crear_session():
    """Crea sesión de base de datos"""
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"Trusted_Connection=yes;"
    )
    params = urllib.parse.quote_plus(connection_string)
    database_url = f"mssql+pyodbc:///?odbc_connect={params}"
    
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def test_resolucion_variables():
    """Prueba la resolución de variables"""
    print("🧪 PROBANDO RESOLUCIÓN DE VARIABLES")
    print("="*40)
    
    # Crear sesión y servicio
    db = crear_session()
    variable_service = VariableService(db)
    
    # Textos de prueba con variables
    textos_prueba = [
        "Hola {{cliente_nombre}}, tu saldo es de {{saldo_total}}",
        "Te ofrecemos un plan de 2 cuotas por {{oferta_2}}",
        "Puedes pagar un inicial de {{pago_flexible}} y el resto en cuotas",
        "El descuento disponible es del {{descuento_disponible}}",
        "Tu cuota mensual sería de {{cuota_mensual}}"
    ]
    
    # Contexto de prueba
    contexto_prueba = {
        "nombre_cliente": "Juan Pérez",
        "saldo": 25000,
        "entidad": "Banco Nacional",
        "descuento": 20,
        "num_cuotas": 4
    }
    
    print("📋 Contexto de prueba:")
    for key, value in contexto_prueba.items():
        print(f"   {key}: {value}")
    
    print("\n🔧 Resolviendo variables...")
    
    for i, texto in enumerate(textos_prueba, 1):
        print(f"\n{i}. Texto original:")
        print(f"   {texto}")
        
        texto_resuelto = variable_service.resolver_variables(texto, contexto_prueba)
        
        print(f"   Texto resuelto:")
        print(f"   {texto_resuelto}")
        
        # Verificar que no queden variables sin resolver
        if "{{" in texto_resuelto:
            print(f"   ⚠️ Variables sin resolver detectadas")
        else:
            print(f"   ✅ Todas las variables resueltas")
    
    # Probar variables disponibles
    print(f"\n📋 Variables disponibles:")
    variables = variable_service.obtener_variables_disponibles()
    for nombre in sorted(variables.keys()):
        print(f"   - {nombre}")
    
    db.close()

def test_mensaje_completo():
    """Prueba un mensaje completo como el que aparece en el chat"""
    print("\n🎯 PROBANDO MENSAJE COMPLETO DEL CHAT")
    print("="*40)
    
    db = crear_session()
    variable_service = VariableService(db)
    
    # Mensaje que aparece en el log con errores
    mensaje_original = """Te propongo estas opciones de pago para tu deuda de {{saldo_total}}: 
1️⃣ Pago único con descuento de {{oferta_2}}. 
2️⃣ Plan en 2 cuotas sin interés adicional. 
3️⃣ Plan en 6 cuotas con un primer pago de {{pago_flexible}}. ¿Cuál prefieres?"""
    
    contexto = {
        "saldo": 18500,
        "descuento": 15
    }
    
    print("📝 Mensaje original:")
    print(mensaje_original)
    
    print(f"\n🔧 Resolviendo con contexto: {contexto}")
    
    mensaje_resuelto = variable_service.resolver_variables(mensaje_original, contexto)
    
    print(f"\n✅ Mensaje resuelto:")
    print(mensaje_resuelto)
    
    db.close()

if __name__ == "__main__":
    try:
        test_resolucion_variables()
        test_mensaje_completo()
        
        print("\n🎉 PRUEBAS COMPLETADAS")
        print("\n📋 Si las variables se resuelven correctamente:")
        print("1. Reinicia el servidor FastAPI")
        print("2. Prueba el chat nuevamente")
        print("3. Los mensajes deberían mostrar valores reales")
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()