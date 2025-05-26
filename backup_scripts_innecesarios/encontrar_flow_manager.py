"""
Script para encontrar y corregir ConfigurableFlowManager
para que use correctamente el VariableService
"""

import os
import glob
import re

def encontrar_configurable_flow_manager():
    """Encuentra el archivo ConfigurableFlowManager"""
    print("🔍 BUSCANDO ConfigurableFlowManager...")
    
    # Buscar archivos que contengan ConfigurableFlowManager
    archivos_py = glob.glob("**/*.py", recursive=True)
    
    archivos_encontrados = []
    
    for archivo in archivos_py:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
                if 'class ConfigurableFlowManager' in contenido:
                    archivos_encontrados.append(archivo)
                    print(f"   ✅ ENCONTRADO: {archivo}")
                    
        except Exception as e:
            continue
    
    return archivos_encontrados

def analizar_flow_manager(archivo_path):
    """Analiza el ConfigurableFlowManager para ver si usa VariableService"""
    print(f"\n🔍 ANALIZANDO: {archivo_path}")