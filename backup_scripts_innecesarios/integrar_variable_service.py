"""
Script para integrar el variable_service en el conversation_manager
para que las variables se resuelvan correctamente en el chat real
"""

import os
import re
import glob

def encontrar_conversation_manager():
    """Encuentra el archivo conversation_manager"""
    archivos_posibles = [
        "app/services/conversation_manager.py",
        "app/conversation_manager.py",
        "conversation_manager.py",
        "app/core/conversation_manager.py"
    ]
    
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            return archivo
    
    # Buscar recursivamente
    archivos_encontrados = glob.glob("**/conversation_manager.py", recursive=True)
    if archivos_encontrados:
        return archivos_encontrados[0]
    
    return None

def encontrar_router_chat():
    """Encuentra el router de chat"""
    archivos_posibles = [
        "app/routers/chat.py",
        "app/api/chat.py", 
        "app/routes/chat.py",
        "routers/chat.py"
    ]
    
    for archivo in archivos_posibles:
        if os.path.exists(archivo):
            return archivo
    
    archivos_encontrados = glob.glob("**/chat.py", recursive=True)
    for archivo in archivos_encontrados:
        if 'router' in archivo or 'api' in archivo or 'route' in archivo:
            return archivo
    
    return None

def actualizar_conversation_manager(archivo_path):
    """Actualiza el conversation manager para usar variable_service"""
    print(f"🔧 ACTUALIZANDO: {archivo_path}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar si ya tiene variable_service
        if 'variable_service' in contenido:
            print("   ✅ Ya tiene variable_service importado")
            return True
        
        # Agregar import del variable_service
        import_variable_service = "from app.services.variable_service import VariableService"
        
        # Encontrar donde agregar el import
        lineas = contenido.split('\n')
        nueva_lineas = []
        import_agregado = False
        
        for i, linea in enumerate(lineas):
            nueva_lineas.append(linea)
            
            # Agregar después de otros imports de services
            if ('from app.services' in linea or 'from .services' in linea) and not import_agregado:
                nueva_lineas.append(import_variable_service)
                import_agregado = True
        
        # Si no se agregó, buscar después de imports generales
        if not import_agregado:
            for i, linea in enumerate(nueva_lineas):
                if linea.startswith('class ') or linea.startswith('def '):
                    nueva_lineas.insert(i, import_variable_service)
                    nueva_lineas.insert(i+1, "")
                    import_agregado = True
                    break
        
        # Actualizar constructor para incluir variable_service
        contenido_nuevo = '\n'.join(nueva_lineas)
        
        # Buscar el constructor y agregar variable_service
        patron_init = r'def __init__\(self,([^)]*)\):'
        match = re.search(patron_init, contenido_nuevo)
        
        if match:
            params_actuales = match.group(1).strip()
            if 'db:' in params_actuales and 'variable_service' not in params_actuales:
                nuevos_params = params_actuales
                if params_actuales and not params_actuales.endswith(','):
                    nuevos_params += ','
                nuevos_params += ' variable_service: VariableService = None'
                
                contenido_nuevo = contenido_nuevo.replace(
                    f"def __init__(self,{params_actuales}):",
                    f"def __init__(self,{nuevos_params}):"
                )
                
                # Agregar inicialización en el constructor
                patron_db_assign = r'self\.db\s*=\s*db'
                if re.search(patron_db_assign, contenido_nuevo):
                    contenido_nuevo = re.sub(
                        patron_db_assign,
                        'self.db = db\n        self.variable_service = variable_service or VariableService(db)',
                        contenido_nuevo
                    )
        
        # Buscar método que genera respuestas y agregar resolución de variables
        metodos_respuesta = [
            'procesar_mensaje',
            'generar_respuesta', 
            'process_message',
            'handle_message',
            'get_response'
        ]
        
        for metodo in metodos_respuesta:
            patron_metodo = f'def {metodo}\\([^)]*\\):'
            if re.search(patron_metodo, contenido_nuevo):
                # Buscar donde se devuelve la respuesta
                lineas_metodo = contenido_nuevo.split('\n')
                for i, linea in enumerate(lineas_metodo):
                    if f'def {metodo}(' in linea:
                        # Buscar el return de este método
                        nivel_indentacion = len(linea) - len(linea.lstrip())
                        for j in range(i+1, len(lineas_metodo)):
                            linea_actual = lineas_metodo[j]
                            
                            # Si encontramos un return que devuelve texto/mensaje
                            if ('return' in linea_actual and 
                                ('message' in linea_actual or 'response' in linea_actual or 'texto' in linea_actual)):
                                
                                # Agregar resolución de variables antes del return
                                indentacion = ' ' * (nivel_indentacion + 8)
                                linea_resolucion = f"{indentacion}# Resolver variables antes de devolver respuesta"
                                linea_resolucion2 = f"{indentacion}if hasattr(self, 'variable_service') and self.variable_service:"
                                linea_resolucion3 = f"{indentacion}    respuesta_final = self.variable_service.resolver_variables(respuesta_final, contexto)"
                                
                                # Insertar antes del return
                                lineas_metodo.insert(j, linea_resolucion)
                                lineas_metodo.insert(j+1, linea_resolucion2)
                                lineas_metodo.insert(j+2, linea_resolucion3)
                                lineas_metodo.insert(j+3, "")
                                break
                        break
                
                contenido_nuevo = '\n'.join(lineas_metodo)
                break
        
        # Escribir archivo actualizado
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido_nuevo)
        
        print("   ✅ Conversation manager actualizado")
        return True
        
    except Exception as e:
        print(f"   ❌ Error actualizando conversation manager: {e}")
        return False

def actualizar_router_chat(archivo_path):
    """Actualiza el router de chat para incluir variable_service"""
    print(f"🔧 ACTUALIZANDO ROUTER: {archivo_path}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Verificar si ya tiene variable_service
        if 'VariableService' in contenido:
            print("   ✅ Ya tiene VariableService en router")
            return True
        
        # Agregar import
        import_variable = "from app.services.variable_service import VariableService"
        
        lineas = contenido.split('\n')
        nueva_lineas = []
        import_agregado = False
        
        for linea in lineas:
            nueva_lineas.append(linea)
            
            # Agregar después de imports de services
            if 'from app.services' in linea and 'variable_service' not in linea and not import_agregado:
                nueva_lineas.append(import_variable)
                import_agregado = True
        
        if not import_agregado:
            # Agregar al inicio de imports
            for i, linea in enumerate(nueva_lineas):
                if linea.startswith('from ') or linea.startswith('import '):
                    nueva_lineas.insert(i, import_variable)
                    import_agregado = True
                    break
        
        contenido_nuevo = '\n'.join(nueva_lineas)
        
        # Buscar donde se instancia el conversation_manager y agregar variable_service
        patron_manager = r'(\w+Manager\([^)]*)\)'
        matches = re.finditer(patron_manager, contenido_nuevo)
        
        for match in matches:
            instancia_actual = match.group(1)
            if 'db' in instancia_actual and 'variable_service' not in instancia_actual:
                # Agregar variable_service a la instancia
                nueva_instancia = instancia_actual + ', VariableService(db)'
                contenido_nuevo = contenido_nuevo.replace(
                    instancia_actual + ')',
                    nueva_instancia + ')'
                )
                break
        
        # Escribir archivo actualizado
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido_nuevo)
        
        print("   ✅ Router de chat actualizado")
        return True
        
    except Exception as e:
        print(f"   ❌ Error actualizando router: {e}")
        return False

def crear_ejemplo_uso():
    """Crea un ejemplo de cómo usar variable_service correctamente"""
    print("📝 CREANDO EJEMPLO DE USO...")
    
    ejemplo = '''# ejemplo_variable_service.py
"""
Ejemplo de cómo usar correctamente el VariableService
"""

from app.services.variable_service import VariableService

def ejemplo_resolucion_variables(db, mensaje_con_variables, contexto_conversacion):
    """
    Ejemplo de cómo resolver variables en mensajes
    """
    
    # 1. Crear instancia del servicio
    variable_service = VariableService(db)
    
    # 2. Preparar contexto con datos específicos de la conversación
    contexto = {
        'saldo': 18500,  # Saldo real del cliente
        'nombre_cliente': 'Juan Pérez',
        'entidad': 'Banco Nacional',
        'descuento': 15,
        'num_cuotas': 6,
        'conversation_id': 123
    }
    
    # 3. Combinar con contexto general si existe
    if contexto_conversacion:
        contexto.update(contexto_conversacion)
    
    # 4. Resolver variables en el mensaje
    mensaje_resuelto = variable_service.resolver_variables(
        mensaje_con_variables, 
        contexto
    )
    
    return mensaje_resuelto

# Ejemplo de uso en conversation_manager:
class ConversationManager:
    def __init__(self, db, variable_service=None):
        self.db = db
        self.variable_service = variable_service or VariableService(db)
    
    def procesar_mensaje(self, user_message, conversation_id):
        # ... lógica de procesamiento ...
        
        # Obtener respuesta base
        respuesta_base = self._get_response_template(estado_actual)
        
        # Preparar contexto
        contexto = {
            'conversation_id': conversation_id,
            'saldo': self._get_saldo_cliente(conversation_id),
            'nombre_cliente': self._get_nombre_cliente(conversation_id),
            # ... otros datos del contexto ...
        }
        
        # IMPORTANTE: Resolver variables antes de devolver
        respuesta_final = self.variable_service.resolver_variables(
            respuesta_base, 
            contexto
        )
        
        return {
            'message': respuesta_final,
            'estado': estado_actual,
            'contexto': contexto
        }
'''
    
    with open("ejemplo_variable_service.py", "w", encoding="utf-8") as f:
        f.write(ejemplo)
    
    print("   ✅ ejemplo_variable_service.py creado")

def main():
    print("🔧 INTEGRADOR DE VARIABLE SERVICE")
    print("="*50)
    
    # Verificar directorio
    if not os.path.exists('main.py'):
        print("❌ Ejecutar desde el directorio que contiene main.py")
        return
    
    try:
        # Encontrar archivos
        conversation_manager = encontrar_conversation_manager()
        router_chat = encontrar_router_chat()
        
        print(f"📋 Archivos encontrados:")
        print(f"   📄 Conversation Manager: {conversation_manager or 'NO ENCONTRADO'}")
        print(f"   📄 Router Chat: {router_chat or 'NO ENCONTRADO'}")
        
        exito = True
        
        # Actualizar conversation_manager
        if conversation_manager:
            if not actualizar_conversation_manager(conversation_manager):
                exito = False
        else:
            print("   ⚠️ No se encontró conversation_manager.py")
            exito = False
        
        # Actualizar router de chat
        if router_chat:
            if not actualizar_router_chat(router_chat):
                exito = False
        else:
            print("   ⚠️ No se encontró router de chat")
        
        # Crear ejemplo
        crear_ejemplo_uso()
        
        if exito:
            print("\n🎉 INTEGRACIÓN COMPLETADA")
            print("\n📋 Próximos pasos:")
            print("1. Reiniciar el servidor FastAPI")
            print("2. Probar el chat - las variables {{}} ahora deberían resolverse")
            print("3. Verificar logs para confirmar resolución")
        else:
            print("\n⚠️ INTEGRACIÓN PARCIAL")
            print("Algunos archivos no se pudieron actualizar automáticamente")
            print("Verificar manualmente la integración del VariableService")
        
    except Exception as e:
        print(f"\n❌ Error durante integración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()