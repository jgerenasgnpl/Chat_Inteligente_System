#!/usr/bin/env python3
"""
SCRIPT DE VALIDACIÓN - VERIFICAR DATOS DINÁMICOS
Verifica que no haya datos quemados y todo sea dinámico desde BD
"""

import asyncio
import json
from app.db.session import SessionLocal
from app.services.variable_service import crear_variable_service
from app.api.endpoints.chat import SmartLanguageProcessor

async def test_datos_dinamicos():
    """Test completo de datos dinámicos desde BD"""
    
    print("🧪 INICIANDO VALIDACIÓN DE DATOS DINÁMICOS")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # ===== TEST 1: CONSULTA DIRECTA A BD =====
        print("\n🔍 TEST 1: CONSULTA DIRECTA A BD")
        print("-" * 40)
        
        cedula_test = "93388915"  # Usar cédula real de tu BD
        
        from sqlalchemy import text
        query = text("""
            SELECT TOP 1 
                Nombre_del_cliente, Saldo_total, banco,
                Oferta_1, Oferta_2, 
                Hasta_3_cuotas, Hasta_6_cuotas, Hasta_12_cuotas
            FROM ConsolidadoCampañasNatalia 
            WHERE CAST(Cedula AS VARCHAR) = :cedula
        """)
        
        result = db.execute(query, {"cedula": cedula_test}).fetchone()
        
        if result:
            datos_bd = {
                "nombre": result[0],
                "saldo": int(float(result[1])) if result[1] else 0,
                "banco": result[2],
                "oferta_1": int(float(result[3])) if result[3] else 0,
                "oferta_2": int(float(result[4])) if result[4] else 0,
                "cuotas_3": int(float(result[5])) if result[5] else 0,
                "cuotas_6": int(float(result[6])) if result[6] else 0,
                "cuotas_12": int(float(result[7])) if result[7] else 0
            }
            
            print(f"✅ DATOS BD OBTENIDOS:")
            print(f"   Nombre: {datos_bd['nombre']}")
            print(f"   Saldo: ${datos_bd['saldo']:,}")
            print(f"   Oferta_2: ${datos_bd['oferta_2']:,}")
            print(f"   Banco: {datos_bd['banco']}")
            
            # ✅ VERIFICAR QUE NO SEAN DATOS QUEMADOS
            if datos_bd['saldo'] == 15000:
                print(f"❌ WARNING: Saldo parece ser valor quemado (15000)")
            if datos_bd['nombre'] == "Cliente":
                print(f"❌ WARNING: Nombre parece ser valor quemado ('Cliente')")
            
        else:
            print(f"❌ No se encontraron datos para cédula: {cedula_test}")
            return False
        
        # ===== TEST 2: VARIABLE SERVICE =====
        print(f"\n🔧 TEST 2: VARIABLE SERVICE")
        print("-" * 40)
        
        variable_service = crear_variable_service(db)
        
        # Contexto con datos del cliente
        contexto_test = {
            "cliente_encontrado": True,
            "cedula_detectada": cedula_test,
            "Nombre_del_cliente": datos_bd['nombre'],
            "saldo_total": datos_bd['saldo'],
            "oferta_2": datos_bd['oferta_2'],
            "Oferta_2": datos_bd['oferta_2'],
            "hasta_6_cuotas": datos_bd['cuotas_6'],
            "banco": datos_bd['banco']
        }
        
        # Test de resolución de variables
        template_test = "Hola {{Nombre_del_cliente}}, tu saldo es {{saldo_total}} con {{banco}}. Oferta: {{oferta_2}}"
        
        resultado_variables = variable_service.resolver_variables(template_test, contexto_test)
        
        print(f"✅ TEMPLATE: {template_test}")
        print(f"✅ RESULTADO: {resultado_variables}")
        
        # ✅ VERIFICAR QUE USE DATOS REALES
        if datos_bd['nombre'] not in resultado_variables:
            print(f"❌ ERROR: Nombre real no aparece en resultado")
        if f"${datos_bd['saldo']:,}" not in resultado_variables:
            print(f"❌ ERROR: Saldo real no aparece en resultado")
        if datos_bd['banco'] not in resultado_variables:
            print(f"❌ ERROR: Banco real no aparece en resultado")
        
        # ===== TEST 3: SMART PROCESSOR =====
        print(f"\n🤖 TEST 3: SMART PROCESSOR")
        print("-" * 40)
        
        smart_processor = SmartLanguageProcessor(db)
        
        # Simular procesamiento de selección de plan
        mensaje_test = "Pago unico"
        estado_test = "proponer_planes_pago"
        
        resultado_smart = smart_processor.procesar_mensaje_inteligente(
            mensaje_test, 
            contexto_test, 
            estado_test
        )
        
        print(f"✅ MENSAJE: '{mensaje_test}'")
        print(f"✅ ESTADO: {estado_test}")
        print(f"✅ RESULTADO: {resultado_smart['next_state']}")
        print(f"✅ MÉTODO: {resultado_smart['metodo']}")
        
        contexto_final = resultado_smart['contexto_actualizado']
        
        # ✅ VERIFICAR DATOS EN CONTEXTO FINAL
        print(f"\n📊 VERIFICACIÓN CONTEXTO FINAL:")
        print(f"   Cliente encontrado: {contexto_final.get('cliente_encontrado', False)}")
        print(f"   Nombre: {contexto_final.get('Nombre_del_cliente', 'NO ENCONTRADO')}")
        print(f"   Saldo: ${contexto_final.get('saldo_total', 0):,}")
        print(f"   Plan capturado: {contexto_final.get('plan_capturado', False)}")
        
        if contexto_final.get('plan_capturado'):
            print(f"   Plan seleccionado: {contexto_final.get('plan_seleccionado')}")
            print(f"   Monto acordado: ${contexto_final.get('monto_acordado', 0):,}")
        
        # ===== VALIDACIONES CRÍTICAS =====
        print(f"\n✅ VALIDACIONES CRÍTICAS:")
        print("-" * 40)
        
        validaciones = []
        
        # 1. Cliente encontrado debe ser True
        if contexto_final.get('cliente_encontrado'):
            validaciones.append("✅ cliente_encontrado = True")
        else:
            validaciones.append("❌ cliente_encontrado = False (DEBE SER TRUE)")
        
        # 2. Nombre debe ser real (no "Cliente")
        nombre_final = contexto_final.get('Nombre_del_cliente', '')
        if nombre_final and nombre_final != "Cliente":
            validaciones.append(f"✅ Nombre real: {nombre_final}")
        else:
            validaciones.append(f"❌ Nombre quemado o faltante: {nombre_final}")
        
        # 3. Saldo debe ser real (no 15000 ni 0)
        saldo_final = contexto_final.get('saldo_total', 0)
        if saldo_final > 0 and saldo_final != 15000:
            validaciones.append(f"✅ Saldo real: ${saldo_final:,}")
        else:
            validaciones.append(f"❌ Saldo quemado o faltante: ${saldo_final:,}")
        
        # 4. Ofertas deben ser reales
        oferta_final = contexto_final.get('oferta_2', 0)
        if oferta_final > 0:
            validaciones.append(f"✅ Oferta real: ${oferta_final:,}")
        else:
            validaciones.append(f"❌ Oferta faltante: ${oferta_final:,}")
        
        # 5. Verificar que no hay valores por defecto sospechosos
        valores_sospechosos = {
            'saldo_total': [15000, 0],
            'oferta_2': [10500, 0],
            'hasta_6_cuotas': [2500, 0]
        }
        
        for campo, valores_prohibidos in valores_sospechosos.items():
            valor_actual = contexto_final.get(campo, 0)
            if valor_actual in valores_prohibidos:
                validaciones.append(f"⚠️ Posible valor quemado en {campo}: {valor_actual}")
        
        # ===== RESULTADOS FINALES =====
        print(f"\n📊 RESULTADOS FINALES:")
        print("=" * 70)
        
        for validacion in validaciones:
            print(f"   {validacion}")
        
        errores = [v for v in validaciones if v.startswith("❌")]
        warnings = [v for v in validaciones if v.startswith("⚠️")]
        exitos = [v for v in validaciones if v.startswith("✅")]
        
        print(f"\n📈 RESUMEN:")
        print(f"   ✅ Exitosos: {len(exitos)}")
        print(f"   ⚠️ Advertencias: {len(warnings)}")
        print(f"   ❌ Errores: {len(errores)}")
        
        if len(errores) == 0:
            print(f"\n🎉 ¡VALIDACIÓN EXITOSA! Sistema 100% dinámico desde BD")
            return True
        else:
            print(f"\n❌ VALIDACIÓN FALLÓ: {len(errores)} errores encontrados")
            print(f"\n🔧 ACCIONES REQUERIDAS:")
            for error in errores:
                print(f"   - {error}")
            return False
        
    except Exception as e:
        print(f"❌ ERROR EN VALIDACIÓN: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

async def test_serialization():
    """Test específico de serialización JSON"""
    print(f"\n🔧 TEST SERIALIZACIÓN JSON:")
    print("-" * 40)
    
    from decimal import Decimal
    from datetime import datetime
    
    # Datos con tipos problemáticos
    datos_test = {
        "nombre": "PEDRO VARGAS",
        "saldo": Decimal('1784744'),
        "oferta": Decimal('1249321'),
        "fecha": datetime.now(),
        "cliente_encontrado": True,
        "valores_enteros": [Decimal('1000'), Decimal('2000')]
    }
    
    print(f"✅ Datos originales: {type(datos_test['saldo'])}")
    
    # Test de serialización segura
    try:
        from app.api.endpoints.chat import safe_json_dumps, limpiar_contexto_para_bd
        
        # Limpiar datos
        datos_limpios = limpiar_contexto_para_bd(datos_test)
        print(f"✅ Datos limpiados: {type(datos_limpios['saldo'])}")
        
        # Serializar
        json_result = safe_json_dumps(datos_limpios)
        print(f"✅ JSON generado: {json_result[:100]}...")
        
        # Deserializar para verificar
        datos_recuperados = json.loads(json_result)
        print(f"✅ Datos recuperados: {datos_recuperados['nombre']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en serialización: {e}")
        return False

# ===== FUNCIÓN PRINCIPAL =====
async def main():
    """Función principal de validación"""
    print("🚀 INICIANDO VALIDACIÓN COMPLETA DEL SISTEMA")
    print("=" * 80)
    
    # Test 1: Datos dinámicos
    resultado_datos = await test_datos_dinamicos()
    
    # Test 2: Serialización
    resultado_serialization = await test_serialization()
    
    print(f"\n" + "=" * 80)
    print(f"📊 RESULTADOS FINALES DE VALIDACIÓN:")
    print(f"   Datos dinámicos: {'✅ OK' if resultado_datos else '❌ FALLO'}")
    print(f"   Serialización: {'✅ OK' if resultado_serialization else '❌ FALLO'}")
    
    if resultado_datos and resultado_serialization:
        print(f"\n🎉 ¡SISTEMA COMPLETAMENTE VALIDADO!")
        print(f"   - Datos 100% dinámicos desde BD")
        print(f"   - Sin valores quemados")
        print(f"   - Serialización JSON correcta")
        print(f"   - Flujo de contexto preservado")
    else:
        print(f"\n❌ SISTEMA REQUIERE CORRECCIONES")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())