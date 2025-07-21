# ARCHIVO: fix_datos_incorrectos.py
# CORRECCIONES ESPECÍFICAS PARA DATOS INCORRECTOS

"""
🎯 SCRIPT PARA CORREGIR DATOS INCORRECTOS EN EL SISTEMA
Aplica las 3 correcciones principales identificadas
"""

import json
from typing import Dict, Any
from datetime import datetime

# ==========================================
# 1. CORRECCIÓN EN conversation_service.py
# ==========================================

def build_client_context_CORREGIDO(cliente_info: Dict[str, Any], cedula: str) -> Dict[str, Any]:
    """✅ CORREGIDO - Usar datos directos sin anidamiento 'datos'"""
    
    print(f"🔧 [CLIENT_CONTEXT] Construyendo contexto para: {cliente_info.get('nombre', 'N/A')}")
    print(f"📊 [CLIENT_CONTEXT] Saldo recibido: ${cliente_info.get('saldo', 0):,}")
    
    return {
        "cedula_detectada": cedula,
        "cliente_encontrado": True,
        
        # ✅ ACCESO DIRECTO - NO 'datos.get()'
        "Nombre_del_cliente": cliente_info.get("nombre", "Cliente"),
        "saldo_total": cliente_info.get("saldo", 0),
        "banco": cliente_info.get("banco", "Entidad Financiera"),
        "oferta_1": cliente_info.get("oferta_1", 0),
        "oferta_2": cliente_info.get("oferta_2", 0),
        "hasta_3_cuotas": cliente_info.get("hasta_3_cuotas", 0),
        "hasta_6_cuotas": cliente_info.get("hasta_6_cuotas", 0),
        "hasta_12_cuotas": cliente_info.get("hasta_12_cuotas", 0),
        "producto": cliente_info.get("producto", "Producto"),
        "telefono": cliente_info.get("telefono", ""),
        "email": cliente_info.get("email", ""),
        
        # ✅ METADATA
        "consulta_timestamp": datetime.now().isoformat(),
        "consulta_method": "direct_client_data",
        "data_source": "real_database_query"
    }

# ==========================================
# 2. CORRECCIÓN EN variable_service.py
# ==========================================

def combinar_datos_CORREGIDO(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """✅ CORREGIDO - Prioridad ABSOLUTA a datos reales del cliente"""
    
    # 1. VERIFICAR DATOS REALES
    cliente_real = (
        contexto.get("cliente_encontrado") == True and
        contexto.get("saldo_total", 0) > 0 and
        len(str(contexto.get("Nombre_del_cliente", ""))) > 2
    )
    
    print(f"🔍 [COMBINAR] Cliente real detectado: {cliente_real}")
    
    if cliente_real:
        print(f"✅ [COMBINAR] DATOS REALES CONFIRMADOS:")
        print(f"   Nombre: {contexto.get('Nombre_del_cliente')}")
        print(f"   Saldo: ${contexto.get('saldo_total', 0):,}")
        print(f"   Banco: {contexto.get('banco')}")
        
        # ✅ RETORNAR SOLO DATOS REALES
        return contexto.copy()
    
    else:
        print(f"⚠️ [COMBINAR] Usando datos por defecto del sistema")
        
        # Variables básicas por defecto
        variables_sistema = {
            "saldo_total": 15000,
            "Nombre_del_cliente": "Cliente", 
            "banco": "Entidad Financiera",
            "oferta_1": 0,
            "oferta_2": 0,
            "hasta_3_cuotas": 0,
            "hasta_6_cuotas": 0,
            "hasta_12_cuotas": 0
        }
        
        # Combinar con prioridad al contexto
        resultado = {}
        resultado.update(variables_sistema)
        resultado.update(contexto)
        
        return resultado

# ==========================================
# 3. CORRECCIÓN EN PERSISTENCIA DE CONTEXTO
# ==========================================

def update_context_PRESERVANDO_CLIENTE(context_data: str, updates: Dict) -> str:
    """✅ CORREGIDO - Preservar datos del cliente al actualizar contexto"""
    
    try:
        # 1. OBTENER CONTEXTO ACTUAL
        current_context = {}
        if context_data:
            try:
                current_context = json.loads(context_data)
            except:
                current_context = {}
        
        # 2. IDENTIFICAR DATOS DEL CLIENTE
        client_keys = {
            'cliente_encontrado', 'Nombre_del_cliente', 'saldo_total',
            'banco', 'oferta_1', 'oferta_2', 'hasta_3_cuotas', 
            'hasta_6_cuotas', 'hasta_12_cuotas', 'cedula_detectada'
        }
        
        # 3. PRESERVAR DATOS REALES
        for key, new_value in updates.items():
            current_value = current_context.get(key)
            
            if key in client_keys and current_value:
                # Si hay datos del cliente, no sobrescribir con 0 o valores genéricos
                if (isinstance(new_value, (int, float)) and new_value == 0 and 
                    isinstance(current_value, (int, float)) and current_value > 0):
                    print(f"🛡️ [PRESERVAR] Manteniendo {key}: {current_value} (no sobrescribir con {new_value})")
                    continue
                    
                if (isinstance(new_value, str) and new_value in ["Cliente", "Entidad Financiera"] and
                    isinstance(current_value, str) and len(current_value) > 5):
                    print(f"🛡️ [PRESERVAR] Manteniendo {key}: {current_value} (no sobrescribir con genérico)")
                    continue
            
            # Actualizar valor
            current_context[key] = new_value
        
        # 4. RETORNAR CONTEXTO ACTUALIZADO
        context_json = json.dumps(current_context, ensure_ascii=False, default=str)
        
        # 5. LOG DE VERIFICACIÓN
        if current_context.get("cliente_encontrado"):
            print(f"✅ [CONTEXTO] Cliente preservado: {current_context.get('Nombre_del_cliente')}")
            print(f"✅ [CONTEXTO] Saldo preservado: ${current_context.get('saldo_total', 0):,}")
        
        return context_json
        
    except Exception as e:
        print(f"❌ Error actualizando contexto: {e}")
        return context_data or "{}"

# ==========================================
# 4. FUNCIÓN DE VALIDACIÓN
# ==========================================

def validar_datos_cliente(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """Validar que los datos del cliente sean correctos"""
    
    issues = []
    
    # Verificar datos básicos
    if not contexto.get("cliente_encontrado"):
        issues.append("cliente_encontrado es False")
    
    if not contexto.get("Nombre_del_cliente") or contexto.get("Nombre_del_cliente") == "Cliente":
        issues.append("Nombre genérico o faltante")
    
    saldo = contexto.get("saldo_total", 0)
    if not saldo or saldo <= 0:
        issues.append(f"Saldo inválido: {saldo}")
    
    if not contexto.get("banco") or contexto.get("banco") == "Entidad Financiera":
        issues.append("Banco genérico o faltante")
    
    return {
        "valido": len(issues) == 0,
        "issues": issues,
        "datos_cliente": {
            "nombre": contexto.get("Nombre_del_cliente"),
            "saldo": contexto.get("saldo_total"),
            "banco": contexto.get("banco"),
            "cliente_encontrado": contexto.get("cliente_encontrado")
        }
    }

# ==========================================
# 5. FUNCIÓN DE TEST
# ==========================================

def test_correccion_datos():
    """Test para verificar que las correcciones funcionan"""
    
    print("🧪 INICIANDO TESTS DE CORRECCIÓN DE DATOS")
    print("=" * 50)
    
    # Datos de prueba reales
    cliente_info_real = {
        "nombre": "MARIA ANGELICA ESCOBAR RODRIGUEZ",
        "saldo": 4173695,
        "banco": "Scotiabank - Colpatria",
        "oferta_1": 2086847,
        "oferta_2": 1873823,
        "hasta_3_cuotas": 867415,
        "hasta_6_cuotas": 434708
    }
    
    # Test 1: Construcción de contexto
    print("\n🧪 TEST 1: Construcción de contexto del cliente")
    contexto = build_client_context_CORREGIDO(cliente_info_real, "1016020871")
    
    print(f"📊 Resultado del contexto:")
    print(f"   Nombre: {contexto['Nombre_del_cliente']}")
    print(f"   Saldo: ${contexto['saldo_total']:,}")
    print(f"   Banco: {contexto['banco']}")
    
    assert contexto["Nombre_del_cliente"] == "MARIA ANGELICA ESCOBAR RODRIGUEZ"
    assert contexto["saldo_total"] == 4173695
    assert contexto["banco"] == "Scotiabank - Colpatria"
    print("✅ Test 1 PASÓ")
    
    # Test 2: Validación de datos
    print("\n🧪 TEST 2: Validación de datos")
    validacion = validar_datos_cliente(contexto)
    
    print(f"📊 Resultado de validación:")
    print(f"   Válido: {validacion['valido']}")
    print(f"   Issues: {validacion['issues']}")
    
    assert validacion["valido"] == True
    assert len(validacion["issues"]) == 0
    print("✅ Test 2 PASÓ")
    
    # Test 3: Combinación de datos
    print("\n🧪 TEST 3: Combinación de datos")
    datos_combinados = combinar_datos_CORREGIDO(contexto)
    
    print(f"📊 Datos combinados:")
    print(f"   Cliente encontrado: {datos_combinados.get('cliente_encontrado')}")
    print(f"   Nombre: {datos_combinados.get('Nombre_del_cliente')}")
    print(f"   Saldo: ${datos_combinados.get('saldo_total', 0):,}")
    
    assert datos_combinados["Nombre_del_cliente"] == "MARIA ANGELICA ESCOBAR RODRIGUEZ"
    assert datos_combinados["saldo_total"] == 4173695
    print("✅ Test 3 PASÓ")
    
    # Test 4: Preservación de contexto
    print("\n🧪 TEST 4: Preservación de contexto")
    context_json = json.dumps(contexto)
    
    # Simular actualizaciones que NO deben sobrescribir datos reales
    updates_maliciosas = {
        "saldo_total": 0,  # ❌ Intento de sobrescribir con 0
        "Nombre_del_cliente": "Cliente",  # ❌ Intento de sobrescribir con genérico
        "banco": "Entidad Financiera",  # ❌ Intento de sobrescribir con genérico
        "nueva_variable": "OK"  # ✅ Esta sí debe actualizarse
    }
    
    context_actualizado = update_context_PRESERVANDO_CLIENTE(context_json, updates_maliciosas)
    datos_preservados = json.loads(context_actualizado)
    
    print(f"📊 Después de intentos de sobrescritura:")
    print(f"   Nombre preservado: {datos_preservados.get('Nombre_del_cliente')}")
    print(f"   Saldo preservado: ${datos_preservados.get('saldo_total', 0):,}")
    print(f"   Nueva variable: {datos_preservados.get('nueva_variable')}")
    
    # Verificar que los datos importantes NO fueron sobrescritos
    assert datos_preservados["Nombre_del_cliente"] == "MARIA ANGELICA ESCOBAR RODRIGUEZ"
    assert datos_preservados["saldo_total"] == 4173695
    assert datos_preservados["banco"] == "Scotiabank - Colpatria"
    # Pero la nueva variable sí debe estar
    assert datos_preservados["nueva_variable"] == "OK"
    print("✅ Test 4 PASÓ")
    
    print("\n" + "=" * 50)
    print("🎉 TODOS LOS TESTS PASARON - CORRECCIONES FUNCIONAN CORRECTAMENTE")
    
    # Mostrar el código que se debe aplicar
    print("\n🔧 CORRECCIONES A APLICAR:")
    print("1. En conversation_service.py, método _build_client_context:")
    print("   - Cambiar datos_cliente.get() por cliente_info.get()")
    print("2. En variable_service.py, método _combinar_datos_contexto_y_sistema_FIXED:")
    print("   - Dar prioridad absoluta a datos del cliente")
    print("3. En conversation_service.py, método _update_context_simple:")
    print("   - Preservar datos del cliente al actualizar contexto")
    
    return True

if __name__ == "__main__":
    test_correccion_datos()