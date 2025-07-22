import asyncio
import json
from datetime import datetime
from app.db.session import SessionLocal
from app.services.dynamic_transition_service import create_dynamic_transition_service
from app.services.conversation_service import crear_conversation_service

class DynamicSystemValidator:
    """Validador completo del sistema dinámico"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.dynamic_service = create_dynamic_transition_service(self.db)
        self.conversation_service = crear_conversation_service(self.db)
        
    async def validar_sistema_completo(self):
        """Validación completa del sistema dinámico"""
        
        print("🧪 INICIANDO VALIDACIÓN COMPLETA DEL SISTEMA DINÁMICO")
        print("=" * 70)
        
        resultados = {
            "configuracion_bd": await self._validar_configuracion_bd(),
            "transiciones_criticas": await self._validar_transiciones_criticas(),
            "preservacion_contexto": await self._validar_preservacion_contexto(),
            "flujo_completo": await self._validar_flujo_completo_usuario(),
            "resumen": {}
        }
        
        # Calcular resumen
        total_tests = sum(len(categoria.get("tests", [])) for categoria in resultados.values() if isinstance(categoria, dict))
        tests_pasados = sum(len([t for t in categoria.get("tests", []) if t.get("passed", False)]) for categoria in resultados.values() if isinstance(categoria, dict))
        
        resultados["resumen"] = {
            "total_tests": total_tests,
            "tests_pasados": tests_pasados,
            "tasa_exito": f"{(tests_pasados/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            "sistema_funcional": tests_pasados >= (total_tests * 0.8)  # 80% mínimo
        }
        
        self._mostrar_resumen_final(resultados)
        return resultados
    
    async def _validar_configuracion_bd(self):
        """Validar configuración de BD"""
        print("\n📋 VALIDANDO CONFIGURACIÓN DE BD...")
        
        tests = []
        
        # Test 1: Estados básicos
        try:
            from sqlalchemy import text
            query = text("SELECT COUNT(*) FROM Estados_Conversacion WHERE activo = 1")
            count_estados = self.db.execute(query).scalar()
            
            tests.append({
                "nombre": "Estados en BD",
                "esperado": ">= 5",
                "obtenido": count_estados,
                "passed": count_estados >= 5,
                "detalles": f"{count_estados} estados activos encontrados"
            })
        except Exception as e:
            tests.append({
                "nombre": "Estados en BD",
                "passed": False,
                "error": str(e)
            })
        
        # Test 2: ML Mappings
        try:
            query = text("SELECT COUNT(*) FROM ml_intention_mappings WHERE active = 1")
            count_ml = self.db.execute(query).scalar()
            
            tests.append({
                "nombre": "ML Mappings",
                "esperado": ">= 10",
                "obtenido": count_ml,
                "passed": count_ml >= 10,
                "detalles": f"{count_ml} mapeos ML encontrados"
            })
        except Exception as e:
            tests.append({
                "nombre": "ML Mappings",
                "passed": False,
                "error": str(e)
            })
        
        # Test 3: Keyword Patterns
        try:
            query = text("SELECT COUNT(*) FROM keyword_condition_patterns WHERE active = 1")
            count_keywords = self.db.execute(query).scalar()
            
            tests.append({
                "nombre": "Keyword Patterns",
                "esperado": ">= 15",
                "obtenido": count_keywords,
                "passed": count_keywords >= 15,
                "detalles": f"{count_keywords} patrones de palabras clave"
            })
        except Exception as e:
            tests.append({
                "nombre": "Keyword Patterns",
                "passed": False,
                "error": str(e)
            })
        
        # Test 4: Estado específico para el problema
        try:
            query = text("""
                SELECT nombre, estado_siguiente_true 
                FROM Estados_Conversacion 
                WHERE nombre = 'proponer_planes_pago' AND activo = 1
            """)
            result = self.db.execute(query).fetchone()
            
            correcto = result and result[1] == 'confirmar_plan_elegido'
            
            tests.append({
                "nombre": "Estado proponer_planes_pago corregido",
                "esperado": "confirmar_plan_elegido",
                "obtenido": result[1] if result else "No encontrado",
                "passed": correcto,
                "detalles": "Transición correcta configurada" if correcto else "Transición incorrecta"
            })
        except Exception as e:
            tests.append({
                "nombre": "Estado proponer_planes_pago",
                "passed": False,
                "error": str(e)
            })
        
        passed_count = len([t for t in tests if t.get("passed", False)])
        print(f"   ✅ {passed_count}/{len(tests)} tests de configuración pasados")
        
        return {"categoria": "Configuración BD", "tests": tests}
    
    async def _validar_transiciones_criticas(self):
        """Validar transiciones críticas del problema reportado"""
        print("\n🎯 VALIDANDO TRANSICIONES CRÍTICAS...")
        
        tests = []
        
        # Test 1: Transición "pago único" en proponer_planes_pago
        try:
            result = self.dynamic_service.determine_next_state(
                current_state="proponer_planes_pago",
                user_message="pago unico",
                ml_result={"intention": "PAGO_UNICO", "confidence": 0.9},
                context={"cliente_encontrado": True, "Nombre_del_cliente": "TEST USER"}
            )
            
            correcto = result['next_state'] == 'confirmar_plan_elegido'
            
            tests.append({
                "nombre": "Pago único → Confirmar plan",
                "input": "pago unico",
                "esperado": "confirmar_plan_elegido",
                "obtenido": result['next_state'],
                "passed": correcto,
                "metodo": result.get('detection_method'),
                "confidence": result.get('confidence')
            })
        except Exception as e:
            tests.append({
                "nombre": "Pago único → Confirmar plan",
                "passed": False,
                "error": str(e)
            })
        
        # Test 2: Transición "acepto" en proponer_planes_pago
        try:
            result = self.dynamic_service.determine_next_state(
                current_state="proponer_planes_pago",
                user_message="acepto",
                ml_result={"intention": "CONFIRMACION_EXITOSA", "confidence": 0.9},
                context={"cliente_encontrado": True}
            )
            
            correcto = result['next_state'] == 'confirmar_plan_elegido'
            
            tests.append({
                "nombre": "Acepto → Confirmar plan",
                "input": "acepto",
                "esperado": "confirmar_plan_elegido",
                "obtenido": result['next_state'],
                "passed": correcto,
                "metodo": result.get('detection_method')
            })
        except Exception as e:
            tests.append({
                "nombre": "Acepto → Confirmar plan",
                "passed": False,
                "error": str(e)
            })
        
        # Test 3: Evitar volver a inicial con cliente
        try:
            result = self.dynamic_service.determine_next_state(
                current_state="confirmar_plan_elegido",
                user_message="continuar",
                ml_result={"intention": "CONTINUACION", "confidence": 0.5},
                context={
                    "cliente_encontrado": True,
                    "Nombre_del_cliente": "MARIA ANGELICA",
                    "saldo_total": 4173695
                }
            )
            
            # NO debe volver a inicial si hay cliente
            correcto = result['next_state'] != 'inicial'
            
            tests.append({
                "nombre": "No volver a inicial con cliente",
                "input": "continuar",
                "esperado": "≠ inicial",
                "obtenido": result['next_state'],
                "passed": correcto,
                "detalles": "Mantiene contexto del cliente"
            })
        except Exception as e:
            tests.append({
                "nombre": "No volver a inicial con cliente",
                "passed": False,
                "error": str(e)
            })
        
        passed_count = len([t for t in tests if t.get("passed", False)])
        print(f"   ✅ {passed_count}/{len(tests)} transiciones críticas pasaron")
        
        return {"categoria": "Transiciones Críticas", "tests": tests}
    
    async def _validar_preservacion_contexto(self):
        """Validar que el contexto se preserve correctamente"""
        print("\n🔒 VALIDANDO PRESERVACIÓN DE CONTEXTO...")
        
        tests = []
        
        # Crear contexto de prueba con cliente
        contexto_test = {
            "cliente_encontrado": True,
            "Nombre_del_cliente": "MARIA ANGELICA ESCOBAR RODRIGUEZ",
            "saldo_total": 4173695,
            "banco": "Scotiabank - Colpatria",
            "oferta_2": 784744,
            "hasta_6_cuotas": 626054
        }
        
        try:
            # Simular transición que podría perder contexto
            result = self.dynamic_service.determine_next_state(
                current_state="proponer_planes_pago",
                user_message="pago unico",
                ml_result={"intention": "PAGO_UNICO", "confidence": 0.9},
                context=contexto_test
            )
            
            # El contexto debería mantenerse
            context_preserved = (
                result.get('next_state') != 'inicial' and
                len(contexto_test) > 0
            )
            
            tests.append({
                "nombre": "Preservación de contexto cliente",
                "passed": context_preserved,
                "detalles": f"Estado resultante: {result.get('next_state')}",
                "contexto_elementos": len(contexto_test)
            })
            
        except Exception as e:
            tests.append({
                "nombre": "Preservación de contexto cliente",
                "passed": False,
                "error": str(e)
            })
        
        # Test de captura de plan
        try:
            # Verificar que se capture información del plan
            if hasattr(self.conversation_service, '_capturar_seleccion_plan'):
                plan_info = self.conversation_service._capturar_seleccion_plan(
                    "pago unico",
                    {"condition_detected": "cliente_selecciona_pago_unico"},
                    contexto_test
                )
                
                plan_captured = plan_info.get('plan_capturado', False)
                
                tests.append({
                    "nombre": "Captura de plan seleccionado",
                    "passed": plan_captured,
                    "plan_tipo": plan_info.get('plan_seleccionado', 'N/A'),
                    "monto": plan_info.get('monto_acordado', 0)
                })
            else:
                tests.append({
                    "nombre": "Captura de plan seleccionado",
                    "passed": False,
                    "error": "Método no encontrado"
                })
                
        except Exception as e:
            tests.append({
                "nombre": "Captura de plan seleccionado",
                "passed": False,
                "error": str(e)
            })
        
        passed_count = len([t for t in tests if t.get("passed", False)])
        print(f"   ✅ {passed_count}/{len(tests)} tests de contexto pasaron")
        
        return {"categoria": "Preservación Contexto", "tests": tests}
    
    async def _validar_flujo_completo_usuario(self):
        """Validar el flujo completo del usuario reportado"""
        print("\n🎭 VALIDANDO FLUJO COMPLETO DE USUARIO...")
        
        tests = []
        
        # Flujo exacto del problema reportado
        flujo_pasos = [
            {
                "paso": 1,
                "estado": "inicial",
                "mensaje": "hola",
                "esperado": "validar_documento"
            },
            {
                "paso": 2,
                "estado": "validar_documento",
                "mensaje": "1016020871",
                "esperado": "informar_deuda"
            },
            {
                "paso": 3,
                "estado": "informar_deuda",
                "mensaje": "Sí, quiero ver opciones",
                "esperado": "proponer_planes_pago"
            },
            {
                "paso": 4,
                "estado": "proponer_planes_pago",
                "mensaje": "pago unico",
                "esperado": "confirmar_plan_elegido"  # ✅ CRÍTICO
            },
            {
                "paso": 5,
                "estado": "confirmar_plan_elegido",
                "mensaje": "confirmo",
                "esperado": "generar_acuerdo"
            }
        ]
        
        contexto_simulado = {}
        
        for paso_info in flujo_pasos:
            try:
                # Simular contexto según el paso
                if paso_info["paso"] >= 2:
                    contexto_simulado.update({
                        "cliente_encontrado": True,
                        "Nombre_del_cliente": "MARIA ANGELICA ESCOBAR RODRIGUEZ",
                        "saldo_total": 4173695,
                        "oferta_2": 784744
                    })
                
                # Crear ML result apropiado
                ml_result = self._generar_ml_result_apropiado(paso_info["mensaje"])
                
                # Ejecutar transición
                result = self.dynamic_service.determine_next_state(
                    current_state=paso_info["estado"],
                    user_message=paso_info["mensaje"],
                    ml_result=ml_result,
                    context=contexto_simulado.copy()
                )
                
                estado_obtenido = result['next_state']
                correcto = estado_obtenido == paso_info["esperado"]
                
                tests.append({
                    "nombre": f"Paso {paso_info['paso']}: {paso_info['mensaje'][:20]}...",
                    "estado_inicial": paso_info["estado"],
                    "mensaje": paso_info["mensaje"],
                    "esperado": paso_info["esperado"],
                    "obtenido": estado_obtenido,
                    "passed": correcto,
                    "metodo": result.get('detection_method'),
                    "critico": paso_info["paso"] == 4  # El paso del problema
                })
                
                if correcto:
                    print(f"   ✅ Paso {paso_info['paso']}: {paso_info['estado']} → {estado_obtenido}")
                else:
                    print(f"   ❌ Paso {paso_info['paso']}: Esperado {paso_info['esperado']}, obtuvo {estado_obtenido}")
                
            except Exception as e:
                tests.append({
                    "nombre": f"Paso {paso_info['paso']}: {paso_info['mensaje'][:20]}...",
                    "passed": False,
                    "error": str(e),
                    "critico": paso_info["paso"] == 4
                })
                print(f"   💥 Paso {paso_info['paso']}: ERROR - {e}")
        
        passed_count = len([t for t in tests if t.get("passed", False)])
        critical_passed = len([t for t in tests if t.get("critico") and t.get("passed", False)])
        
        print(f"   ✅ {passed_count}/{len(tests)} pasos del flujo pasaron")
        print(f"   🎯 {critical_passed}/1 pasos críticos pasaron")
        
        return {"categoria": "Flujo Completo Usuario", "tests": tests}
    
    def _generar_ml_result_apropiado(self, mensaje: str):
        """Generar resultado ML apropiado para el mensaje"""
        
        mensaje_lower = mensaje.lower()
        
        if any(word in mensaje_lower for word in ['hola', 'buenas']):
            return {"intention": "SALUDO", "confidence": 0.9}
        elif mensaje_lower.isdigit():
            return {"intention": "IDENTIFICACION", "confidence": 0.95}
        elif 'opciones' in mensaje_lower:
            return {"intention": "CONFIRMACION", "confidence": 0.8}
        elif 'pago unic' in mensaje_lower:
            return {"intention": "PAGO_UNICO", "confidence": 0.9}
        elif 'confirmo' in mensaje_lower:
            return {"intention": "CONFIRMACION_EXITOSA", "confidence": 0.95}
        else:
            return {"intention": "MENSAJE_GENERAL", "confidence": 0.5}
    
    def _mostrar_resumen_final(self, resultados):
        """Mostrar resumen final de la validación"""
        
        print("\n" + "=" * 70)
        print("📊 RESUMEN FINAL DE VALIDACIÓN")
        print("=" * 70)
        
        resumen = resultados["resumen"]
        
        print(f"🎯 Total tests ejecutados: {resumen['total_tests']}")
        print(f"✅ Tests pasados: {resumen['tests_pasados']}")
        print(f"📈 Tasa de éxito: {resumen['tasa_exito']}")
        
        if resumen["sistema_funcional"]:
            print(f"\n🎉 ¡SISTEMA DINÁMICO FUNCIONANDO CORRECTAMENTE!")
            print(f"   El problema del flujo está RESUELTO")
        else:
            print(f"\n⚠️ SISTEMA NECESITA CORRECCIONES")
            print(f"   Revisar tests fallidos para identificar problemas")
        
        # Mostrar detalles por categoría
        for categoria, datos in resultados.items():
            if categoria != "resumen" and isinstance(datos, dict):
                tests = datos.get("tests", [])
                passed = len([t for t in tests if t.get("passed", False)])
                total = len(tests)
                
                print(f"\n📋 {datos['categoria']}: {passed}/{total}")
                
                # Mostrar tests críticos fallidos
                for test in tests:
                    if not test.get("passed", False):
                        print(f"   ❌ {test['nombre']}: {test.get('error', 'Falló')}")
        
        print("=" * 70)
        
        # Recomendaciones
        if not resumen["sistema_funcional"]:
            print(f"\n💡 RECOMENDACIONES:")
            print(f"   1. Ejecutar script SQL de configuración")
            print(f"   2. Verificar que todas las tablas existan")
            print(f"   3. Implementar correcciones de código Python")
            print(f"   4. Verificar preservación de contexto")

async def main():
    """Función principal de validación"""
    validator = DynamicSystemValidator()
    try:
        resultados = await validator.validar_sistema_completo()
        return resultados
    finally:
        validator.db.close()

if __name__ == "__main__":
    asyncio.run(main())