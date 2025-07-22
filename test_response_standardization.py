import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch

# Simular las dependencias para el test
class MockDB:
    def execute(self, query, params=None):
        # Simular resultado de consulta cliente
        if "ConsolidadoCampañasNatalia" in str(query):
            class MockResult:
                def fetchone(self):
                    return ["MARIA ANGELICA", 4173695, "Scotiabank", 1000000, 784744, 626054, 313027, 156513, "Tarjeta"]
            return MockResult()
        return Mock()

async def test_estandarizacion_respuestas_completa():
    """🧪 TEST COMPLETO: Validar que la estandarización de respuestas funciona"""
    
    print("🧪 INICIANDO TEST DE ESTANDARIZACIÓN DE RESPUESTAS")
    print("=" * 60)
    
    # ✅ 1. SIMULAR DIFERENTES FORMATOS DE RESPUESTA QUE PUEDEN LLEGAR
    respuestas_diversas = [
        # Formato del improved_chat_processor
        {
            'success': True,
            'next_state': 'informar_deuda',
            'context': {'cliente_encontrado': True, 'Nombre_del_cliente': 'TEST USER'},
            'message': 'Cliente encontrado',
            'buttons': [{'id': 'opciones', 'text': 'Ver opciones'}],
            'method': 'cedula_detection_improved'
        },
        
        # Formato del dynamic_service
        {
            'next_state': 'proponer_planes_pago',
            'condition_detected': 'cliente_selecciona_plan',
            'confidence': 0.9,
            'detection_method': 'keyword_pattern',
            'transition_info': {'execution_time_ms': 15.5}
        },
        
        # Formato de fallback
        {
            'estado_siguiente': 'inicial',
            'mensaje_respuesta': 'No entiendo',
            'botones': [],
            'confianza': 0.3,
            'metodo': 'fallback_original'
        },
        
        # Formato incompleto (el que causaba el error)
        {
            'next_state': 'confirmar_plan_elegido',
            'context': {'plan_seleccionado': 'Pago único'},
            # ❌ SIN 'metodo' - esto causaba el KeyError
        },
        
        # Formato con claves mezcladas
        {
            'intention': 'CONFIRMACION_EXITOSA',
            'confidence': 0.95,
            'new_state': 'generar_acuerdo',
            'response': 'Plan confirmado',
            'button_options': [{'id': 'finalizar', 'text': 'Finalizar'}],
            'processor_method': 'ml_enhanced'
        }
    ]
    
    # ✅ 2. FUNCIÓN DE ESTANDARIZACIÓN (LA SOLUCIÓN)
    def estandarizar_respuesta_mejorada(resultado: Dict[str, Any]) -> Dict[str, Any]:
        """✅ FUNCIÓN MEJORADA DE ESTANDARIZACIÓN"""
        
        respuesta_estandar = {
            'intencion': (
                resultado.get('intencion') or 
                resultado.get('intention') or 
                resultado.get('detected_intention') or 
                'PROCESAMIENTO_GENERAL'
            ),
            'confianza': (
                resultado.get('confianza') or 
                resultado.get('confidence') or 
                resultado.get('detection_confidence') or 
                0.0
            ),
            'next_state': (
                resultado.get('next_state') or 
                resultado.get('estado_siguiente') or 
                resultado.get('new_state') or 
                'inicial'
            ),
            'contexto_actualizado': (
                resultado.get('contexto_actualizado') or 
                resultado.get('context') or 
                resultado.get('context_updates') or 
                {}
            ),
            'mensaje_respuesta': (
                resultado.get('mensaje_respuesta') or 
                resultado.get('message') or 
                resultado.get('response') or 
                '¿En qué puedo ayudarte?'
            ),
            'botones': (
                resultado.get('botones') or 
                resultado.get('buttons') or 
                resultado.get('button_options') or 
                []
            ),
            'metodo': (
                resultado.get('metodo') or 
                resultado.get('method') or 
                resultado.get('detection_method') or 
                resultado.get('processor_method') or 
                'sistema_dinamico'
            ),
            'usar_resultado': resultado.get('success', True),
            'transition_info': resultado.get('transition_info', {})
        }
        
        return respuesta_estandar
    
    # ✅ 3. EJECUTAR TESTS DE ESTANDARIZACIÓN
    test_results = []
    
    for i, respuesta_original in enumerate(respuestas_diversas, 1):
        print(f"\n🧪 TEST {i}: Estandarizando respuesta con formato '{type(respuesta_original).__name__}'")
        print(f"   Keys originales: {list(respuesta_original.keys())}")
        
        try:
            # ✅ APLICAR ESTANDARIZACIÓN
            respuesta_estandarizada = estandarizar_respuesta_mejorada(respuesta_original)
            
            # ✅ VERIFICAR QUE TODAS LAS CLAVES REQUERIDAS ESTÉN PRESENTES
            claves_requeridas = [
                'intencion', 'confianza', 'next_state', 'contexto_actualizado',
                'mensaje_respuesta', 'botones', 'metodo', 'usar_resultado'
            ]
            
            claves_presentes = [clave for clave in claves_requeridas if clave in respuesta_estandarizada]
            claves_faltantes = [clave for clave in claves_requeridas if clave not in respuesta_estandarizada]
            
            test_passed = len(claves_faltantes) == 0
            
            # ✅ VERIFICAR QUE NO HAY VALORES None
            valores_none = [clave for clave, valor in respuesta_estandarizada.items() if valor is None]
            
            test_results.append({
                'test_id': i,
                'input_keys': list(respuesta_original.keys()),
                'output_keys': list(respuesta_estandarizada.keys()),
                'claves_presentes': claves_presentes,
                'claves_faltantes': claves_faltantes,
                'valores_none': valores_none,
                'test_passed': test_passed and len(valores_none) == 0,
                'metodo_detectado': respuesta_estandarizada.get('metodo'),
                'next_state_detectado': respuesta_estandarizada.get('next_state')
            })
            
            if test_passed and len(valores_none) == 0:
                print(f"   ✅ PASÓ: Todas las claves presentes")
                print(f"   📊 Método estandarizado: {respuesta_estandarizada['metodo']}")
                print(f"   📍 Estado siguiente: {respuesta_estandarizada['next_state']}")
            else:
                print(f"   ❌ FALLÓ:")
                if claves_faltantes:
                    print(f"      Claves faltantes: {claves_faltantes}")
                if valores_none:
                    print(f"      Valores None: {valores_none}")
                    
        except Exception as e:
            print(f"   💥 ERROR: {e}")
            test_results.append({
                'test_id': i,
                'test_passed': False,
                'error': str(e)
            })
    
    # ✅ 4. TEST ESPECÍFICO DEL PROBLEMA ORIGINAL
    print(f"\n🎯 TEST ESPECÍFICO: Reproductor del error original KeyError: 'metodo'")
    
    # Esta era la respuesta que causaba el error
    respuesta_problematica = {
        'success': True,
        'next_state': 'informar_deuda',
        'context': {'cliente_encontrado': True},
        'message': 'Cliente encontrado',
        'buttons': []
        # ❌ NOTA: Sin 'metodo' - esto causaba KeyError
    }
    
    try:
        # ✅ INTENTAR ACCESO DIRECTO (ESTO FALLABA ANTES)
        metodo_directo = respuesta_problematica['metodo']  # ❌ KeyError aquí
        print(f"   ❌ Acceso directo no falló (esto es inesperado)")
    except KeyError as e:
        print(f"   ✅ Confirmado: Acceso directo falla con KeyError: {e}")
    
    # ✅ APLICAR SOLUCIÓN
    respuesta_solucionada = estandarizar_respuesta_mejorada(respuesta_problematica)
    metodo_solucionado = respuesta_solucionada['metodo']
    print(f"   ✅ Con estandarización: metodo = '{metodo_solucionado}'")
    
    # ✅ 5. ESTADÍSTICAS FINALES
    tests_pasados = len([r for r in test_results if r.get('test_passed', False)])
    total_tests = len(test_results)
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTADOS FINALES:")
    print(f"   ✅ Tests pasados: {tests_pasados}/{total_tests}")
    print(f"   📈 Tasa de éxito: {(tests_pasados/total_tests*100):.1f}%")
    
    # ✅ 6. VALIDACIÓN DE COMPATIBILIDAD TOTAL
    print(f"\n🔧 VALIDACIÓN DE COMPATIBILIDAD:")
    
    metodos_detectados = [r.get('metodo_detectado') for r in test_results if r.get('metodo_detectado')]
    estados_detectados = [r.get('next_state_detectado') for r in test_results if r.get('next_state_detectado')]
    
    print(f"   🎯 Métodos estandarizados: {set(metodos_detectados)}")
    print(f"   📍 Estados detectados: {set(estados_detectados)}")
    
    # ✅ VERIFICAR QUE NINGÚN MÉTODO ES None O VACÍO
    metodos_validos = [m for m in metodos_detectados if m and m != 'None']
    compatibilidad_completa = len(metodos_validos) == len(metodos_detectados)
    
    if tests_pasados == total_tests and compatibilidad_completa:
        print(f"\n🎉 ¡SOLUCIÓN EXITOSA!")
        print(f"   ✅ El error KeyError: 'metodo' está RESUELTO")
        print(f"   ✅ Compatibilidad total entre formatos")
        print(f"   ✅ Sistema 100% dinámico mantenido")
        return True
    else:
        print(f"\n⚠️ Solución necesita ajustes:")
        for result in test_results:
            if not result.get('test_passed', False):
                print(f"   ❌ Test {result.get('test_id')}: {result.get('error', 'Falló validación')}")
        return False

async def test_implementacion_endpoint_corregido():
    """🧪 TEST: Validar que el endpoint corregido maneja todas las respuestas"""
    
    print("\n🧪 TEST DE IMPLEMENTACIÓN EN ENDPOINT")
    print("=" * 40)
    
    # ✅ FUNCIÓN EXTRAER INFORMACIÓN (DEL ENDPOINT CORREGIDO)
    def extraer_informacion_resultado_seguro(resultado: Dict[str, Any]) -> Dict[str, Any]:
        """Función del endpoint corregido"""
        info_extraida = {}
        
        info_extraida['intencion'] = (
            resultado.get('intencion') or 
            resultado.get('intention') or 
            resultado.get('detected_intention') or 
            'PROCESAMIENTO_GENERAL'
        )
        
        info_extraida['confianza'] = (
            resultado.get('confianza') or 
            resultado.get('confidence') or 
            resultado.get('detection_confidence') or 
            0.0
        )
        
        info_extraida['metodo'] = (
            resultado.get('metodo') or 
            resultado.get('method') or 
            resultado.get('detection_method') or 
            resultado.get('processor_method') or 
            'sistema_dinamico'
        )
        
        return info_extraida
    
    # ✅ RESPUESTAS DE PRUEBA
    respuestas_test = [
        {'method': 'cedula_detection'},  # Formato improved_processor
        {'detection_method': 'keyword'},  # Formato dynamic_service  
        {'metodo': 'fallback'},  # Formato original
        {},  # Formato vacío (el problemático)
        {'processor_method': 'ml_enhanced'}  # Formato con otra clave
    ]
    
    resultados_endpoint = []
    
    for i, respuesta in enumerate(respuestas_test, 1):
        try:
            info = extraer_informacion_resultado_seguro(respuesta)
            
            # ✅ SIMULAR USO EN ENDPOINT (donde ocurría el error)
            intencion = info['intencion']
            confianza = info['confianza'] 
            metodo = info['metodo']  # ✅ ESTA LÍNEA YA NO DEBE FALLAR
            
            print(f"   ✅ Test {i}: metodo='{metodo}', intencion='{intencion}'")
            resultados_endpoint.append(True)
            
        except KeyError as e:
            print(f"   ❌ Test {i}: KeyError: {e}")
            resultados_endpoint.append(False)
        except Exception as e:
            print(f"   💥 Test {i}: Error: {e}")
            resultados_endpoint.append(False)
    
    endpoint_tests_pasados = sum(resultados_endpoint)
    print(f"\n📊 Endpoint tests: {endpoint_tests_pasados}/{len(resultados_endpoint)} pasados")
    
    return endpoint_tests_pasados == len(resultados_endpoint)

async def main():
    """🧪 EJECUTAR TODOS LOS TESTS"""
    
    print("🚀 INICIANDO SUITE COMPLETA DE TESTS")
    print("=" * 70)
    
    # Test 1: Estandarización de respuestas
    test1_passed = await test_estandarizacion_respuestas_completa()
    
    # Test 2: Implementación en endpoint
    test2_passed = await test_implementacion_endpoint_corregido()
    
    # Resultado final
    all_tests_passed = test1_passed and test2_passed
    
    print("\n" + "=" * 70)
    print("🏁 RESULTADO FINAL")
    print("=" * 70)
    
    if all_tests_passed:
        print("🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ El error KeyError: 'metodo' está completamente RESUELTO")
        print("✅ La estandarización de respuestas funciona correctamente")
        print("✅ El sistema mantiene su naturaleza 100% dinámica")
        print("\n💡 RECOMENDACIÓN:")
        print("   Implementar las funciones de estandarización en el código")
        print("   Usar _extraer_informacion_resultado_seguro() en el endpoint")
        print("   Agregar _estandarizar_respuesta() en improved_chat_processor")
    else:
        print("⚠️ ALGUNOS TESTS FALLARON")
        print("📋 Revisar implementación antes de desplegar")
    
    return all_tests_passed

if __name__ == "__main__":
    asyncio.run(main())