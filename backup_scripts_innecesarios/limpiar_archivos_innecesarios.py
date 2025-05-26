"""
Script para eliminar archivos de diagnóstico y corrección ya innecesarios
"""

import os
import glob

def identificar_archivos_innecesarios():
    """Identifica archivos que ya no son necesarios"""
    
    archivos_innecesarios = [
        # Scripts de diagnóstico ya ejecutados
        "debug_conversation_flow.py",
        "verificar_router_chat.py", 
        "buscar_flow_manager_real.py",
        
        # Scripts de corrección ya ejecutados
        "corregir_constructor_flow_manager.py",
        "corregir_archivo_especifico.py",
        "encontrar_flow_manager.py",
        "integrar_variable_service.py",
        
        # Scripts de ejemplo/prueba
        "ejemplo_variable_service.py",
        "test_variables.py",
        "verificacion_final.py",
        
        # Este mismo script de limpieza (después de ejecutar)
        "limpiar_archivos_innecesarios.py"
    ]
    
    archivos_existentes = []
    archivos_no_encontrados = []
    
    print("🗑️ IDENTIFICANDO ARCHIVOS INNECESARIOS...")
    print("="*50)
    
    for archivo in archivos_innecesarios:
        if os.path.exists(archivo):
            archivos_existentes.append(archivo)
            tamaño = os.path.getsize(archivo)
            print(f"   📄 {archivo} ({tamaño} bytes)")
        else:
            archivos_no_encontrados.append(archivo)
    
    print(f"\n📊 RESUMEN:")
    print(f"   📄 Archivos encontrados: {len(archivos_existentes)}")
    print(f"   ❌ Archivos no encontrados: {len(archivos_no_encontrados)}")
    
    return archivos_existentes

def crear_backup_antes_eliminar(archivos):
    """Crea un backup de los archivos antes de eliminarlos"""
    print(f"\n💾 CREANDO BACKUP...")
    
    backup_dir = "backup_scripts_innecesarios"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"   📁 Directorio creado: {backup_dir}")
    
    for archivo in archivos:
        try:
            # Copiar archivo al backup
            import shutil
            backup_path = os.path.join(backup_dir, archivo)
            shutil.copy2(archivo, backup_path)
            print(f"   ✅ Backup: {archivo} -> {backup_path}")
        except Exception as e:
            print(f"   ❌ Error backup {archivo}: {e}")

def eliminar_archivos(archivos):
    """Elimina los archivos innecesarios"""
    print(f"\n🗑️ ELIMINANDO ARCHIVOS...")
    
    eliminados = 0
    errores = 0
    
    for archivo in archivos:
        try:
            os.remove(archivo)
            print(f"   ✅ Eliminado: {archivo}")
            eliminados += 1
        except Exception as e:
            print(f"   ❌ Error eliminando {archivo}: {e}")
            errores += 1
    
    print(f"\n📊 RESULTADO:")
    print(f"   ✅ Archivos eliminados: {eliminados}")
    print(f"   ❌ Errores: {errores}")

def mostrar_archivos_importantes():
    """Muestra los archivos importantes que SÍ deben mantenerse"""
    print(f"\n📋 ARCHIVOS IMPORTANTES (NO TOCAR):")
    print("="*50)
    
    archivos_importantes = [
        "main.py",
        "app/services/variable_service.py",
        "app/api/endpoints/chat.py", 
        "app/models/",
        "app/schemas/",
        "app/crud/",
        "app/core/",
        "app/db/"
    ]
    
    for archivo in archivos_importantes:
        if os.path.exists(archivo):
            if os.path.isfile(archivo):
                print(f"   📄 {archivo}")
            else:
                print(f"   📁 {archivo}/")
        else:
            print(f"   ⚠️ {archivo} (no encontrado)")

def main():
    print("🧹 LIMPIADOR DE ARCHIVOS INNECESARIOS")
    print("="*60)
    
    # Identificar archivos
    archivos = identificar_archivos_innecesarios()
    
    if not archivos:
        print("\n✅ No hay archivos innecesarios para eliminar")
        return
    
    # Mostrar archivos importantes
    mostrar_archivos_importantes()
    
    # Confirmar eliminación
    print(f"\n❓ ¿Eliminar {len(archivos)} archivos innecesarios?")
    print("   Los archivos se respaldarán antes de eliminar")
    print("   Escribir 'SI' para confirmar:")
    
    confirmacion = input().strip().upper()
    
    if confirmacion == 'SI':
        # Crear backup
        crear_backup_antes_eliminar(archivos)
        
        # Eliminar archivos
        eliminar_archivos(archivos)
        
        print("\n🎉 LIMPIEZA COMPLETADA")
        print("\nℹ️ Si necesitas recuperar algún archivo:")
        print("   📁 Revisa: backup_scripts_innecesarios/")
        
    else:
        print("\n❌ Limpieza cancelada")

if __name__ == "__main__":
    main()