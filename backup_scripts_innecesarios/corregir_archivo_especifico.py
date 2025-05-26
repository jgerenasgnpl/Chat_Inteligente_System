"""
Script para corregir un archivo específico de ConfigurableFlowManager
Uso: python corregir_archivo_especifico.py "ruta/al/archivo.py"
"""

import sys
import os
import re

def corregir_constructor_especifico(archivo_path):
    """Corrige el constructor específico del archivo dado"""
    print(f"🔧 CORRIGIENDO ARCHIVO: {archivo_path}")
    
    if not os.path.exists(archivo_path):
        print(f"❌ Archivo no encontrado: {archivo_path}")
        return False
    
    try:
        # Leer archivo
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido_original = f.read()
        
        print(f"📊 Tamaño del archivo: {len(contenido_original)} caracteres")
        
        # Mostrar constructor actual
        lineas = contenido_original.split('\n')
        constructor_encontrado = False
        linea_constructor = None
        
        for i, linea in enumerate(lineas):
            if 'class ConfigurableFlowManager' in linea:
                print(f"📋 Clase encontrada en línea {i+1}: {linea.strip()}")
                
                # Buscar constructor en las siguientes líneas
                for j in range(i+1, min(i+30, len(lineas))):
                    if '    def __init__(' in lineas[j]:
                        constructor_encontrado = True
                        linea_constructor = j
                        print(f"📋 Constructor en línea {j+1}: {lineas[j].strip()}")
                        
                        # Mostrar líneas del constructor
                        for k in range(j, min(j+10, len(lineas))):
                            if k == j or lineas[k].startswith('        '):
                                print(f"   {k+1:3d}: {lineas[k]}")
                            else:
                                break
                        break
                break
        
        if not constructor_encontrado:
            print("❌ Constructor no encontrado")
            return False
        
        # Analizar si ya tiene variable_service
        constructor_line = lineas[linea_constructor]
        
        if 'variable_service' in constructor_line:
            print("✅ El constructor ya acepta variable_service")
            
            # Verificar si se asigna
            if 'self.variable_service' in contenido_original:
                print("✅ Ya se asigna self.variable_service")
                print("🎯 El archivo ya está corregido")
                return True
            else:
                print("⚠️ Falta asignación de self.variable_service")
                # Solo agregar asignación
                return agregar_asignacion_variable_service(archivo_path, contenido_original)
        
        # Corregir constructor
        print("🔧 Corrigiendo constructor...")
        
        contenido_modificado = contenido_original
        
        # Método 1: Reemplazo directo del constructor
        patron_constructor = r'(def __init__\(self,\s*db[^)]*)\):'
        match = re.search(patron_constructor, constructor_line)
        
        if match:
            parte_antes = match.group(1)
            nueva_linea = parte_antes + ', variable_service=None):'
            
            print(f"   ANTES: {constructor_line.strip()}")
            print(f"   DESPUÉS: {nueva_linea}")
            
            # Reemplazar línea específica
            lineas[linea_constructor] = constructor_line.replace(
                match.group(0), 
                nueva_linea
            )
            
        else:
            # Método 2: Reemplazo manual
            print("   Usando método manual...")
            if constructor_line.endswith('):'):
                nueva_linea = constructor_line.replace(')', ', variable_service=None)')
                lineas[linea_constructor] = nueva_linea
                print(f"   CORREGIDO: {nueva_linea.strip()}")
        
        # Agregar asignación de variable_service
        asignacion_agregada = False
        for i in range(linea_constructor + 1, min(linea_constructor + 10, len(lineas))):
            if 'self.db = db' in lineas[i]:
                # Insertar después de self.db = db
                indentacion = '        '  # 8 espacios
                nueva_asignacion = indentacion + 'self.variable_service = variable_service'
                lineas.insert(i + 1, nueva_asignacion)
                print(f"   AGREGADO en línea {i+2}: {nueva_asignacion}")
                asignacion_agregada = True
                break
        
        if not asignacion_agregada:
            print("⚠️ No se pudo agregar asignación automáticamente")
        
        # Escribir archivo corregido
        contenido_nuevo = '\n'.join(lineas)
        
        # Crear backup
        backup_path = archivo_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(contenido_original)
        print(f"💾 Backup creado: {backup_path}")
        
        # Escribir corrección
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido_nuevo)
        
        print("✅ Archivo corregido exitosamente")
        
        # Verificar corrección
        return verificar_correccion_final(archivo_path)
        
    except Exception as e:
        print(f"❌ Error corrigiendo archivo: {e}")
        import traceback
        traceback.print_exc()
        return False

def agregar_asignacion_variable_service(archivo_path, contenido):
    """Solo agrega la asignación de self.variable_service"""
    print("🔧 Agregando asignación de self.variable_service...")
    
    lineas = contenido.split('\n')
    
    for i, linea in enumerate(lineas):
        if 'self.db = db' in linea:
            # Agregar después de esta línea
            indentacion = '        '
            nueva_linea = indentacion + 'self.variable_service = variable_service'
            lineas.insert(i + 1, nueva_linea)
            
            # Escribir archivo
            contenido_nuevo = '\n'.join(lineas)
            
            # Backup
            backup_path = archivo_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            # Escribir corrección
            with open(archivo_path, 'w', encoding='utf-8') as f:
                f.write(contenido_nuevo)
            
            print(f"✅ Asignación agregada en línea {i+2}")
            return True
    
    print("❌ No se encontró 'self.db = db' para agregar asignación")
    return False

def verificar_correccion_final(archivo_path):
    """Verifica que la corrección final sea exitosa"""
    print(f"\n🔍 VERIFICACIÓN FINAL: {archivo_path}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificaciones
        tiene_parametro = False
        tiene_asignacion = False
        
        # Buscar parámetro en constructor
        lineas = contenido.split('\n')
        for linea in lineas:
            if '    def __init__(' in linea and 'variable_service' in linea:
                tiene_parametro = True
                print(f"✅ Parámetro: {linea.strip()}")
                break
        
        # Buscar asignación
        if 'self.variable_service = variable_service' in contenido:
            tiene_asignacion = True
            print("✅ Asignación: self.variable_service = variable_service")
        
        if tiene_parametro and tiene_asignacion:
            print("🎉 CORRECCIÓN COMPLETA Y EXITOSA")
            return True
        else:
            print("⚠️ CORRECCIÓN INCOMPLETA")
            if not tiene_parametro:
                print("   ❌ Falta parámetro variable_service en constructor")
            if not tiene_asignacion:
                print("   ❌ Falta asignación self.variable_service")
            return False
        
    except Exception as e:
        print(f"❌ Error verificando: {e}")
        return False

def main():
    print("🔧 CORRECTOR DE ARCHIVO ESPECÍFICO")
    print("="*50)
    
    # Verificar argumentos
    if len(sys.argv) != 2:
        print("❌ Uso incorrecto")
        print("📋 Uso correcto: python corregir_archivo_especifico.py \"ruta/al/archivo.py\"")
        print("📋 Ejemplo: python corregir_archivo_especifico.py \"app/services/flow_manager.py\"")
        return
    
    archivo_path = sys.argv[1]
    
    # Corregir archivo
    if corregir_constructor_especifico(archivo_path):
        print("\n🎉 ARCHIVO CORREGIDO EXITOSAMENTE")
        print("\n📋 Próximos pasos:")
        print("1. Reiniciar el servidor:")
        print("   Ctrl+C para parar")
        print("   python main.py")
        print("2. Probar el chat - el error de constructor debería desaparecer")
        print("3. Si las variables {{}} aún no se resuelven, será el siguiente paso")
    else:
        print("\n❌ NO SE PUDO CORREGIR EL ARCHIVO")
        print("📋 Corrección manual necesaria")

if __name__ == "__main__":
    main()