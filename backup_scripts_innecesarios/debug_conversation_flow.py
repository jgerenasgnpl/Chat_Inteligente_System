"""
Script para debuggear dónde se está perdiendo la resolución de variables
"""

import os
import sys
import glob

def encontrar_archivos_conversation():
    """Encuentra todos los archivos relacionados con conversation"""
    print("🔍 BUSCANDO ARCHIVOS DE CONVERSACIÓN...")
    
    patterns = [
        "**/conversation*.py",
        "**/chat*.py", 
        "**/message*.py",
        "**/response*.py"
    ]
    
    archivos_encontrados = []
    
    for pattern in patterns:
        archivos = glob.glob(pattern, recursive=True)
        archivos_encontrados.extend(archivos)
    
    # Remover duplicados
    archivos_unicos = list(set(archivos_encontrados))
    
    print(f"📋 Archivos encontrados ({len(archivos_unicos)}):")
    for archivo in sorted(archivos_unicos):
        print(f"   📄 {archivo}")
    
    return archivos_unicos

def buscar_en_archivos(termino, archivos):
    """Busca un término específico en los archivos"""
    print(f"\n🔍 BUSCANDO '{termino}' EN ARCHIVOS...")
    
    resultados = []
    
    for archivo in archivos:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if termino.lower() in contenido.lower():
                    # Encontrar líneas que contienen el término
                    lineas = contenido.split('\n')
                    lineas_encontradas = []
                    
                    for i, linea in enumerate(lineas, 1):
                        if termino.lower() in linea.lower():
                            lineas_encontradas.append((i, linea.strip()))
                    
                    if lineas_encontradas:
                        resultados.append((archivo, lineas_encontradas))
                        
        except Exception as e:
            print(f"   ❌ Error leyendo {archivo}: {e}")
    
    # Mostrar resultados
    for archivo, lineas in resultados:
        print(f"\n📄 {archivo}:")
        for num_linea, linea in lineas[:3]:  # Mostrar máximo 3 líneas por archivo
            print(f"   {num_linea:3d}: {linea}")
        if len(lineas) > 3:
            print(f"   ... y {len(lineas) - 3} líneas más")
    
    return resultados

def buscar_resolucion_variables():
    """Busca dónde se deberían resolver las variables"""
    print("🔍 BUSCANDO RESOLUCIÓN DE VARIABLES...")
    
    archivos = encontrar_archivos_conversation()
    
    # Buscar términos relacionados con variables
    terminos = [
        "{{",
        "resolver_variables",
        "variable_service", 
        "VariableService",
        "message",
        "response"
    ]
    
    for termino in terminos:
        buscar_en_archivos(termino, archivos)

def verificar_imports_variable_service():
    """Verifica si el variable_service se está importando"""
    print("\n🔍 VERIFICANDO IMPORTS DE VARIABLE_SERVICE...")
    
    archivos_py = glob.glob("**/*.py", recursive=True)
    
    archivos_con_import = []
    archivos_sin_import = []
    
    for archivo in archivos_py:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if 'variable_service' in contenido.lower() or 'VariableService' in contenido:
                    archivos_con_import.append(archivo)
                elif 'conversation' in archivo.lower() or 'chat' in archivo.lower():
                    archivos_sin_import.append(archivo)
                    
        except:
            continue
    
    print(f"✅ Archivos que SÍ importan VariableService ({len(archivos_con_import)}):")
    for archivo in archivos_con_import:
        print(f"   📄 {archivo}")
    
    print(f"\n⚠️ Archivos conversation/chat que NO importan VariableService ({len(archivos_sin_import)}):")
    for archivo in archivos_sin_import:
        print(f"   📄 {archivo}")
    
    return archivos_con_import, archivos_sin_import

def analizar_main_py():
    """Analiza el archivo main.py para ver cómo se maneja el chat"""
    print("\n🔍 ANALIZANDO MAIN.PY...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar rutas de chat
        if '/chat' in contenido:
            print("✅ Rutas de chat encontradas")
        
        # Buscar imports
        imports_encontrados = []
        lineas = contenido.split('\n')
        for i, linea in enumerate(lineas, 1):
            if linea.strip().startswith('from ') or linea.strip().startswith('import '):
                imports_encontrados.append((i, linea.strip()))
        
        print(f"📋 Imports encontrados ({len(imports_encontrados)}):")
        for num_linea, import_line in imports_encontrados:
            print(f"   {num_linea:3d}: {import_line}")
        
        # Buscar variable_service
        if 'variable' in contenido.lower():
            print("✅ Referencias a 'variable' encontradas")
        else:
            print("❌ NO se encontraron referencias a 'variable'")
            
    except Exception as e:
        print(f"❌ Error analizando main.py: {e}")

def main():
    print("🔧 DEBUG: FLUJO DE CONVERSACIÓN")
    print("="*50)
    
    # Cambiar al directorio del proyecto si es necesario
    if os.path.exists('main.py'):
        print("✅ Directorio correcto detectado")
    else:
        print("❌ No se encuentra main.py - verifique el directorio")
        return
    
    analizar_main_py()
    verificar_imports_variable_service() 
    buscar_resolucion_variables()
    
    print("\n🎯 RECOMENDACIONES:")
    print("1. Verificar que variable_service se importe en conversation_manager")
    print("2. Verificar que se llame resolver_variables() antes de enviar respuesta")
    print("3. Verificar que el contexto se pase correctamente")

if __name__ == "__main__":
    main()