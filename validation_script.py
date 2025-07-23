#!/usr/bin/env python3
"""
🎯 SCRIPT DE VALIDACIÓN AUTOMATIZADA
Verifica que el sistema optimizado funcione correctamente
Valida la corrección del problema "pago único" → "confirmar_plan_elegido"
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any
from datetime import datetime

class SystemValidator:
    """Validador automatizado del sistema optimizado"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def run_complete_validation(self) -> Dict[str, Any]:
        """Ejecutar validación completa del sistema"""
        
        print("🎯 INICIANDO VALIDACIÓN AUTOMATIZADA DEL SISTEMA")
        print("=" * 70)
        print(f"🔗 Base URL: {self.base_url}")
        print(f"🕐 Timestamp: {datetime.now().isoformat()}")
        print("=" * 70)
        
        # 1. Verificar conectividad básica
        if not self._test_connectivity():
            return self._create_failure_report("connectivity_failed")
        
        # 2. Validar health check del sistema
        self._test_system_health()
        
        # 3. Validar configuración de BD
        self._test_database_configuration()
        
        # 4. Validar problema específico resuelto
        self._test_specific_problem_resolution()
        
        # 5. Validar flujo completo de usuario
        self._test_complete_user_flow()
        
        # 6. Validar integración OpenAI
        self._test_openai_integration()
        
        # 7. Validar preservación de contexto
        self._test_context_preservation()
        
        # 8. Generar reporte final
        return self._generate_final_report()
    
    def _test_connectivity(self) -> bool:
        """Test de conectividad básica"""
        try:
            print("\n🔌 TEST 1: Conectividad Básica")
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                print("   ✅ Servidor accesible")
                return True
            else:
                print(f"   ❌ Servidor retornó código {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error de conectividad: {e}")
            return False
    
    def _test_system_health(self):
        """Test de health check del sistema optimizado"""
        print("\n🏥 TEST 2: Health Check Sistema Optimizado")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/chat/health-sistema-completo")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                if status == 'healthy':
                    print("   ✅ Sistema en estado saludable")
                    self._add_test_result("system_health", True, f"Status: {status}")
                else:
                    print(f"   ⚠️ Sistema en estado: {status}")
                    self._add_test_result("system_health", False, f"Status degradado: {status}")
                
                # Verificar componentes específicos
                components = data.get('components', {})
                tables = data.get('tables', {})
                
                print(f"   📊 Componentes: {components}")
                print(f"   📋 Tablas: {list(tables.keys())}")
                
            else:
                print(f"   ❌ Health check falló: {response.status_code}")
                self._add_test_result("system_health", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error en health check: {e}")
            self._add_test_result("system_health", False, str(e))
    
    def _test_database_configuration(self):
        """Test de configuración de base de datos"""
        print("\n🗄️ TEST 3: Configuración de Base de Datos")
        
        # Este test se puede hacer a través del sistema si hay endpoint específico
        # Por ahora, asumimos que el health check incluye verificación de BD
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/chat/health-sistema-completo")
            if response.status_code == 200:
                data = response.json()
                tables = data.get('tables', {})
                
                required_tables = [
                    'Estados_Conversacion',
                    'ml_intention_mappings', 
                    'keyword_condition_patterns',
                    'ConsolidadoCampañasNatalia'
                ]
                
                tables_ok = 0
                for table in required_tables:
                    if table in tables and tables[table].get('exists', False):
                        print(f"   ✅ Tabla {table}: OK ({tables[table].get('count', 0)} registros)")
                        tables_ok += 1
                    else:
                        print(f"   ❌ Tabla {table}: Faltante o vacía")
                
                success = tables_ok == len(required_tables)
                self._add_test_result("database_config", success, f"{tables_ok}/{len(required_tables)} tablas OK")
                
            else:
                print("   ❌ No se pudo verificar configuración de BD")
                self._add_test_result("database_config", False, "No accesible")
                
        except Exception as e:
            print(f"   ❌ Error verificando BD: {e}")
            self._add_test_result("database_config", False, str(e))
    
    def _test_specific_problem_resolution(self):
        """TEST CRÍTICO: Verificar que el problema específico esté resuelto"""
        print("\n🎯 TEST 4: Problema Específico Resuelto (CRÍTICO)")
        print("   Verificando: 'pago único' → 'confirmar_plan_elegido'")
        
        try:
            # Enviar mensaje específico del problema
            test_payload = {
                "user_id": 999999,  # Usuario de test
                "conversation_id": 999999,
                "message": "pago unico"
            }
            
            # Primero necesitamos establecer contexto de cliente
            setup_payload = {
                "user_id": 999999,
                "conversation_id": 999999,
                "message": "mi cedula es 93388915"
            }
            
            # Configurar cliente (puede fallar si no existe en BD, está OK)
            setup_response = self.session.post(
                f"{self.base_url}/api/v1/chat/message", 
                json=setup_payload
            )
            
            time.sleep(1)  # Pequeña pausa
            
            # Ahora el test crítico
            response = self.session.post(
                f"{self.base_url}/api/v1/chat/message", 
                json=test_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                current_state = data.get('current_state', '')
                
                if current_state == 'confirmar_plan_elegido':
                    print("   ✅ PROBLEMA RESUELTO: 'pago único' → 'confirmar_plan_elegido'")
                    self._add_test_result("specific_problem", True, f"Estado correcto: {current_state}")
                else:
                    print(f"   ❌ PROBLEMA PERSISTE: Estado obtenido: {current_state}")
                    self._add_test_result("specific_problem", False, f"Estado incorrecto: {current_state}")
                
            else:
                print(f"   ❌ Error en test crítico: HTTP {response.status_code}")
                self._add_test_result("specific_problem", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error en test crítico: {e}")
            self._add_test_result("specific_problem", False, str(e))
    
    def _test_complete_user_flow(self):
        """Test de flujo completo de usuario"""
        print("\n👤 TEST 5: Flujo Completo de Usuario")
        
        user_id = 888888
        conversation_id = 888888
        
        test_sequence = [
            {
                "step": 1,
                "message": "hola",
                "expected_state": "validar_documento",
                "description": "Saludo inicial"
            },
            {
                "step": 2, 
                "message": "93388915",
                "expected_state": "informar_deuda",
                "description": "Identificación con cédula"
            },
            {
                "step": 3,
                "message": "si quiero ver opciones",
                "expected_state": "proponer_planes_pago", 
                "description": "Solicitar opciones"
            },
            {
                "step": 4,
                "message": "pago unico",
                "expected_state": "confirmar_plan_elegido",
                "description": "Selección pago único (CRÍTICO)"
            },
            {
                "step": 5,
                "message": "acepto",
                "expected_state": "generar_acuerdo",
                "description": "Confirmación final"
            }
        ]
        
        flow_success = True
        
        for test_step in test_sequence:
            try:
                payload = {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "message": test_step["message"]
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/v1/chat/message",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    actual_state = data.get('current_state', '')
                    
                    if actual_state == test_step["expected_state"]:
                        print(f"   ✅ Paso {test_step['step']}: {test_step['description']} → {actual_state}")
                    else:
                        print(f"   ❌ Paso {test_step['step']}: Esperado {test_step['expected_state']}, obtuvo {actual_state}")
                        flow_success = False
                        
                        # Si es el paso crítico, es especialmente importante
                        if test_step["step"] == 4:
                            print(f"   🚨 PASO CRÍTICO FALLÓ: El problema principal no está resuelto")
                else:
                    print(f"   ❌ Paso {test_step['step']}: HTTP {response.status_code}")
                    flow_success = False
                
                time.sleep(0.5)  # Pausa entre requests
                
            except Exception as e:
                print(f"   ❌ Paso {test_step['step']}: Error {e}")
                flow_success = False
        
        self._add_test_result("complete_flow", flow_success, f"Flujo completo {'exitoso' if flow_success else 'falló'}")
    
    def _test_openai_integration(self):
        """Test de integración OpenAI (opcional)"""
        print("\n🤖 TEST 6: Integración OpenAI (Opcional)")
        
        try:
            response = self.session.get(f"{self.base_url}/api/v1/chat/test-openai-integration")
            
            if response.status_code == 200:
                data = response.json()
                openai_available = data.get('openai_available', False)
                
                if openai_available:
                    connection_test = data.get('connection_test', {})
                    processing_test = data.get('processing_test', {})
                    
                    if connection_test.get('success', False):
                        print("   ✅ OpenAI: Conectado y funcional")
                        
                        if processing_test.get('enhanced', False):
                            print("   ✅ OpenAI: Procesamiento mejorado activo")
                            self._add_test_result("openai_integration", True, "Completamente funcional")
                        else:
                            print("   ⚠️ OpenAI: Conectado pero procesamiento limitado")
                            self._add_test_result("openai_integration", True, "Conectado con limitaciones")
                    else:
                        print("   ⚠️ OpenAI: Configurado pero con problemas de conexión")
                        self._add_test_result("openai_integration", False, "Problemas de conexión")
                else:
                    print("   ⚠️ OpenAI: No disponible (sistema funcionará con fallbacks)")
                    self._add_test_result("openai_integration", True, "No disponible - fallbacks activos")
            else:
                print(f"   ⚠️ No se pudo verificar OpenAI: HTTP {response.status_code}")
                self._add_test_result("openai_integration", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ Error verificando OpenAI: {e}")
            self._add_test_result("openai_integration", False, str(e))
    
    def _test_context_preservation(self):
        """Test de preservación de contexto"""
        print("\n🔒 TEST 7: Preservación de Contexto")
        
        try:
            user_id = 777777
            conversation_id = 777777
            
            # Establecer cliente
            setup_payload = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message": "mi cedula es 93388915"
            }
            
            response1 = self.session.post(
                f"{self.base_url}/api/v1/chat/message",
                json=setup_payload
            )
            
            if response1.status_code == 200:
                data1 = response1.json()
                context1 = data1.get('context', {})
                client_found1 = context1.get('cliente_encontrado', False)
                client_name1 = context1.get('Nombre_del_cliente', '')
                
                if client_found1:
                    print(f"   ✅ Cliente establecido: {client_name1}")
                    
                    # Enviar mensaje que podría perder contexto
                    test_payload = {
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                        "message": "acepto"
                    }
                    
                    time.sleep(0.5)
                    
                    response2 = self.session.post(
                        f"{self.base_url}/api/v1/chat/message",
                        json=test_payload
                    )
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        context2 = data2.get('context', {})
                        client_found2 = context2.get('cliente_encontrado', False)
                        client_name2 = context2.get('Nombre_del_cliente', '')
                        
                        if client_found2 and client_name2 == client_name1:
                            print("   ✅ Contexto preservado correctamente")
                            self._add_test_result("context_preservation", True, "Cliente preservado")
                        else:
                            print("   ❌ Contexto perdido o modificado")
                            self._add_test_result("context_preservation", False, "Cliente perdido")
                    else:
                        print("   ❌ Error en segundo mensaje")
                        self._add_test_result("context_preservation", False, "Error segundo mensaje")
                else:
                    print("   ⚠️ No se pudo establecer cliente para test")
                    self._add_test_result("context_preservation", False, "No se estableció cliente")
            else:
                print("   ❌ Error estableciendo cliente")
                self._add_test_result("context_preservation", False, "Error estableciendo cliente")
                
        except Exception as e:
            print(f"   ❌ Error en test de contexto: {e}")
            self._add_test_result("context_preservation", False, str(e))
    
    def _add_test_result(self, test_name: str, success: bool, details: str = ""):
        """Agregar resultado de test"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
        
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generar reporte final de validación"""
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # Verificar tests críticos
        critical_tests = [
            "system_health",
            "specific_problem",  # Este es el más importante
            "complete_flow"
        ]
        
        critical_passed = 0
        for result in self.results:
            if result["test"] in critical_tests and result["success"]:
                critical_passed += 1
        
        system_operational = critical_passed >= 2  # Al menos 2 de 3 críticos deben pasar
        
        print("\n" + "=" * 70)
        print("📊 REPORTE FINAL DE VALIDACIÓN")
        print("=" * 70)
        
        print(f"🎯 Tests totales: {self.total_tests}")
        print(f"✅ Tests exitosos: {self.passed_tests}")
        print(f"❌ Tests fallidos: {self.total_tests - self.passed_tests}")
        print(f"📈 Tasa de éxito: {success_rate:.1f}%")
        print(f"🏥 Sistema operacional: {'SÍ' if system_operational else 'NO'}")
        
        print("\n📋 DETALLE DE TESTS:")
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            critical = "🎯" if result["test"] in critical_tests else "  "
            print(f"   {status} {critical} {result['test']}: {result['details']}")
        
        # Verificación específica del problema principal
        specific_problem_resolved = any(
            r["test"] == "specific_problem" and r["success"] 
            for r in self.results
        )
        
        print("\n🎯 VERIFICACIÓN DEL PROBLEMA PRINCIPAL:")
        if specific_problem_resolved:
            print("   ✅ PROBLEMA RESUELTO: 'pago único' → 'confirmar_plan_elegido'")
            print("   ✅ El issue reportado ha sido corregido exitosamente")
        else:
            print("   ❌ PROBLEMA PERSISTE: Requiere revisión adicional")
            print("   ❌ El issue reportado NO ha sido resuelto")
        
        print("\n🔧 RECOMENDACIONES:")
        if system_operational and specific_problem_resolved:
            print("   🎉 ¡Sistema listo para producción!")
            print("   📈 Monitorear métricas de uso de OpenAI")
            print("   📊 Revisar logs para optimizaciones adicionales")
        else:
            print("   ⚠️ Revisar componentes fallidos antes de desplegar")
            print("   🔍 Verificar configuración de BD y servicios")
            print("   📞 Contactar equipo de desarrollo si problemas persisten")
        
        return {
            "validation_timestamp": datetime.now().isoformat(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "success_rate": success_rate,
            "system_operational": system_operational,
            "specific_problem_resolved": specific_problem_resolved,
            "critical_tests_passed": f"{critical_passed}/{len(critical_tests)}",
            "test_results": self.results,
            "overall_status": "PASSED" if system_operational and specific_problem_resolved else "FAILED",
            "recommendations": [
                "Sistema listo para producción" if system_operational and specific_problem_resolved else "Revisar componentes fallidos",
                "Monitorear métricas de OpenAI",
                "Verificar logs regularmente"
            ]
        }
    
    def _create_failure_report(self, reason: str) -> Dict[str, Any]:
        """Crear reporte de falla"""
        return {
            "validation_timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "passed_tests": 0,
            "success_rate": 0,
            "system_operational": False,
            "specific_problem_resolved": False,
            "overall_status": "FAILED",
            "failure_reason": reason,
            "recommendations": [
                "Verificar que el servidor esté ejecutándose",
                "Comprobar configuración de red",
                "Revisar logs del servidor"
            ]
        }

def main():
    """Función principal del script de validación"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Validación automatizada del sistema chat optimizado")
    parser.add_argument("--url", default="http://localhost:8000", help="URL base del servidor")
    parser.add_argument("--output", help="Archivo para guardar reporte JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Salida verbose")
    
    args = parser.parse_args()
    
    # Crear validador
    validator = SystemValidator(args.url)
    
    # Ejecutar validación
    try:
        report = validator.run_complete_validation()
        
        # Guardar reporte si se especificó archivo
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 Reporte guardado en: {args.output}")
        
        # Código de salida basado en resultado
        if report["overall_status"] == "PASSED":
            print("\n🎉 VALIDACIÓN EXITOSA")
            sys.exit(0)
        else:
            print("\n❌ VALIDACIÓN FALLÓ")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Validación interrumpida por usuario")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Error crítico en validación: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()