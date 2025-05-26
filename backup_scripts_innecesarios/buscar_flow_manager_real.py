"""
Script para encontrar el archivo REAL de ConfigurableFlowManager
(no los scripts de corrección)
"""

import os
import glob

def buscar_flow_manager_especifico():
    """Busca específicamente ConfigurableFlowManager en app/"""
    print("🔍 BÚSQUEDA ESPECÍFICA DE ConfigurableFlowManager...")
    
    # Buscar solo en directorio app/ y subdirectorios
    patrones = [
        "app/**/*.py",
        "app/*.py"
    ]
    
    archivos_encontrados = []
    
    for patron in patrones:
        archivos = glob.glob(patron, recursive=True)
        archivos_encontrados.extend(archivos)
    
    # Filtrar archivos que NO sean scripts de corrección
    archivos_filtrados = []
    for archivo in archivos_encontrados:
        nombre_archivo = os.path.basename(archivo)
        
        # Excluir archivos de corrección/debug
        if not any(palabra in nombre_archivo.lower() for palabra in 
                  ['corregir', 'debug', 'verificar', 'test', 'ejemplo']):
            archivos_filtrados.append(archivo)
    
    print(f"📋 Archivos Python encontrados en app/: {len(archivos_filtrados)}")
    
    # Buscar ConfigurableFlowManager en cada archivo
    archivos_con_clase = []
    
    for archivo in archivos_filtrados:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                # Buscar definición de clase (no imports)
                if 'class ConfigurableFlowManager' in contenido:
                    archivos_con_clase.append(archivo)
                    print(f"   ✅ DEFINICIÓN ENCONTRADA: {archivo}")
                    
                    # Mostrar líneas relevantes
                    lineas = contenido.split('\n')
                    for i, linea in enumerate(lineas):
                        if 'class ConfigurableFlowManager' in linea:
                            print(f"      Línea {i+1}: {linea.strip()}")
                            
                            # Mostrar constructor
                            for j in range(i+1, min(i+20, len(lineas))):
                                if '    def __init__(' in lineas[j]:
                                    print(f"      Línea {j+1}: {lineas[j].strip()}")
                                    # Mostrar parámetros completos
                                    for k in range(j+1, min(j+5, len(lineas))):
                                        if lineas[k].strip() and '        ' in lineas[k]:
                                            print(f"      Línea {k+1}: {lineas[k].strip()}")
                                        elif lineas[k].strip() and not lineas[k].startswith('        '):
                                            break
                                    break
                            break
                
                # También buscar imports para mapear dependencias
                elif 'ConfigurableFlowManager' in contenido and ('import' in contenido or 'from' in contenido):
                    print(f"   📦 IMPORT ENCONTRADO: {archivo}")
                    
                    # Mostrar líneas de import
                    lineas = contenido.split('\n')
                    for i, linea in enumerate(lineas):
                        if 'ConfigurableFlowManager' in linea and ('import' in linea or 'from' in linea):
                            print(f"      Línea {i+1}: {linea.strip()}")
                    
        except Exception as e:
            print(f"   ❌ Error leyendo {archivo}: {e}")
    
    return archivos_con_clase

def buscar_en_todo_el_proyecto():
    """Búsqueda más amplia si no se encuentra en app/"""
    print("\n🔍 BÚSQUEDA AMPLIA EN TODO EL PROYECTO...")
    
    archivos_py = []
    for root, dirs, files in os.walk('.'):
        # Excluir directorios comunes que no contienen código fuente
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                archivo_completo = os.path.join(root, file)
                # Normalizar path
                archivo_completo = archivo_completo.replace('\\', '/')
                
                # Excluir archivos de corrección
                if not any(palabra in file.lower() for palabra in 
                          ['corregir', 'debug', 'verificar', 'test', 'ejemplo']):
                    archivos_py.append(archivo_completo)
    
    print(f"📋 Total archivos Python: {len(archivos_py)}")
    
    archivos_con_clase = []
    
    for archivo in archivos_py:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if 'class ConfigurableFlowManager' in contenido:
                    archivos_con_clase.append(archivo)
                    print(f"   ✅ ENCONTRADO: {archivo}")
                    
        except Exception:
            continue
    
    return archivos_con_clase

def mostrar_estructura_directorios():
    """Muestra la estructura de directorios para entender el proyecto"""
    print("\n🗂️ ESTRUCTURA DEL PROYECTO:")
    
    for root, dirs, files in os.walk('.'):
        # Excluir directorios que no nos interesan
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'node_modules']]
        
        nivel = root.replace('.', '').count(os.sep)
        indent = ' ' * 2 * nivel
        
        # Solo mostrar hasta 3 niveles de profundidad
        if nivel <= 3:
            print(f"{indent}{os.path.basename(root)}/")
            
            # Mostrar archivos Python
            subindent = ' ' * 2 * (nivel + 1)
            for file in files:
                if file.endswith('.py'):
                    print(f"{subindent}{file}")

def buscar_imports_configurable():
    """Busca todos los archivos que importan ConfigurableFlowManager"""
    print("\n🔍 BUSCANDO IMPORTS DE ConfigurableFlowManager...")
    
    archivos_py = glob.glob("**/*.py", recursive=True)
    
    for archivo in archivos_py:
        # Excluir archivos de corrección
        if any(palabra in archivo.lower() for palabra in 
               ['corregir', 'debug', 'verificar', 'test', 'ejemplo']):
            continue
            
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if 'ConfigurableFlowManager' in contenido:
                    print(f"\n📄 {archivo}:")
                    
                    lineas = contenido.split('\n')
                    for i, linea in enumerate(lineas):
                        if 'ConfigurableFlowManager' in linea:
                            print(f"   {i+1:3d}: {linea.strip()}")
                    
        except Exception:
            continue

def main():
    print("🔧 BÚSQUEDA REAL DE ConfigurableFlowManager")
    print("="*60)
    
    # Verificar directorio
    if not os.path.exists('main.py'):
        print("❌ Ejecutar desde el directorio raíz del proyecto")
        return
    
    # Mostrar estructura para diagnóstico
    mostrar_estructura_directorios()
    
    # Búsqueda específica en app/
    archivos_en_app = buscar_flow_manager_especifico()
    
    if not archivos_en_app:
        print("\n⚠️ No encontrado en app/, buscando en todo el proyecto...")
        archivos_en_proyecto = buscar_en_todo_el_proyecto()
        
        if not archivos_en_proyecto:
            print("\n❌ ConfigurableFlowManager NO ENCONTRADO")
            print("\n🔍 Búsqueda de imports...")
            buscar_imports_configurable()
        else:
            print(f"\n✅ Encontrado en: {archivos_en_proyecto}")
    else:
        print(f"\n✅ ConfigurableFlowManager encontrado en: {archivos_en_app[0]}")
        
        # Ahora corregir el archivo real
        print(f"\n🎯 ARCHIVO A CORREGIR: {archivos_en_app[0]}")
        print("\nEjecuta el siguiente comando para corregir:")
        print(f"   python corregir_archivo_especifico.py \"{archivos_en_app[0]}\"")

if __name__ == "__main__":
    main()