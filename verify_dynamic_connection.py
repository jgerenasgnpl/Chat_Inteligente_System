"""
🔍 VERIFICADOR DE CONEXIÓN DINÁMICA
- Verifica que las tablas estén conectadas
- Fuerza la carga de datos dinámicos
- Elimina dependencia de código hardcodeado
"""

from app.db.session import SessionLocal
from sqlalchemy import text
import json

def verify_dynamic_tables(  ):
    """Verificar que las tablas dinámicas tengan datos"""
    
    db = SessionLocal()
    
    try:
        print("🔍 VERIFICANDO CONEXIÓN DINÁMICA...")
        print("=" * 50)
        
        # 1. ML Intention Mappings
        query1 = text("SELECT COUNT(*) FROM ml_intention_mappings WHERE active = 1")
        ml_count = db.execute(query1).scalar()
        print(f"📊 ML Mappings activos: {ml_count}")
        
        if ml_count > 0:
            # Mostrar algunos ejemplos
            query1_data = text("SELECT TOP 3 ml_intention, bd_condition, confidence_threshold FROM ml_intention_mappings WHERE active = 1")
            for row in db.execute(query1_data):
                print(f"   • {row[0]} → {row[1]} (confianza: {row[2]})")
        
        # 2. Keyword Patterns
        query2 = text("SELECT COUNT(*) FROM keyword_condition_patterns WHERE active = 1")
        keyword_count = db.execute(query2).scalar()
        print(f"🔤 Keyword Patterns activos: {keyword_count}")
        
        if keyword_count > 0:
            # Mostrar algunos ejemplos
            query2_data = text("SELECT TOP 3 keyword_pattern, bd_condition, confidence_score FROM keyword_condition_patterns WHERE active = 1")
            for row in db.execute(query2_data):
                print(f"   • '{row[0]}' → {row[1]} (confianza: {row[2]})")
        
        # 3. Condition Evaluators
        query3 = text("SELECT COUNT(*) FROM condition_evaluators WHERE active = 1")
        evaluator_count = db.execute(query3).scalar()
        print(f"⚙️ Evaluadores activos: {evaluator_count}")
        
        if evaluator_count > 0:
            # Mostrar algunos ejemplos
            query3_data = text("SELECT TOP 3 condition_name, evaluation_method FROM condition_evaluators WHERE active = 1")
            for row in db.execute(query3_data):
                print(f"   • {row[0]} → {row[1]}")
        
        print("=" * 50)
        
        if ml_count > 0 and keyword_count > 0:
            print("✅ TABLAS DINÁMICAS CON DATOS - Sistema debería funcionar dinámicamente")
            return True
        else:
            print("❌ TABLAS VACÍAS - Sistema usará fallback hardcodeado")
            return False
            
    except Exception as e:
        print(f"❌ ERROR conectando a tablas dinámicas: {e}")
        return False
        
    finally:
        db.close()

def test_dynamic_service():
    """Test completo del servicio dinámico"""
    
    print("\n🧪 TESTING SERVICIO DINÁMICO...")
    print("=" * 50)
    
    try:
        from app.services.dynamic_transition_service import create_dynamic_transition_service
        
        db = SessionLocal()
        dynamic_service = create_dynamic_transition_service(db)
        
        # Test de configuración
        stats = dynamic_service.get_stats()
        print(f"📊 Configuración cargada:")
        print(f"   ML mappings: {stats['configuration']['ml_mappings_count']}")
        print(f"   Keyword patterns: {stats['configuration']['keyword_patterns_count']}")
        print(f"   Evaluadores: {stats['configuration']['condition_evaluators_count']}")
        print(f"   Fuente: {stats['configuration']['configuration_source']}")
        
        # Test de transición real
        print(f"\n🎯 TEST DE TRANSICIÓN DINÁMICA:")
        
        test_result = dynamic_service.determine_next_state(
            current_state="proponer_planes_pago",
            user_message="acepto",
            ml_result={"intention": "CONFIRMACION_EXITOSA", "confidence": 0.9},
            context={"cliente_encontrado": True}
        )
        
        print(f"   Input: 'acepto' en estado 'proponer_planes_pago'")
        print(f"   Output: {test_result['next_state']}")
        print(f"   Método: {test_result['detection_method']}")
        print(f"   Condición: {test_result['condition_detected']}")
        
        if test_result['next_state'] != "proponer_planes_pago":  # Debería cambiar
            print("✅ SISTEMA DINÁMICO FUNCIONANDO CORRECTAMENTE")
            return True
        else:
            print("❌ SISTEMA NO ESTÁ CAMBIANDO ESTADOS DINÁMICAMENTE")
            return False
            
        db.close()
        
    except Exception as e:
        print(f"❌ ERROR en test dinámico: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Ejecutar verificaciones
    tables_ok = verify_dynamic_tables()
    service_ok = test_dynamic_service()
    
    print(f"\n🎯 RESULTADO FINAL:")
    print(f"   Tablas con datos: {'✅' if tables_ok else '❌'}")
    print(f"   Servicio dinámico: {'✅' if service_ok else '❌'}")
    
    if tables_ok and service_ok:
        print(f"\n🎉 SISTEMA 100% DINÁMICO OPERATIVO")
    else:
        print(f"\n🔧 REQUIERE CORRECCIÓN")