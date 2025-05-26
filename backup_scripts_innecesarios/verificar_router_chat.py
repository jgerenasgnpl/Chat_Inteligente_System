"""
Script para verificar el estado actual del router de chat
y cómo está pasando el VariableService
"""

import os

def analizar_router_chat():
    """Analiza el router de chat actual"""
    archivo_router = "app/api/endpoints/chat.py"
    
    print("🔍 ANALIZANDO ROUTER DE CHAT")
    print("="*40)
    
    if not os.path.exists(archivo_router):
        print(f"❌ No se encontró: {archivo_router}")
        return
    
    try:
        with open(archivo_router, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        print(f"📄 Archivo: {archivo_router}")
        print(f"📊 Tamaño: {len(contenido)} caracteres")
        
        # Mostrar líneas relevantes
        lineas = contenido.split('\n')
        
        print("\n📋 LÍNEAS RELEVANTES:")
        for i, linea in enumerate(lineas, 1):
            linea_clean = linea.strip()
            
            # Mostrar imports
            if ('import' in linea_clean and 
                ('VariableService' in linea_clean or 'variable_service' in linea_clean)):
                print(f"   {i:2d}: {linea}")
            
            # Mostrar donde se usa ConfigurableFlowManager
            elif 'ConfigurableFlowManager' in linea:
                print(f"   {i:2d}: {linea}")
            
            # Mostrar función principal del chat
            elif 'def process_chat_message' in linea or 'def chat' in linea:
                print(f"   {i:2d}: {linea}")
                # Mostrar siguientes 10 líneas
                for j in range(1, min(11, len(lineas) - i)):
                    if i + j <= len(lineas):
                        print(f"   {i+j:2d}: {lineas[i+j-1]}")
        
        # Verificaciones específicas
        print("\n🔍 VERIFICACIONES:")
        
        verificaciones = {
            "Import VariableService": "from app.services.variable_service import VariableService" in contenido,
            "Import ConfigurableFlowManager": "ConfigurableFlowManager" in contenido,
            "Usa VariableService(db)": "VariableService(db)" in contenido,
            "Pasa a flow_manager": "flow_manager = " in contenido and "VariableService" in contenido
        }
        
        for verificacion, resultado in verificaciones.items():
            status = "✅" if resultado else "❌"
            print(f"   {status} {verificacion}")
        
        # Buscar función específica de procesamiento
        print("\n🔍 FUNCIÓN DE PROCESAMIENTO:")
        
        patron_funcion = None
        inicio_funcion = None
        
        for i, linea in enumerate(lineas):
            if 'def process_chat_message' in linea or 'def chat_message' in linea:
                patron_funcion = linea.strip()
                inicio_funcion = i
                break
        
        if inicio_funcion is not None:
            print(f"   ✅ Función encontrada en línea {inicio_funcion + 1}: {patron_funcion}")
            
            # Mostrar toda la función
            print("\n📋 CÓDIGO DE LA FUNCIÓN:")
            nivel_indentacion = len(lineas[inicio_funcion]) - len(lineas[inicio_funcion].lstrip())
            
            for i in range(inicio_funcion, min(inicio_funcion + 30, len(lineas))):
                linea_actual = lineas[i]
                
                # Parar si encontramos otra función al mismo nivel
                if (i > inicio_funcion and 
                    linea_actual.strip() and 
                    not linea_actual.startswith(' ') and 
                    ('def ' in linea_actual or 'class ' in linea_actual)):
                    break
                
                print(f"   {i+1:2d}: {linea_actual}")
        
        else:
            print("   ❌ No se encontró función de procesamiento")
        
        return contenido
        
    except Exception as e:
        print(f"❌ Error analizando router: {e}")
        return None

def buscar_archivos_flow_manager():
    """Busca archivos que podrían contener ConfigurableFlowManager"""
    print("\n🔍 BUSCANDO ConfigurableFlowManager...")
    
    import glob
    
    archivos_py = glob.glob("**/*.py", recursive=True)
    archivos_encontrados = []
    
    for archivo in archivos_py:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if 'ConfigurableFlowManager' in contenido:
                    archivos_encontrados.append(archivo)
                    
                    # Ver si es definición de clase o import
                    if 'class ConfigurableFlowManager' in contenido:
                        print(f"   ✅ DEFINICIÓN: {archivo}")
                    else:
                        print(f"   📦 IMPORT: {archivo}")
        except:
            continue
    
    return archivos_encontrados

def main():
    print("🔧 VERIFICADOR DE ROUTER CHAT")
    print("="*50)
    
    # Analizar router actual
    contenido_router = analizar_router_chat()
    
    # Buscar ConfigurableFlowManager
    archivos_flow = buscar_archivos_flow_manager()
    
    print(f"\n📊 RESUMEN:")
    print(f"   📄 Router analizado: {'✅' if contenido_router else '❌'}")
    print(f"   📦 Archivos con ConfigurableFlowManager: {len(archivos_flow)}")
    
    if archivos_flow:
        print("\n🎯 PRÓXIMO PASO:")
        print("   Ejecutar: python encontrar_flow_manager.py")
        print("   Para corregir el ConfigurableFlowManager")
    else:
        print("\n⚠️ ConfigurableFlowManager no encontrado")
        print("   Verificar imports en el router")

if __name__ == "__main__":
    main()