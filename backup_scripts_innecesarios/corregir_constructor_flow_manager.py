"""
Script para corregir INMEDIATAMENTE el constructor de ConfigurableFlowManager
Soluciona el error: takes 2 positional arguments but 3 were given
"""

import os
import glob
import re

def encontrar_configurable_flow_manager():
    """Encuentra el archivo con ConfigurableFlowManager"""
    print("🔍 BUSCANDO ConfigurableFlowManager...")
    
    archivos_py = glob.glob("**/*.py", recursive=True)
    
    for archivo in archivos_py:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if 'class ConfigurableFlowManager' in contenido:
                    print(f"   ✅ ENCONTRADO: {archivo}")
                    return archivo
                    
        except Exception:
            continue
    
    print("   ❌ ConfigurableFlowManager no encontrado")
    return None

def mostrar_constructor_actual(archivo_path):
    """Muestra el constructor actual para diagnóstico"""
    print(f"\n🔍 ANALIZANDO CONSTRUCTOR EN: {archivo_path}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar la clase y su constructor
        lineas = contenido.split('\n')
        
        encontrar_clase = False
        constructor_encontrado = False
        
        for i, linea in enumerate(lineas):
            # Buscar la clase
            if 'class ConfigurableFlowManager' in linea:
                encontrar_clase = True
                print(f"   📋 Clase encontrada en línea {i+1}: {linea.strip()}")
                continue
            
            # Buscar constructor dentro de la clase
            if encontrar_clase and '    def __init__(' in linea:
                constructor_encontrado = True
                print(f"   📋 Constructor en línea {i+1}: {linea.strip()}")
                
                # Mostrar siguientes líneas del constructor
                for j in range(1, 10):  # Mostrar hasta 10 líneas más
                    if i + j < len(lineas):
                        linea_sig = lineas[i + j]
                        print(f"   {i+j+1:3d}: {linea_sig}")
                        
                        # Parar si encontramos otra función o fin de constructor
                        if (linea_sig.strip() and 
                            not linea_sig.startswith('        ') and 
                            linea_sig.startswith('    ')):
                            break
                break
        
        return constructor_encontrado
        
    except Exception as e:
        print(f"   ❌ Error leyendo archivo: {e}")
        return False

def corregir_constructor(archivo_path):
    """Corrige el constructor para aceptar VariableService"""
    print(f"\n🔧 CORRIGIENDO CONSTRUCTOR EN: {archivo_path}")
    
    try:
        # Leer archivo
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        
        # Patrón para encontrar constructor actual
        patron_constructor = r'(def __init__\(self,\s*db[^)]*)\):'
        
        match = re.search(patron_constructor, contenido)
        
        if match:
            constructor_actual = match.group(1)
            print(f"   📋 Constructor actual: {constructor_actual})")
            
            # Crear nuevo constructor con VariableService
            nuevo_constructor = constructor_actual + ', variable_service=None'
            
            print(f"   🔧 Nuevo constructor: {nuevo_constructor})")
            
            # Reemplazar constructor
            contenido = contenido.replace(
                constructor_actual + '):', 
                nuevo_constructor + '):'
            )
            
            # Buscar donde se asigna self.db y agregar self.variable_service
            patron_db_assign = r'(self\.db\s*=\s*db)'
            
            if re.search(patron_db_assign, contenido):
                # Agregar asignación de variable_service después de db
                contenido = re.sub(
                    patron_db_assign,
                    r'\1\n        self.variable_service = variable_service',
                    contenido
                )
                print("   ✅ Agregada asignación: self.variable_service = variable_service")
            
            # Crear backup
            backup_path = archivo_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(contenido_original)
            print(f"   💾 Backup creado: {backup_path}")
            
            # Escribir archivo corregido
            with open(archivo_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            print("   ✅ Constructor corregido exitosamente")
            return True
        
        else:
            print("   ❌ No se pudo encontrar patrón del constructor")
            
            # Buscar manualmente
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                if '    def __init__(' in linea and 'self' in linea:
                    print(f"   📋 Constructor encontrado manualmente en línea {i+1}: {linea}")
                    
                    # Corrección manual
                    if 'variable_service' not in linea:
                        linea_corregida = linea.replace(')', ', variable_service=None)')
                        lineas[i] = linea_corregida
                        
                        # Buscar donde agregar self.variable_service
                        for j in range(i+1, min(i+10, len(lineas))):
                            if 'self.db = db' in lineas[j]:
                                lineas.insert(j+1, '        self.variable_service = variable_service')
                                break
                        
                        # Escribir archivo corregido
                        contenido_corregido = '\n'.join(lineas)
                        
                        # Backup
                        backup_path = archivo_path + '.backup'
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            f.write(contenido_original)
                        
                        # Escribir corrección
                        with open(archivo_path, 'w', encoding='utf-8') as f:
                            f.write(contenido_corregido)
                        
                        print("   ✅ Corrección manual exitosa")
                        return True
            
            return False
        
    except Exception as e:
        print(f"   ❌ Error corrigiendo constructor: {e}")
        return False

def verificar_correccion(archivo_path):
    """Verifica que la corrección se aplicó correctamente"""
    print(f"\n🔍 VERIFICANDO CORRECCIÓN EN: {archivo_path}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar constructor
        constructor_ok = 'variable_service' in contenido and 'def __init__(' in contenido
        
        # Verificar asignación
        asignacion_ok = 'self.variable_service' in contenido
        
        print(f"   📋 Constructor acepta variable_service: {'✅' if constructor_ok else '❌'}")
        print(f"   📋 Asigna self.variable_service: {'✅' if asignacion_ok else '❌'}")
        
        if constructor_ok and asignacion_ok:
            print("   🎉 CORRECCIÓN EXITOSA")
            return True
        else:
            print("   ⚠️ CORRECCIÓN INCOMPLETA")
            return False
        
    except Exception as e:
        print(f"   ❌ Error verificando: {e}")
        return False

def probar_servidor():
    """Proporciona instrucciones para probar el servidor"""
    print(f"\n🚀 PROBANDO EL SERVIDOR...")
    print("="*50)
    
    print("📋 Pasos para probar:")
    print("1. Reiniciar el servidor:")
    print("   Ctrl+C para parar el servidor actual")
    print("   python main.py")
    print("")
    print("2. Probar el chat:")
    print("   Enviar mensaje 'Hola'")
    print("   Ya NO debería aparecer el error de constructor")
    print("")
    print("3. Verificar variables:")
    print("   Las variables {{saldo_total}} aún podrían no resolverse")
    print("   Ese será el siguiente paso a corregir")

def main():
    print("🔧 CORRECTOR INMEDIATO DE CONSTRUCTOR")
    print("="*50)
    print("🎯 Solucionando: ConfigurableFlowManager.__init__() takes 2 positional arguments but 3 were given")
    
    # Encontrar archivo
    archivo_flow = encontrar_configurable_flow_manager()
    
    if not archivo_flow:
        print("\n❌ No se pudo encontrar ConfigurableFlowManager")
        print("💡 Verificar que el archivo existe en el proyecto")
        return
    
    # Mostrar constructor actual
    if mostrar_constructor_actual(archivo_flow):
        # Corregir constructor
        if corregir_constructor(archivo_flow):
            # Verificar corrección
            if verificar_correccion(archivo_flow):
                print("\n🎉 PROBLEMA DE CONSTRUCTOR SOLUCIONADO")
                probar_servidor()
            else:
                print("\n⚠️ Corrección incompleta, revisar manualmente")
        else:
            print("\n❌ No se pudo corregir automáticamente")
    else:
        print("\n❌ No se pudo analizar el constructor")

if __name__ == "__main__":
    main()