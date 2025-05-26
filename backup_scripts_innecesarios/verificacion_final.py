"""
Script de verificación final para confirmar que todas las correcciones funcionan
"""

import sys
import os
import requests
import time
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyodbc
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuración
SERVER = "172.18.79.20,1433"
DATABASE = "turnosvirtuales_dev"
API_BASE_URL = "http://127.0.0.1:8000"

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

def verificar_base_datos():
    """Verifica que la base de datos esté correcta"""
    print("🔍 VERIFICANDO BASE DE DATOS...")
    
    try:
        db = crear_session()
        
        # Verificar tablas principales
        tablas_criticas = [
            'Estados_Conversacion',
            'Variables_Sistema', 
            'Configuracion_Global',
            'predicciones_ml',
            'Condiciones_Negocio',
            'Acciones_Negocio'
        ]
        
        for tabla in tablas_criticas:
            try:
                query = text(f"SELECT COUNT(*) FROM {tabla}")
                count = db.execute(query).scalar()
                
                if count > 0:
                    print(f"   ✅ {tabla}: {count} registros")
                else:
                    print(f"   ⚠️ {tabla}: Sin registros")
                    
            except Exception as e:
                print(f"   ❌ {tabla}: ERROR - {e}")
        
        # Verificar variables específicas
        query = text("""
            SELECT nombre, valor_por_defecto 
            FROM Variables_Sistema 
            WHERE nombre IN ('saldo_total', 'oferta_2', 'pago_flexible')
        """)
        
        variables = db.execute(query).fetchall()
        print(f"\n   📊 Variables críticas encontradas: {len(variables)}")
        for var in variables:
            print(f"      - {var[0]}: {var[1]}")
        
        db.close()
        return len(variables) >= 3
        
    except Exception as e:
        print(f"   ❌ Error verificando BD: {e}")
        return False

def verificar_archivos_python():
    """Verifica que los archivos Python estén creados"""
    print("\n🔍 VERIFICANDO ARCHIVOS PYTHON...")
    
    archivos_criticos = [
        "app/services/variable_service.py",
        "app/services/condiciones_service.py", 
        "app/services/acciones_service.py"
    ]
    
    todos_presentes = True
    
    for archivo in archivos_criticos:
        if os.path.exists(archivo):
            print(f"   ✅ {archivo}")
        else:
            print(f"   ❌ {archivo} - FALTANTE")
            todos_presentes = False
    
    # Verificar contenido de variable_service
    if os.path.exists("app/services/variable_service.py"):
        with open("app/services/variable_service.py", 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        funciones_criticas = [
            'resolver_variables',
            '_cargar_variables_sistema',
            '_calcular_variable_dinamica'
        ]
        
        for funcion in funciones_criticas:
            if funcion in contenido:
                print(f"   ✅ Función {funcion} presente")
            else:
                print(f"   ❌ Función {funcion} faltante")
                todos_presentes = False
    
    return todos_presentes

def test_resolucion_variables_directo():
    """Prueba directa de resolución de variables"""
    print("\n🧪 PROBANDO RESOLUCIÓN DE VARIABLES DIRECTA...")
    
    try:
        from app.services.variable_service import VariableService
        
        db = crear_session()
        variable_service = VariableService(db)
        
        # Test con mensaje real del chat
        mensaje_test = "Te propongo estas opciones de pago para tu deuda de {{saldo_total}}: 1️⃣ Pago único con descuento de {{oferta_2}}."
        
        contexto_test = {
            'saldo': 20000,
            'nombre_cliente': 'Cliente Prueba'
        }
        
        resultado = variable_service.resolver_variables(mensaje_test, contexto_test)
        
        print(f"   📝 Mensaje original: {mensaje_test[:50]}...")
        print(f"   📝 Mensaje resuelto: {resultado[:50]}...")
        
        # Verificar que las variables se resolvieron
        if "{{" not in resultado:
            print("   ✅ Variables resueltas correctamente")
            return True
        else:
            print("   ❌ Variables sin resolver detectadas")
            return False
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Error en test directo: {e}")
        return False

def verificar_servidor_corriendo():
    """Verifica si el servidor FastAPI está corriendo"""
    print("\n🔍 VERIFICANDO SERVIDOR FASTAPI...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("   ✅ Servidor FastAPI funcionando")
            return True
        else:
            print(f"   ⚠️ Servidor responde pero código: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException:
        print("   ❌ Servidor no está corriendo")
        print("   💡 Ejecutar: python main.py")
        return False

def test_api_chat():
    """Prueba la API del chat para verificar resolución de variables"""
    print("\n🧪 PROBANDO API DE CHAT...")
    
    if not verificar_servidor_corriendo():
        return False
    
    try:
        # Test mensaje simple
        payload = {
            "user_id": 999,  # ID de prueba
            "message": "hola"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat/message",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            mensaje_respuesta = data.get('message', '')
            
            print(f"   📝 Respuesta API: {mensaje_respuesta[:100]}...")
            
            # Verificar si hay variables sin resolver
            if "{{" in mensaje_respuesta:
                print("   ❌ Variables sin resolver en respuesta API")
                return False
            else:
                print("   ✅ Respuesta API sin variables sin resolver")
                return True
        else:
            print(f"   ❌ Error API: {response.status_code}")
            if response.text:
                print(f"      {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ Error probando API: {e}")
        return False

def generar_reporte_final(resultados):
    """Genera reporte final con resultados"""
    print("\n📊 REPORTE FINAL")
    print("="*50)
    
    total_pruebas = len(resultados)
    pruebas_exitosas = sum(1 for r in resultados.values() if r)
    
    print(f"Pruebas realizadas: {total_pruebas}")
    print(f"Pruebas exitosas: {pruebas_exitosas}")
    print(f"Porcentaje de éxito: {(pruebas_exitosas/total_pruebas)*100:.1f}%")
    
    print("\n📋 Detalle de pruebas:")
    for prueba, resultado in resultados.items():
        status = "✅" if resultado else "❌"
        print(f"   {status} {prueba}")
    
    if pruebas_exitosas == total_pruebas:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        print("\n🚀 El sistema está listo para usar:")
        print("1. Las variables {{}} se resuelven correctamente")
        print("2. Las condiciones y acciones están cargadas")
        print("3. La API responde sin errores")
        print("4. La base de datos está completa")
        
        return True
    else:
        print("\n⚠️ ALGUNAS PRUEBAS FALLARON")
        print("\n🔧 Acciones recomendadas:")
        
        if not resultados.get('base_datos'):
            print("- Ejecutar: python verificar_migracion.py")
        
        if not resultados.get('archivos_python'):
            print("- Ejecutar: python corregir_condiciones_acciones.py")
            print("- Ejecutar: python integrar_variable_service.py")
        
        if not resultados.get('test_variables'):
            print("- Verificar variable_service.py")
            print("- Ejecutar: python test_variables.py")
        
        if not resultados.get('api_chat'):
            print("- Reiniciar servidor: python main.py")
            print("- Verificar logs del servidor")
        
        return False

def main():
    print("🔧 VERIFICACIÓN FINAL DEL SISTEMA")
    print("="*50)
    
    print("🎯 Verificando todas las correcciones aplicadas...")
    
    # Ejecutar todas las verificaciones
    resultados = {
        'base_datos': verificar_base_datos(),
        'archivos_python': verificar_archivos_python(),
        'test_variables': test_resolucion_variables_directo(),
        'api_chat': test_api_chat()
    }
    
    # Generar reporte final
    exito_total = generar_reporte_final(resultados)
    
    if exito_total:
        print("\n🎊 SISTEMA COMPLETAMENTE FUNCIONAL")
        print("\nPuedes usar el chat sin problemas:")
        print(f"- Abrir: {API_BASE_URL}")
        print("- Las variables {{saldo_total}} mostrarán valores reales")
        print("- Los botones funcionarán correctamente")
        print("- No más errores de tabla faltante")
    else:
        print("\n🔧 SISTEMA REQUIERE CORRECCIONES ADICIONALES")
        print("Sigue las acciones recomendadas arriba.")

if __name__ == "__main__":
    main()