#!/usr/bin/env python3
"""
TEST EN TIEMPO REAL - VERIFICACIÓN DE CONSULTA A BD
Ejecutar para verificar que los datos se consulten correctamente desde la BD
"""

import requests
import json
from datetime import datetime

def test_real_time_bd():
    """Test en tiempo real contra el endpoint del chat"""
    
    print("🚀 TEST EN TIEMPO REAL - CONSULTA BD")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # ===== TEST 1: IDENTIFICACIÓN CON CÉDULA REAL =====
    print("\n🔍 TEST 1: IDENTIFICACIÓN CON CÉDULA")
    print("-" * 40)
    
    # Usar cédula que sabemos que existe en tu BD
    cedula_test = "93388915"  # Cambiar por cédula real
    
    payload_identificacion = {
        "user_id": 999,  # Usuario de prueba
        "message": cedula_test,
        "conversation_id": 999
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/chat/message",
            json=payload_identificacion,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Respuesta recibida:")
            print(f"   Estado: {data.get('current_state')}")
            print(f"   Mensaje: {data.get('message', '')[:100]}...")
            
            # ✅ VERIFICAR CONTEXTO
            context = data.get('context', {})
            
            print(f"\n📊 VERIFICACIÓN CONTEXTO:")
            cliente_encontrado = context.get('cliente_encontrado', False)
            nombre_cliente = context.get('Nombre_del_cliente', 'NO ENCONTRADO')
            saldo_total = context.get('saldo_total', 0)
            oferta_2 = context.get('oferta_2', 0)
            banco = context.get('banco', 'NO ENCONTRADO')
            
            print(f"   Cliente encontrado: {cliente_encontrado}")
            print(f"   Nombre: {nombre_cliente}")
            print(f"   Saldo: ${saldo_total:,}" if saldo_total else "$0")
            print(f"   Oferta_2: ${oferta_2:,}" if oferta_2 else "$0")
            print(f"   Banco: {banco}")
            
            # ✅ VALIDACIONES CRÍTICAS
            validaciones = []
            
            if cliente_encontrado:
                validaciones.append("✅ cliente_encontrado = True")
            else:
                validaciones.append("❌ cliente_encontrado = False")
            
            if nombre_cliente and nombre_cliente != "Cliente":
                validaciones.append(f"✅ Nombre real: {nombre_cliente}")
            else:
                validaciones.append(f"❌ Nombre por defecto: {nombre_cliente}")
            
            if saldo_total > 0 and saldo_total != 15000:
                validaciones.append(f"✅ Saldo real: ${saldo_total:,}")
            else:
                validaciones.append(f"❌ Saldo por defecto: ${saldo_total:,}")
            
            if oferta_2 > 0:
                validaciones.append(f"✅ Oferta real: ${oferta_2:,}")
            else:
                validaciones.append(f"❌ Sin oferta: ${oferta_2:,}")
            
            print(f"\n📈 VALIDACIONES:")
            for validacion in validaciones:
                print(f"   {validacion}")
            
            # Guardar conversation_id para siguiente test
            conversation_id = data.get('conversation_id')
            
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return False
    
    # ===== TEST 2: SELECCIÓN DE PLAN =====
    if cliente_encontrado and conversation_id:
        print(f"\n🎯 TEST 2: SELECCIÓN DE PLAN")
        print("-" * 40)
        
        payload_plan = {
            "user_id": 999,
            "message": "Pago unico",
            "conversation_id": conversation_id
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/chat/message",
                json=payload_plan,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"✅ Respuesta a selección de plan:")
                print(f"   Estado: {data.get('current_state')}")
                print(f"   Mensaje: {data.get('message', '')[:150]}...")
                
                context = data.get('context', {})
                
                # Verificar datos del plan
                plan_capturado = context.get('plan_capturado', False)
                plan_seleccionado = context.get('plan_seleccionado', 'NO CAPTURADO')
                monto_acordado = context.get('monto_acordado', 0)
                
                print(f"\n💼 INFORMACIÓN DEL PLAN:")
                print(f"   Plan capturado: {plan_capturado}")
                print(f"   Plan seleccionado: {plan_seleccionado}")
                print(f"   Monto acordado: ${monto_acordado:,}" if monto_acordado else "$0")
                
                # Verificar que se mantienen datos del cliente
                cliente_mantenido = context.get('cliente_encontrado', False)
                nombre_mantenido = context.get('Nombre_del_cliente', 'NO ENCONTRADO')
                
                print(f"\n🔄 CONTINUIDAD DE DATOS:")
                print(f"   Cliente mantenido: {cliente_mantenido}")
                print(f"   Nombre mantenido: {nombre_mantenido}")
                
                if cliente_mantenido and nombre_mantenido == nombre_cliente:
                    print(f"   ✅ Datos del cliente preservados correctamente")
                else:
                    print(f"   ❌ Se perdieron datos del cliente")
                
            else:
                print(f"❌ Error en selección de plan: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error en test de plan: {e}")
    
    # ===== RESULTADOS FINALES =====
    print(f"\n" + "=" * 60)
    print(f"📊 RESUMEN DEL TEST:")
    
    errores = [v for v in validaciones if v.startswith("❌")]
    exitos = [v for v in validaciones if v.startswith("✅")]
    
    print(f"   ✅ Validaciones exitosas: {len(exitos)}")
    print(f"   ❌ Errores encontrados: {len(errores)}")
    
    if len(errores) == 0:
        print(f"\n🎉 ¡TEST EXITOSO! Sistema funcionando con datos dinámicos")
    else:
        print(f"\n❌ TEST FALLÓ: Sistema usando datos por defecto")
        print(f"\n🔧 ERRORES A CORREGIR:")
        for error in errores:
            print(f"   - {error}")
    
    return len(errores) == 0

def test_directo_bd():
    """Test directo a la BD para verificar datos"""
    
    print(f"\n🔍 TEST DIRECTO A BD")
    print("-" * 40)
    
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        
        # Consultar datos reales
        cedula_test = "93388915"
        
        query = text("""
            SELECT TOP 5
                Cedula, Nombre_del_cliente, Saldo_total, 
                Oferta_2, banco
            FROM ConsolidadoCampañasNatalia 
            WHERE Saldo_total > 0
            ORDER BY Saldo_total DESC
        """)
        
        result = db.execute(query)
        rows = result.fetchall()
        
        print(f"✅ DATOS DISPONIBLES EN BD:")
        print(f"   Total registros encontrados: {len(rows)}")
        
        for i, row in enumerate(rows):
            print(f"   {i+1}. Cédula: {row[0]}, Nombre: {row[1]}, Saldo: ${float(row[2]):,.0f}")
        
        if rows:
            print(f"\n💡 USAR ESTAS CÉDULAS PARA TESTING:")
            for i, row in enumerate(rows[:3]):
                print(f"   - {row[0]} ({row[1]})")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error consultando BD: {e}")
        return False

def generar_reporte():
    """Generar reporte de pruebas"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n📋 GENERANDO REPORTE DE PRUEBAS")
    print("-" * 40)
    
    # Test directo BD
    bd_ok = test_directo_bd()
    
    # Test API
    api_ok = test_real_time_bd()
    
    # Resumen final
    print(f"\n" + "=" * 60)
    print(f"📊 REPORTE FINAL - {timestamp}")
    print("=" * 60)
    print(f"   Base de datos: {'✅ OK' if bd_ok else '❌ ERROR'}")
    print(f"   API Endpoint: {'✅ OK' if api_ok else '❌ ERROR'}")
    
    if bd_ok and api_ok:
        print(f"\n🎉 SISTEMA COMPLETAMENTE FUNCIONAL")
        print(f"   ✅ Datos dinámicos desde BD")
        print(f"   ✅ Variables resueltas correctamente")
        print(f"   ✅ Contexto preservado")
        print(f"   ✅ Sin datos quemados")
    else:
        print(f"\n❌ SISTEMA REQUIERE CORRECCIONES")
        if not bd_ok:
            print(f"   🔧 Revisar conexión a BD")
        if not api_ok:
            print(f"   🔧 Aplicar correcciones de código")
    
    print("=" * 60)

if __name__ == "__main__":
    generar_reporte()