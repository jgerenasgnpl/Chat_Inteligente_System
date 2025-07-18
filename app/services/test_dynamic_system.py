"""
CREAR NUEVO ARCHIVO: test_dynamic_system.py
Para probar el sistema dinámico
"""

import asyncio
from app.db.session import SessionLocal
from app.services.dynamic_transition_service import create_dynamic_transition_service

async def test_complete_dynamic_system():
    """Test completo del sistema dinámico"""
    
    print("🧪 INICIANDO TEST DEL SISTEMA 100% DINÁMICO")
    print("=" * 60)
    
    db = SessionLocal()
    dynamic_service = create_dynamic_transition_service(db)
    
    # Test cases específicos para el problema original
    test_cases = [
        {
            "name": "Caso 1: Acepto en proponer_planes_pago",
            "current_state": "proponer_planes_pago",
            "message": "acepto",
            "ml_result": {"intention": "CONFIRMACION_EXITOSA", "confidence": 0.9},
            "context": {"cliente_encontrado": True, "Nombre_del_cliente": "PEDRO VARGAS"},
            "expected_state": "confirmar_plan_elegido"
        },
        {
            "name": "Caso 2: Aceptar acuerdo",
            "current_state": "proponer_planes_pago", 
            "message": "aceptar acuerdo",
            "ml_result": {"intention": "CONFIRMACION_EXITOSA", "confidence": 0.9},
            "context": {"cliente_encontrado": True, "Nombre_del_cliente": "ALEXANDER RIVERA"},
            "expected_state": "confirmar_plan_elegido"
        },
        {
            "name": "Caso 3: Plan 1",
            "current_state": "proponer_planes_pago",
            "message": "plan 1",
            "ml_result": {"intention": "PLAN_SELECCIONADO", "confidence": 0.95},
            "context": {"cliente_encontrado": True},
            "expected_state": "confirmar_plan_elegido"
        },
        {
            "name": "Caso 4: Cédula detectada",
            "current_state": "validar_documento",
            "message": "93388915",
            "ml_result": {"intention": "IDENTIFICACION", "confidence": 0.95},
            "context": {},
            "expected_state": "informar_deuda"
        },
        {
            "name": "Caso 5: Solicitud de opciones",
            "current_state": "informar_deuda",
            "message": "si quiero ver opciones",
            "ml_result": {"intention": "CONFIRMACION", "confidence": 0.8},
            "context": {"cliente_encontrado": True},
            "expected_state": "proponer_planes_pago"
        }
    ]
    
    # Ejecutar tests
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test['name']}")
        print(f"   Estado actual: {test['current_state']}")
        print(f"   Mensaje: '{test['message']}'")
        print(f"   ML: {test['ml_result']['intention']} ({test['ml_result']['confidence']})")
        
        try:
            result = dynamic_service.determine_next_state(
                current_state=test['current_state'],
                user_message=test['message'],
                ml_result=test['ml_result'],
                context=test['context']
            )
            
            actual_state = result['next_state']
            expected_state = test['expected_state']
            
            if actual_state == expected_state:
                print(f"   ✅ PASÓ: {test['current_state']} → {actual_state}")
                print(f"   📊 Método: {result.get('detection_method')}")
                print(f"   ⚡ Tiempo: {result.get('execution_time_ms', 0):.1f}ms")
                passed += 1
            else:
                print(f"   ❌ FALLÓ: Esperado '{expected_state}', obtuvo '{actual_state}'")
                print(f"   📊 Método: {result.get('detection_method')}")
                print(f"   🔍 Condición: {result.get('condition_detected')}")
                failed += 1
                
        except Exception as e:
            print(f"   💥 ERROR: {e}")
            failed += 1
    
    # Estadísticas finales
    print("\n" + "=" * 60)
    print(f"📊 RESULTADOS FINALES:")
    print(f"   ✅ Pasaron: {passed}/{len(test_cases)}")
    print(f"   ❌ Fallaron: {failed}/{len(test_cases)}")
    print(f"   📈 Tasa de éxito: {(passed/len(test_cases)*100):.1f}%")
    
    # Estadísticas del sistema
    print(f"\n📋 ESTADÍSTICAS DEL SISTEMA:")
    stats = dynamic_service.get_stats()
    print(f"   🎯 ML mappings: {stats['configuration']['ml_mappings_count']}")
    print(f"   🔤 Keyword patterns: {stats['configuration']['keyword_patterns_count']}")
    print(f"   ⚙️ Evaluadores: {stats['configuration']['condition_evaluators_count']}")
    print(f"   💾 Fuente: {stats['configuration']['configuration_source']}")
    
    db.close()
    
    if passed == len(test_cases):
        print(f"\n🎉 ¡TODOS LOS TESTS PASARON! Sistema 100% dinámico funcionando correctamente.")
        return True
    else:
        print(f"\n⚠️ Algunos tests fallaron. Revisar configuración de BD.")
        return False

if __name__ == "__main__":
    asyncio.run(test_complete_dynamic_system())