from app.services.state_condition_bridge import StateConditionBridge
from app.db.session import SessionLocal

def test_proponer_planes_to_confirmar():
    """
    🧪 TEST ESPECÍFICO: proponer_planes_pago → confirmar_plan_elegido
    """
    
    db = SessionLocal()
    bridge = StateConditionBridge(db)
    
    # ✅ CASO 1: Usuario hace clic en "aceptar acuerdo"
    test_1 = bridge.determinar_siguiente_estado(
        estado_actual="proponer_planes_pago",
        mensaje="aceptar acuerdo",
        intencion_ml="CONFIRMACION_EXITOSA",
        contexto={
            "cliente_encontrado": True,
            "Nombre_del_cliente": "ALEXANDER RIVERA",
            "saldo_total": 69714817
        }
    )
    
    print("🧪 TEST 1: 'aceptar acuerdo'")
    print(f"   Estado actual: proponer_planes_pago")
    print(f"   Mensaje: 'aceptar acuerdo'")
    print(f"   Intención ML: CONFIRMACION_EXITOSA")
    print(f"   ➜ Siguiente estado: {test_1['siguiente_estado']}")
    print(f"   ➜ Condición: {test_1['condicion_evaluada']}")
    print(f"   ➜ Cumplida: {test_1['condicion_cumplida']}")
    print(f"   ➜ Razón: {test_1['razon_transicion']}")
    print()
    
    # ✅ CASO 2: Usuario dice "acepto" 
    test_2 = bridge.determinar_siguiente_estado(
        estado_actual="proponer_planes_pago",
        mensaje="acepto",
        intencion_ml="CONFIRMACION",
        contexto={
            "cliente_encontrado": True,
            "Nombre_del_cliente": "ALEXANDER RIVERA"
        }
    )
    
    print("🧪 TEST 2: 'acepto'")
    print(f"   ➜ Siguiente estado: {test_2['siguiente_estado']}")
    print(f"   ➜ Condición cumplida: {test_2['condicion_cumplida']}")
    print()
    
    # ✅ CASO 3: Usuario dice "plan 1"
    test_3 = bridge.determinar_siguiente_estado(
        estado_actual="proponer_planes_pago", 
        mensaje="plan 1",
        intencion_ml="PLAN_SELECCIONADO",
        contexto={"cliente_encontrado": True}
    )
    
    print("🧪 TEST 3: 'plan 1'")
    print(f"   ➜ Siguiente estado: {test_3['siguiente_estado']}")
    print(f"   ➜ Condición cumplida: {test_3['condicion_cumplida']}")
    print()
    
    # ✅ VERIFICAR CONFIGURACIÓN DEL ESTADO
    config = bridge.get_posibles_transiciones("proponer_planes_pago")
    print("🔧 CONFIGURACIÓN DE 'proponer_planes_pago':")
    print(f"   Condición requerida: {config['condicion_requerida']}")
    print(f"   Acción: {config['accion']}")
    print(f"   Si cumple: {config['posibles_destinos']['si_cumple']}")
    print(f"   Si no cumple: {config['posibles_destinos']['si_no_cumple']}")
    print(f"   Por defecto: {config['posibles_destinos']['por_defecto']}")
    print()
    
    # ✅ DEBUG DETALLADO
    debug = bridge.debug_evaluacion(
        "proponer_planes_pago",
        "aceptar acuerdo", 
        "CONFIRMACION_EXITOSA"
    )
    
    print("🔍 DEBUG DETALLADO:")
    print(f"   Condición BD: {debug['condicion_bd']}")
    print(f"   Mapeo intención: {debug['mapeo_intencion']}")
    print(f"   Keywords detectadas: {debug['keywords_detectadas']}")
    print(f"   Condición cumplida: {debug['condicion_cumplida']}")
    
    db.close()
    
    # ✅ RESULTADO ESPERADO
    expected = "confirmar_plan_elegido"
    actual = test_1['siguiente_estado']
    
    print(f"\n✅ RESULTADO:")
    print(f"   Esperado: {expected}")
    print(f"   Obtenido: {actual}")
    print(f"   ¿Correcto? {'✅ SÍ' if actual == expected else '❌ NO'}")
    
    return actual == expected

# EJECUTAR TEST
if __name__ == "__main__":
    resultado = test_proponer_planes_to_confirmar()
    print(f"\n🎯 TEST {'EXITOSO' if resultado else 'FALLIDO'}")