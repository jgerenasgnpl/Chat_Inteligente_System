"""
CREAR NUEVO ARCHIVO: setup_dynamic_system.py
Script para configurar el sistema dinámico automáticamente
"""

from app.db.session import SessionLocal
from sqlalchemy import text

def setup_complete_dynamic_system():
    """Configurar sistema dinámico completo automáticamente"""
    
    print("🚀 CONFIGURANDO SISTEMA 100% DINÁMICO")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 1. Verificar que las tablas existen
        print("📋 Verificando tablas...")
        
        tables_to_check = [
            'ml_intention_mappings',
            'keyword_condition_patterns', 
            'condition_evaluators',
            'transition_decision_log'
        ]
        
        for table in tables_to_check:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"   ✅ {table}: {result} registros")
            except Exception as e:
                print(f"   ❌ {table}: Error - {e}")
                print(f"   💡 Ejecutar script SQL de creación de tablas")
                return False
        
        # 2. Verificar datos iniciales
        print("\n📊 Verificando datos iniciales...")
        
        ml_count = db.execute(text("SELECT COUNT(*) FROM ml_intention_mappings WHERE active = 1")).scalar()
        keyword_count = db.execute(text("SELECT COUNT(*) FROM keyword_condition_patterns WHERE active = 1")).scalar()
        evaluator_count = db.execute(text("SELECT COUNT(*) FROM condition_evaluators WHERE active = 1")).scalar()
        
        print(f"   🎯 ML mappings activos: {ml_count}")
        print(f"   🔤 Keyword patterns activos: {keyword_count}")
        print(f"   ⚙️ Evaluadores activos: {evaluator_count}")
        
        if ml_count == 0 or keyword_count == 0:
            print(f"   ⚠️ Faltan datos iniciales. Ejecutar script de inserción de datos.")
            return False
        
        # 3. Test básico del sistema
        print("\n🧪 Test básico del sistema...")
        
        from app.services.dynamic_transition_service import create_dynamic_transition_service
        dynamic_service = create_dynamic_transition_service(db)
        
        # Test simple
        test_result = dynamic_service.determine_next_state(
            current_state="proponer_planes_pago",
            user_message="acepto",
            ml_result={"intention": "CONFIRMACION_EXITOSA", "confidence": 0.9},
            context={"cliente_encontrado": True}
        )
        
        if test_result['next_state'] == "confirmar_plan_elegido":
            print(f"   ✅ Test básico pasó: proponer_planes_pago → confirmar_plan_elegido")
        else:
            print(f"   ❌ Test básico falló: obtuvo {test_result['next_state']}")
            return False
        
        print(f"\n🎉 ¡SISTEMA DINÁMICO CONFIGURADO CORRECTAMENTE!")
        print(f"📋 El sistema está listo para usar sin código hardcodeado")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error configurando sistema: {e}")
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    setup_complete_dynamic_system()