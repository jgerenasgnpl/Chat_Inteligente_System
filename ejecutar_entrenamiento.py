#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de ejecución simplificado para entrenamiento ML
Ejecutar desde la raíz del proyecto: python ejecutar_entrenamiento.py
"""

import os
import sys
import subprocess
from pathlib import Path

def verificar_estructura_proyecto():
    """Verifica y crea la estructura de directorios necesaria"""
    print("🔍 Verificando estructura del proyecto...")
    
    # Detectar directorio raíz del proyecto
    current_dir = Path.cwd()
    
    # Buscar indicadores del proyecto
    indicadores = ['main.py', 'app', 'requirements.txt']
    proyecto_encontrado = False
    
    for indicador in indicadores:
        if (current_dir / indicador).exists():
            proyecto_encontrado = True
            break
    
    if not proyecto_encontrado:
        print("⚠️ No se detectó estructura de proyecto Django/FastAPI")
        print("Asegúrate de ejecutar este script desde la raíz del proyecto")
    
    # Crear directorios necesarios
    directorios = [
        'data',
        'data/training',
        'models',
        'logs',
        'app/machine_learning',
        'app/machine_learning/train'
    ]
    
    for directorio in directorios:
        dir_path = current_dir / directorio
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 {directorio}: {'✅ Existe' if dir_path.exists() else '❌ Creado'}")
    
    return current_dir

def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    print("\n🔍 Verificando dependencias...")
    
    dependencias_requeridas = [
        'pandas',
        'numpy', 
        'scikit-learn',
        'joblib',
        'pyodbc',
        'openpyxl'  # Para leer/escribir Excel
    ]
    
    dependencias_faltantes = []
    
    for dep in dependencias_requeridas:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✅ {dep}")
        except ImportError:
            dependencias_faltantes.append(dep)
            print(f"❌ {dep} - NO INSTALADO")
    
    if dependencias_faltantes:
        print(f"\n⚠️ Dependencias faltantes: {', '.join(dependencias_faltantes)}")
        print("Instala con: pip install " + " ".join(dependencias_faltantes))
        return False
    
    print("✅ Todas las dependencias están instaladas")
    return True

def copiar_script_entrenamiento(proyecto_dir):
    """Copia el script de entrenamiento a la ubicación correcta"""
    print("\n📋 Preparando script de entrenamiento...")
    
    # Script de entrenamiento (el que creamos en el artefacto anterior)
    script_content = '''# Este archivo debe ser reemplazado por el contenido del artefacto train_ml_corregido.py
# Por ahora, ejecutaremos el entrenamiento directamente desde aquí
print("⚠️ Script de entrenamiento no encontrado")
print("Copia el contenido del archivo train_ml_corregido.py aquí")
'''
    
    # Ubicación del script
    script_path = proyecto_dir / 'app' / 'machine_learning' / 'train' / 'train_ml_corregido.py'
    
    if not script_path.exists():
        print(f"📝 Creando script en: {script_path}")
        script_path.write_text(script_content, encoding='utf-8')
        
        print(f"""
🚨 IMPORTANTE: 
1. Copia el contenido completo del artefacto 'train_ml_corregido.py' 
2. Pégalo en el archivo: {script_path}
3. Guarda el archivo
4. Ejecuta nuevamente este script
""")
        return False
    else:
        print(f"✅ Script de entrenamiento encontrado: {script_path}")
        return True

def ejecutar_entrenamiento_automatico(proyecto_dir):
    """Ejecuta el entrenamiento en modo automático"""
    print("\n🚀 Iniciando entrenamiento automático...")
    
    # Ruta al script de entrenamiento
    script_path = proyecto_dir / 'app' / 'machine_learning' / 'train' / 'train_ml_corregido.py'
    
    if not script_path.exists():
        print(f"❌ Script no encontrado: {script_path}")
        return False
    
    try:
        # Ejecutar en modo automático
        cmd = [sys.executable, str(script_path), '--auto']
        
        print(f"🔧 Ejecutando: {' '.join(cmd)}")
        print("="*60)
        
        # Ejecutar con salida en tiempo real
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Mostrar salida en tiempo real
        for line in iter(process.stdout.readline, ''):
            print(line.rstrip())
        
        process.wait()
        
        if process.returncode == 0:
            print("\n🎉 ¡ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
            return True
        else:
            print(f"\n❌ Entrenamiento falló con código: {process.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando entrenamiento: {e}")
        return False

def verificar_conexion_bd():
    """Verifica la conexión a la base de datos"""
    print("\n🔍 Verificando conexión a base de datos...")
    
    try:
        import pyodbc
        
        # Intentar conexión (misma configuración que en train_ml_corregido.py)
        conn_string = (
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=172.18.79.20,1433;'
            'DATABASE=turnosvirtuales_dev;'
            'Trusted_Connection=yes'
        )
        
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        print("✅ Conexión a BD exitosa")
        return True
        
    except Exception as e:
        print(f"⚠️ Problema con BD (continuará sin BD): {e}")
        print("💡 El entrenamiento funcionará, pero no se registrarán metadatos en BD")
        return False

def mostrar_instrucciones_post_entrenamiento():
    """Muestra instrucciones después del entrenamiento"""
    print("""
📋 === PRÓXIMOS PASOS DESPUÉS DEL ENTRENAMIENTO ===

1. 🚀 PROBAR EL SISTEMA:
   python main.py
   
2. 🧪 PROBAR EL CHAT:
   curl -X POST http://localhost:8000/api/v1/chat/message \\
   -H "Content-Type: application/json" \\
   -d '{"user_id": 1, "message": "1020428633"}'

3. 📊 VERIFICAR MODELO:
   - Archivo modelo guardado en: models/intention_classifier_YYYYMMDD_HHMMSS.joblib
   - Logs de entrenamiento en: logs/
   - Datos de entrenamiento en: data/training/

4. 🔧 PERSONALIZAR (OPCIONAL):
   - Editar: data/training/datos_entrenamiento.xlsx (agregar más ejemplos)
   - Editar: data/training/estados_conversacion.xlsx (modificar flujos)
   - Re-entrenar: python ejecutar_entrenamiento.py

5. 📈 MONITOREAR:
   - Accuracy del modelo debe ser > 80%
   - Probar con diferentes mensajes
   - Verificar que detecte cédulas correctamente

¡Tu sistema de chat inteligente está listo! 🎉
""")

def main():
    """Función principal del script de ejecución"""
    print("🤖 EJECUTOR AUTOMÁTICO DE ENTRENAMIENTO ML")
    print("Sistema de Chat Inteligente para Cobranza")
    print("="*50)
    
    # 1. Verificar estructura
    proyecto_dir = verificar_estructura_proyecto()
    
    # 2. Verificar dependencias
    if not verificar_dependencias():
        print("\n❌ Instala las dependencias faltantes antes de continuar")
        return 1
    
    # 3. Verificar conexión BD (opcional)
    verificar_conexion_bd()
    
    # 4. Verificar/copiar script de entrenamiento
    if not copiar_script_entrenamiento(proyecto_dir):
        print("\n❌ Configura el script de entrenamiento antes de continuar")
        return 1
    
    # 5. Ejecutar entrenamiento
    if ejecutar_entrenamiento_automatico(proyecto_dir):
        mostrar_instrucciones_post_entrenamiento()
        return 0
    else:
        print("\n❌ El entrenamiento falló. Revisa los errores anteriores.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Entrenamiento cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)