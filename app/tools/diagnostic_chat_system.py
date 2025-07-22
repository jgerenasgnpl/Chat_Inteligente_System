import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal
from typing import Dict, Any
import json

class ChatSystemDiagnostic:
    """Herramienta para diagnosticar problemas en el sistema dinámico"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.issues_found = []
        self.recommendations = []
    
    async def diagnose_complete_system(self):
        """Diagnóstico completo del sistema"""
        
        print("🔍 INICIANDO DIAGNÓSTICO COMPLETO DEL SISTEMA DINÁMICO")
        print("=" * 70)
        
        # Diagnósticos específicos
        await self._diagnose_transition_issue()
        await self._diagnose_hardcoded_data()
        await self._diagnose_table_configuration()
        await self._diagnose_message_flow()
        
        # Mostrar resumen
        self._show_diagnostic_summary()
        
        return {
            "issues_found": self.issues_found,
            "recommendations": self.recommendations,
            "system_health": len(self.issues_found) == 0
        }
    
    async def _diagnose_transition_issue(self):
        """Diagnosticar problema específico de transición bloqueada"""
        
        print("\n🎯 DIAGNÓSTICO: Problema de Transición Bloqueada")
        print("-" * 50)
        
        try:
            # 1. Verificar estado proponer_planes_pago
            query = text("""
                SELECT nombre, condicion, estado_siguiente_true, estado_siguiente_default
                FROM Estados_Conversacion 
                WHERE nombre = 'proponer_planes_pago' AND activo = 1
            """)
            
            result = self.db.execute(query).fetchone()
            
            if result:
                print(f"✅ Estado encontrado: {result[0]}")
                print(f"   Condición: {result[1]}")
                print(f"   Estado true: {result[2]}")
                print(f"   Estado default: {result[3]}")
                
                # Verificar si está mal configurado
                if result[2] == 'proponer_planes_pago' or result[3] == 'proponer_planes_pago':
                    issue = "Estado proponer_planes_pago está en bucle (no transiciona)"
                    self.issues_found.append({
                        "type": "CRITICAL",
                        "issue": issue,
                        "location": "Estados_Conversacion",
                        "current_value": f"true={result[2]}, default={result[3]}"
                    })
                    
                    self.recommendations.append(
                        "CRÍTICO: Cambiar estado_siguiente_true a 'confirmar_plan_elegido'"
                    )
                    
                    print(f"❌ PROBLEMA CRÍTICO: {issue}")
                else:
                    print(f"✅ Configuración de transición correcta")
            else:
                issue = "Estado 'proponer_planes_pago' no encontrado"
                self.issues_found.append({
                    "type": "CRITICAL",
                    "issue": issue,
                    "location": "Estados_Conversacion"
                })
                print(f"❌ PROBLEMA CRÍTICO: {issue}")
            
            # 2. Verificar mapeos de keyword patterns para "acepto"
            query = text("""
                SELECT keyword_pattern, bd_condition, confidence_score, state_context
                FROM keyword_condition_patterns 
                WHERE keyword_pattern IN ('acepto', 'pago unico', 'pago único') 
                    AND active = 1
                ORDER BY confidence_score DESC
            """)
            
            patterns = self.db.execute(query).fetchall()
            
            if patterns:
                print(f"\n📋 Patrones encontrados para selección:")
                for pattern in patterns:
                    print(f"   '{pattern[0]}' → {pattern[1]} (confianza: {pattern[2]})")
                    
                    # Verificar si está mal mapeado
                    if pattern[1] == 'cliente_confirma_interes' and pattern[0] in ['acepto', 'pago unico']:
                        issue = f"Pattern '{pattern[0]}' mal mapeado a confirma_interes en lugar de selecciona_plan"
                        self.issues_found.append({
                            "type": "HIGH",
                            "issue": issue,
                            "location": "keyword_condition_patterns",
                            "current_value": pattern[1]
                        })
                        
                        self.recommendations.append(
                            f"Cambiar mapeo de '{pattern[0]}' a 'cliente_selecciona_plan'"
                        )
                        print(f"❌ PROBLEMA: {issue}")
            else:
                issue = "No se encontraron patrones para selección de planes"
                self.issues_found.append({
                    "type": "HIGH",
                    "issue": issue,
                    "location": "keyword_condition_patterns"
                })
                print(f"❌ PROBLEMA: {issue}")
                
        except Exception as e:
            print(f"❌ Error en diagnóstico de transición: {e}")
    
    async def _diagnose_hardcoded_data(self):
        """Diagnosticar datos hardcodeados en templates"""
        
        print("\n💰 DIAGNÓSTICO: Datos Hardcodeados en Templates")
        print("-" * 50)
        
        try:
            # Buscar valores específicos hardcodeados
            hardcoded_values = [
                ('4,173,695', '4173695'),
                ('784,744', '784744'),
                ('626,054', '626054'),
                ('4173695', 'saldo específico'),
                ('784744', 'oferta específica'),
                ('626054', 'cuota específica')
            ]
            
            for value, description in hardcoded_values:
                query = text("""
                    SELECT nombre, mensaje_template
                    FROM Estados_Conversacion 
                    WHERE mensaje_template LIKE :pattern AND activo = 1
                """)
                
                results = self.db.execute(query, {"pattern": f"%{value}%"}).fetchall()
                
                if results:
                    for result in results:
                        issue = f"Valor hardcodeado encontrado: {description} ({value})"
                        self.issues_found.append({
                            "type": "HIGH",
                            "issue": issue,
                            "location": f"Estados_Conversacion.{result[0]}",
                            "current_value": value
                        })
                        
                        self.recommendations.append(
                            f"Reemplazar {value} con variable {{{{saldo_total}}}} o {{{{oferta_2}}}}"
                        )
                        
                        print(f"❌ HARDCODED: {result[0]} contiene {value}")
                        
                        # Mostrar fragmento del template
                        template_fragment = result[1][:100] + "..." if len(result[1]) > 100 else result[1]
                        print(f"   Fragment: {template_fragment}")
            
            if not any(results for _, _ in hardcoded_values 
                      for results in [self.db.execute(text("""
                          SELECT nombre FROM Estados_Conversacion 
                          WHERE mensaje_template LIKE :pattern AND activo = 1
                      """), {"pattern": f"%{value}%"}).fetchall()]):
                print("✅ No se encontraron valores hardcodeados en templates")
                
        except Exception as e:
            print(f"❌ Error en diagnóstico de datos hardcodeados: {e}")
    
    async def _diagnose_table_configuration(self):
        """Diagnosticar configuración de tablas dinámicas"""
        
        print("\n📊 DIAGNÓSTICO: Configuración de Tablas Dinámicas")
        print("-" * 50)
        
        try:
            # Verificar tablas necesarias
            tables_to_check = [
                ('Estados_Conversacion', 'activo = 1'),
                ('ml_intention_mappings', 'active = 1'),
                ('keyword_condition_patterns', 'active = 1'),
                ('condition_evaluators', 'active = 1')
            ]
            
            for table, condition in tables_to_check:
                try:
                    query = text(f"SELECT COUNT(*) FROM {table} WHERE {condition}")
                    count = self.db.execute(query).scalar()
                    
                    print(f"✅ {table}: {count} registros activos")
                    
                    if count == 0:
                        issue = f"Tabla {table} no tiene registros activos"
                        self.issues_found.append({
                            "type": "CRITICAL",
                            "issue": issue,
                            "location": table
                        })
                        
                        self.recommendations.append(
                            f"Insertar datos iniciales en {table}"
                        )
                        
                except Exception as e:
                    issue = f"Error accediendo a tabla {table}: {str(e)}"
                    self.issues_found.append({
                        "type": "CRITICAL",
                        "issue": issue,
                        "location": table
                    })
                    print(f"❌ ERROR: {table} - {e}")
            
            # Verificar mapeos específicos críticos
            critical_mappings = [
                ("CONFIRMACION_EXITOSA", "cliente_confirma_acuerdo"),
                ("SELECCION_PLAN_UNICO", "cliente_selecciona_plan"),
                ("PAGO_UNICO", "cliente_selecciona_plan")
            ]
            
            print(f"\n🔍 Verificando mapeos críticos:")
            for ml_intention, expected_condition in critical_mappings:
                query = text("""
                    SELECT bd_condition FROM ml_intention_mappings 
                    WHERE ml_intention = :intention AND active = 1
                """)
                
                result = self.db.execute(query, {"intention": ml_intention}).fetchone()
                
                if result:
                    if result[0] == expected_condition:
                        print(f"✅ {ml_intention} → {result[0]}")
                    else:
                        issue = f"Mapeo incorrecto: {ml_intention} → {result[0]} (esperado: {expected_condition})"
                        self.issues_found.append({
                            "type": "HIGH",
                            "issue": issue,
                            "location": "ml_intention_mappings",
                            "current_value": result[0]
                        })
                        print(f"❌ {issue}")
                else:
                    issue = f"Mapeo faltante: {ml_intention}"
                    self.issues_found.append({
                        "type": "HIGH",
                        "issue": issue,
                        "location": "ml_intention_mappings"
                    })
                    print(f"❌ FALTANTE: {ml_intention}")
                    
        except Exception as e:
            print(f"❌ Error en diagnóstico de tablas: {e}")
    
    async def _diagnose_message_flow(self):
        """Diagnosticar flujo de mensajes específico del problema"""
        
        print("\n🔄 DIAGNÓSTICO: Flujo de Mensajes Problemático")
        print("-" * 50)
        
        try:
            # Simular el flujo problemático reportado
            test_cases = [
                {
                    "state": "proponer_planes_pago",
                    "message": "pago unico",
                    "expected_transition": "confirmar_plan_elegido"
                },
                {
                    "state": "proponer_planes_pago", 
                    "message": "acepto",
                    "expected_transition": "confirmar_plan_elegido"
                },
                {
                    "state": "confirmar_plan_elegido",
                    "message": "confirmo",
                    "expected_transition": "generar_acuerdo"
                }
            ]
            
            print(f"🧪 Simulando flujo problemático:")
            
            for i, test in enumerate(test_cases, 1):
                print(f"\nTest {i}: '{test['message']}' en '{test['state']}'")
                
                # Buscar mapeo correspondiente
                query = text("""
                    SELECT bd_condition, confidence_score
                    FROM keyword_condition_patterns 
                    WHERE keyword_pattern = :pattern 
                        AND (state_context = :state OR state_context IS NULL)
                        AND active = 1
                    ORDER BY confidence_score DESC
                """)
                
                result = self.db.execute(query, {
                    "pattern": test['message'],
                    "state": test['state']
                }).fetchone()
                
                if result:
                    condition = result[0]
                    confidence = result[1]
                    
                    # Buscar a qué estado lleva esta condición
                    state_query = text("""
                        SELECT estado_siguiente_true
                        FROM Estados_Conversacion 
                        WHERE nombre = :state 
                            AND (condicion = :condition OR condicion IS NULL)
                            AND activo = 1
                    """)
                    
                    state_result = self.db.execute(state_query, {
                        "state": test['state'],
                        "condition": condition
                    }).fetchone()
                    
                    if state_result:
                        actual_transition = state_result[0]
                        
                        if actual_transition == test['expected_transition']:
                            print(f"   ✅ {test['state']} → {actual_transition} (correcto)")
                        else:
                            issue = f"Transición incorrecta: {test['state']} → {actual_transition} (esperado: {test['expected_transition']})"
                            self.issues_found.append({
                                "type": "CRITICAL",
                                "issue": issue,
                                "location": f"Flujo: {test['message']}",
                                "current_value": actual_transition
                            })
                            print(f"   ❌ {issue}")
                    else:
                        issue = f"No se encontró transición para condición '{condition}' en estado '{test['state']}'"
                        self.issues_found.append({
                            "type": "HIGH",
                            "issue": issue,
                            "location": f"Estados_Conversacion.{test['state']}"
                        })
                        print(f"   ❌ {issue}")
                else:
                    issue = f"No se encontró mapeo para '{test['message']}' en contexto '{test['state']}'"
                    self.issues_found.append({
                        "type": "HIGH",
                        "issue": issue,
                        "location": "keyword_condition_patterns"
                    })
                    print(f"   ❌ {issue}")
                    
        except Exception as e:
            print(f"❌ Error en diagnóstico de flujo: {e}")
    
    def _show_diagnostic_summary(self):
        """Mostrar resumen del diagnóstico"""
        
        print("\n" + "=" * 70)
        print("📊 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 70)
        
        # Contar problemas por tipo
        critical_issues = len([i for i in self.issues_found if i['type'] == 'CRITICAL'])
        high_issues = len([i for i in self.issues_found if i['type'] == 'HIGH'])
        total_issues = len(self.issues_found)
        
        print(f"🔍 Total de problemas encontrados: {total_issues}")
        print(f"🚨 Problemas críticos: {critical_issues}")
        print(f"⚠️ Problemas importantes: {high_issues}")
        
        if total_issues == 0:
            print(f"\n🎉 ¡SISTEMA EN PERFECTO ESTADO!")
            print(f"   No se encontraron problemas de configuración")
        else:
            print(f"\n❌ PROBLEMAS ENCONTRADOS:")
            
            for i, issue in enumerate(self.issues_found, 1):
                print(f"\n{i}. [{issue['type']}] {issue['issue']}")
                print(f"   📍 Ubicación: {issue['location']}")
                if 'current_value' in issue:
                    print(f"   💾 Valor actual: {issue['current_value']}")
            
            print(f"\n💡 RECOMENDACIONES:")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"{i}. {rec}")
        
        print("\n" + "=" * 70)
    
    def close(self):
        """Cerrar conexión"""
        self.db.close()

# ============================================================================
# 🚀 FUNCIÓN PRINCIPAL PARA EJECUTAR EL DIAGNÓSTICO
# ============================================================================

async def run_diagnostic():
    """Ejecutar diagnóstico completo"""
    diagnostic = ChatSystemDiagnostic()
    
    try:
        result = await diagnostic.diagnose_complete_system()
        return result
    finally:
        diagnostic.close()

# ============================================================================
# 🛠️ HERRAMIENTA DE LÍNEA DE COMANDOS
# ============================================================================

if __name__ == "__main__":
    print("🔍 HERRAMIENTA DE DIAGNÓSTICO DEL SISTEMA DINÁMICO")
    print("Ejecutando diagnóstico completo...")
    
    result = asyncio.run(run_diagnostic())
    
    if result["system_health"]:
        print("\n✅ Sistema funcionando correctamente")
        exit(0)
    else:
        print(f"\n❌ Se encontraron {len(result['issues_found'])} problemas")
        print("Revisar recomendaciones arriba para solucionarlos")
        exit(1)