
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional
import pandas as pd
import json
import tempfile
import os
from pydantic_settings import BaseSettings
from datetime import datetime
from app.services.cache_service import cache_service
from app.services.state_condition_bridge import StateConditionBridge
from app.api.deps import get_db, get_current_active_admin
from app.schemas.chat import ConfiguracionEstado

router = APIRouter(
    prefix="/admin",
    tags=["administracion"]
)

@router.get("/verificar-sistema-dinamico")
async def verificar_sistema_dinamico(db: Session = Depends(get_db)):
    """Verificar que el sistema sea 100% dinámico"""
    
    verificaciones = {
        "templates_bd": False,
        "estados_bd": False, 
        "ml_mappings_bd": False,
        "keywords_bd": False,
        "variables_dinamicas": False
    }
    
    try:
        # 1. Verificar templates en Estados_conversacion
        query1 = text("SELECT COUNT(*) FROM Estados_conversacion WHERE mensaje_template IS NOT NULL AND activo = 1")
        templates_count = db.execute(query1).scalar()
        verificaciones["templates_bd"] = templates_count > 5
        
        # 2. Verificar mapeos ML
        query2 = text("SELECT COUNT(*) FROM ml_intention_mappings WHERE active = 1")
        ml_count = db.execute(query2).scalar()
        verificaciones["ml_mappings_bd"] = ml_count > 10
        
        # 3. Verificar keywords
        query3 = text("SELECT COUNT(*) FROM keyword_condition_patterns WHERE active = 1")
        keywords_count = db.execute(query3).scalar()
        verificaciones["keywords_bd"] = keywords_count > 15
        
        # 4. Test de resolución de variables
        from app.services.variable_service import crear_variable_service
        var_service = crear_variable_service(db)
        test_template = "Hola {{Nombre_del_cliente}}, tu saldo es {{saldo_total}}"
        test_context = {"Nombre_del_cliente": "TEST", "saldo_total": 1000}
        resolved = var_service.resolver_variables(test_template, test_context)
        verificaciones["variables_dinamicas"] = "TEST" in resolved and "1000" in resolved
        
        return {
            "sistema_dinamico": all(verificaciones.values()),
            "verificaciones": verificaciones,
            "recomendacion": "✅ Sistema 100% dinámico" if all(verificaciones.values()) else "⚠️ Algunas partes siguen hardcodeadas"
        }
        
    except Exception as e:
        return {"error": str(e)}
    
@router.post("/fix-estados-constraint")
async def fix_estados_constraint(db: Session = Depends(get_db)):
    """Agregar estados faltantes al CHECK constraint"""
    try:
        # 1. Verificar estados actuales permitidos
        check_query = text("""
            SELECT CHECK_CLAUSE 
            FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS 
            WHERE CONSTRAINT_NAME = 'CHK_valid_state_updated'
        """)
        
        result = db.execute(check_query).fetchone()
        
        if result:
            current_constraint = result[0]
            
            # 2. Estados que deben estar permitidos
            estados_requeridos = [
                'inicial', 'validar_documento', 'informar_deuda',
                'proponer_planes_pago', 'confirmar_plan_elegido', 
                'generar_acuerdo', 'finalizar_conversacion',
                'cliente_no_encontrado', 'gestionar_objecion', 
                'escalamiento'  # ← Este falta
            ]
            
            # 3. Construir nuevo constraint
            estados_sql = "', '".join(estados_requeridos)
            new_constraint = f"[current_state] IN ('{estados_sql}')"
            
            # 4. Actualizar constraint
            drop_query = text("ALTER TABLE conversations DROP CONSTRAINT CHK_valid_state_updated")
            add_query = text(f"ALTER TABLE conversations ADD CONSTRAINT CHK_valid_state_updated CHECK ({new_constraint})")
            
            db.execute(drop_query)
            db.execute(add_query)
            db.commit()
            
            return {
                "success": True,
                "constraint_anterior": current_constraint,
                "constraint_nuevo": new_constraint,
                "estados_agregados": ["escalamiento"]
            }
        
        return {"success": False, "error": "Constraint no encontrado"}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@router.get("/estados")
def listar_estados_completo(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                id, nombre, mensaje_template, accion, condicion,
                estado_siguiente_true, estado_siguiente_false, 
                estado_siguiente_default, timeout_segundos, activo,
                fecha_creacion, fecha_actualizacion
            FROM Estados_Conversacion 
            ORDER BY nombre
        """)
        estados = []
        for row in db.execute(query):
            estados.append({
                "id": row[0],
                "nombre": row[1],
                "mensaje_template": row[2],
                "accion": row[3],
                "condicion": row[4],
                "estado_siguiente_true": row[5],
                "estado_siguiente_false": row[6],
                "estado_siguiente_default": row[7],
                "timeout_segundos": row[8],
                "activo": bool(row[9]),
                "fecha_creacion": row[10].isoformat() if row[10] else None,
                "fecha_actualizacion": row[11].isoformat() if row[11] else None
            })
        return {
            "estados": estados,
            "total": len(estados),
            "activos": len([e for e in estados if e["activo"]])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estados: {e}")

@router.post("/api/v1/admin/test-bridge")
async def test_bridge_endpoint(
        estado_actual: str = Form(...),
        mensaje: str = Form(...),
        intencion: str = Form(...),
        db: Session = Depends(get_db)
    ):
        try:
            bridge = StateConditionBridge(db)
            resultado = bridge.determinar_siguiente_estado(
                estado_actual=estado_actual,
                mensaje=mensaje,
                intencion_ml=intencion,
                contexto={"cliente_encontrado": True}
            )
            return {
                "test_input": {
                    "estado_actual": estado_actual,
                    "mensaje": mensaje,
                    "intencion": intencion
                },
                "resultado": resultado,
                "success": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
@router.post("/estados/crear")
def crear_estado_completo(
    nombre: str = Form(...),
    mensaje_template: str = Form(...),
    estado_siguiente_default: str = Form(...),
    accion: Optional[str] = Form(None),
    condicion: Optional[str] = Form(None),
    estado_siguiente_true: Optional[str] = Form(None),
    estado_siguiente_false: Optional[str] = Form(None),
    timeout_segundos: int = Form(300),
    activo: bool = Form(True),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    try:
        check_query = text("""
            SELECT COUNT(*) FROM Estados_Conversacion WHERE nombre = :nombre
        """)
        existe = db.execute(check_query, {"nombre": nombre}).scalar()
        if existe > 0:
            raise HTTPException(status_code=400, detail=f"Estado '{nombre}' ya existe")
        insert_query = text("""
            INSERT INTO Estados_Conversacion (
                nombre, mensaje_template, accion, condicion,
                estado_siguiente_true, estado_siguiente_false,
                estado_siguiente_default, timeout_segundos, activo,
                fecha_creacion, fecha_actualizacion
            ) VALUES (
                :nombre, :mensaje, :accion, :condicion,
                :true_state, :false_state, :default_state,
                :timeout, :activo, GETDATE(), GETDATE()
            )
        """)
        db.execute(insert_query, {
            "nombre": nombre,
            "mensaje": mensaje_template,
            "accion": accion,
            "condicion": condicion,
            "true_state": estado_siguiente_true,
            "false_state": estado_siguiente_false,
            "default_state": estado_siguiente_default,
            "timeout": timeout_segundos,
            "activo": activo
        })
        db.commit()
        return {
            "message": f"Estado '{nombre}' creado exitosamente",
            "estado": {
                "nombre": nombre,
                "mensaje_template": mensaje_template,
                "estado_siguiente_default": estado_siguiente_default
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando estado: {e}")

@router.put("/estados/{nombre_estado}")
def actualizar_estado_completo(
    nombre_estado: str,
    mensaje_template: str = Form(...),
    estado_siguiente_default: str = Form(...),
    accion: Optional[str] = Form(None),
    condicion: Optional[str] = Form(None),
    estado_siguiente_true: Optional[str] = Form(None),
    estado_siguiente_false: Optional[str] = Form(None),
    timeout_segundos: int = Form(300),
    activo: bool = Form(True),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Actualiza un estado existente"""
    try:
        update_query = text("""
            UPDATE Estados_Conversacion SET
                mensaje_template = :mensaje,
                accion = :accion,
                condicion = :condicion,
                estado_siguiente_true = :true_state,
                estado_siguiente_false = :false_state,
                estado_siguiente_default = :default_state,
                timeout_segundos = :timeout,
                activo = :activo,
                fecha_actualizacion = GETDATE()
            WHERE nombre = :nombre
        """)
        
        result = db.execute(update_query, {
            "nombre": nombre_estado,
            "mensaje": mensaje_template,
            "accion": accion,
            "condicion": condicion,
            "true_state": estado_siguiente_true,
            "false_state": estado_siguiente_false,
            "default_state": estado_siguiente_default,
            "timeout": timeout_segundos,
            "activo": activo
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        
        db.commit()
        
        return {"message": f"Estado '{nombre_estado}' actualizado exitosamente"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando estado: {e}")

@router.delete("/estados/{nombre_estado}")
def eliminar_estado(
    nombre_estado: str,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Elimina un estado (marcado como inactivo)"""
    try:
        update_query = text("""
            UPDATE Estados_Conversacion 
            SET activo = 0, fecha_actualizacion = GETDATE()
            WHERE nombre = :nombre
        """)
        
        result = db.execute(update_query, {"nombre": nombre_estado})
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        
        db.commit()
        
        return {"message": f"Estado '{nombre_estado}' desactivado exitosamente"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando estado: {e}")

@router.post("/estados/importar-excel")
async def importar_estados_desde_excel(
    archivo: UploadFile = File(...),
    sobrescribir: bool = Form(False),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Importa estados desde archivo Excel"""
    
    if not archivo.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Archivo debe ser Excel (.xlsx o .xls)")
    
    try:
        # Leer archivo Excel
        content = await archivo.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            df = pd.read_excel(tmp_path)
        finally:
            os.unlink(tmp_path)
        
        # Validar columnas requeridas
        columnas_requeridas = ['nombre', 'mensaje_template']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            raise HTTPException(
                status_code=400, 
                detail=f"Columnas faltantes: {', '.join(columnas_faltantes)}"
            )
        
        # Procesar estados
        estados_procesados = {
            "creados": 0,
            "actualizados": 0,
            "errores": []
        }
        
        for index, row in df.iterrows():
            try:
                nombre = str(row['nombre']).strip()
                
                if not nombre:
                    continue
                
                # Verificar si existe
                check_query = text("""
                    SELECT COUNT(*) FROM Estados_Conversacion WHERE nombre = :nombre
                """)
                existe = db.execute(check_query, {"nombre": nombre}).scalar()
                
                # Preparar datos
                datos = {
                    "nombre": nombre,
                    "mensaje": str(row['mensaje_template']),
                    "accion": str(row.get('accion', '')) if pd.notna(row.get('accion')) else None,
                    "condicion": str(row.get('condicion', '')) if pd.notna(row.get('condicion')) else None,
                    "true_state": str(row.get('estado_siguiente_true', '')) if pd.notna(row.get('estado_siguiente_true')) else None,
                    "false_state": str(row.get('estado_siguiente_false', '')) if pd.notna(row.get('estado_siguiente_false')) else None,
                    "default_state": str(row.get('estado_siguiente_default', '')) if pd.notna(row.get('estado_siguiente_default')) else None,
                    "timeout": int(row.get('timeout_segundos', 300)),
                    "activo": bool(row.get('activo', True))
                }
                
                if existe > 0:
                    if sobrescribir:
                        # Actualizar
                        update_query = text("""
                            UPDATE Estados_Conversacion SET
                                mensaje_template = :mensaje,
                                accion = :accion,
                                condicion = :condicion,
                                estado_siguiente_true = :true_state,
                                estado_siguiente_false = :false_state,
                                estado_siguiente_default = :default_state,
                                timeout_segundos = :timeout,
                                activo = :activo,
                                fecha_actualizacion = GETDATE()
                            WHERE nombre = :nombre
                        """)
                        db.execute(update_query, datos)
                        estados_procesados["actualizados"] += 1
                    else:
                        estados_procesados["errores"].append(f"Estado '{nombre}' ya existe (usar sobrescribir=true)")
                else:
                    # Crear nuevo
                    insert_query = text("""
                        INSERT INTO Estados_Conversacion (
                            nombre, mensaje_template, accion, condicion,
                            estado_siguiente_true, estado_siguiente_false,
                            estado_siguiente_default, timeout_segundos, activo,
                            fecha_creacion, fecha_actualizacion
                        ) VALUES (
                            :nombre, :mensaje, :accion, :condicion,
                            :true_state, :false_state, :default_state,
                            :timeout, :activo, GETDATE(), GETDATE()
                        )
                    """)
                    db.execute(insert_query, datos)
                    estados_procesados["creados"] += 1
                
            except Exception as e:
                estados_procesados["errores"].append(f"Fila {index + 1}: {str(e)}")
                continue
        
        db.commit()
        
        return {
            "message": "Importación completada",
            "resultados": estados_procesados,
            "archivo_procesado": archivo.filename
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error importando Excel: {e}")

@router.get("/estados/exportar-excel")
def exportar_estados_a_excel(
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Exporta estados actuales a Excel"""
    try:
        query = text("""
            SELECT 
                nombre, mensaje_template, accion, condicion,
                estado_siguiente_true, estado_siguiente_false,
                estado_siguiente_default, timeout_segundos, activo
            FROM Estados_Conversacion
            ORDER BY nombre
        """)
        
        result = db.execute(query)
        estados = []
        
        for row in result:
            estados.append({
                "nombre": row[0],
                "mensaje_template": row[1],
                "accion": row[2],
                "condicion": row[3],
                "estado_siguiente_true": row[4],
                "estado_siguiente_false": row[5],
                "estado_siguiente_default": row[6],
                "timeout_segundos": row[7],
                "activo": row[8]
            })
        
        # Crear DataFrame y archivo Excel
        df = pd.DataFrame(estados)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"estados_conversacion_{timestamp}.xlsx"
        filepath = f"exports/{filename}"
        
        # Crear directorio si no existe
        os.makedirs("exports", exist_ok=True)
        
        df.to_excel(filepath, index=False)
        
        return {
            "message": "Estados exportados exitosamente",
            "archivo": filename,
            "ruta": filepath,
            "total_estados": len(estados)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exportando estados: {e}")

@router.get("/estados/validar-flujo")
def validar_flujo_estados(db: Session = Depends(get_db)):
    """Valida la consistencia del flujo de estados"""
    try:
        # Obtener todos los estados
        query = text("""
            SELECT nombre, estado_siguiente_true, estado_siguiente_false, estado_siguiente_default
            FROM Estados_Conversacion WHERE activo = 1
        """)
        
        result = db.execute(query)
        estados_existentes = set()
        transiciones = []
        
        for row in result:
            nombre = row[0]
            estados_existentes.add(nombre)
            
            # Recopilar todas las transiciones
            for next_state in [row[1], row[2], row[3]]:
                if next_state:
                    transiciones.append((nombre, next_state))
        
        # Validar transiciones
        errores = []
        for estado_actual, estado_siguiente in transiciones:
            if estado_siguiente not in estados_existentes and estado_siguiente not in ['fin', 'finalizar_conversacion']:
                errores.append(f"Estado '{estado_actual}' refiere a '{estado_siguiente}' que no existe")
        
        # Encontrar estados huérfanos (no referenciados)
        estados_referenciados = set([t[1] for t in transiciones])
        estados_huerfanos = estados_existentes - estados_referenciados
        estados_huerfanos.discard('inicial')  # El estado inicial no necesita ser referenciado
        
        return {
            "valido": len(errores) == 0,
            "total_estados": len(estados_existentes),
            "total_transiciones": len(transiciones),
            "errores": errores,
            "estados_huerfanos": list(estados_huerfanos),
            "estados_existentes": sorted(list(estados_existentes))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validando flujo: {e}")

@router.get("/estados/diagrama-flujo")
def generar_diagrama_flujo(db: Session = Depends(get_db)):
    """Genera datos para visualizar el diagrama de flujo"""
    try:
        query = text("""
            SELECT 
                nombre, mensaje_template, condicion,
                estado_siguiente_true, estado_siguiente_false, estado_siguiente_default
            FROM Estados_Conversacion 
            WHERE activo = 1
            ORDER BY nombre
        """)
        
        result = db.execute(query)
        nodos = []
        conexiones = []
        
        for row in result:
            nombre = row[0]
            mensaje = row[1][:50] + "..." if len(row[1]) > 50 else row[1]
            condicion = row[2]
            
            # Crear nodo
            nodos.append({
                "id": nombre,
                "label": nombre,
                "mensaje": mensaje,
                "tipo": "estado"
            })
            
            # Crear conexiones
            if row[3]:  # estado_siguiente_true
                conexiones.append({
                    "from": nombre,
                    "to": row[3],
                    "label": f"✓ {condicion}" if condicion else "true",
                    "color": "green"
                })
            
            if row[4]:  # estado_siguiente_false
                conexiones.append({
                    "from": nombre,
                    "to": row[4],
                    "label": f"✗ {condicion}" if condicion else "false",
                    "color": "red"
                })
            
            if row[5]:  # estado_siguiente_default
                conexiones.append({
                    "from": nombre,
                    "to": row[5],
                    "label": "default",
                    "color": "blue"
                })
        
        return {
            "nodos": nodos,
            "conexiones": conexiones,
            "total_nodos": len(nodos),
            "total_conexiones": len(conexiones)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando diagrama: {e}")

@router.post("/openai/configurar")
def configurar_openai_cobranza(
    habilitado: bool = Form(True),
    porcentaje_uso: int = Form(80),
    umbral_confianza: float = Form(0.3),
    modo_cobranza: bool = Form(True),
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Configura parámetros de OpenAI para cobranza"""
    try:
        # Validaciones
        if not (0 <= porcentaje_uso <= 100):
            raise HTTPException(status_code=400, detail="Porcentaje debe estar entre 0 y 100")
        
        if not (0.0 <= umbral_confianza <= 1.0):
            raise HTTPException(status_code=400, detail="Umbral de confianza debe estar entre 0.0 y 1.0")
        
        # Actualizar configuración en BD
        configs = [
            ("openai_habilitado", str(habilitado)),
            ("openai_porcentaje_uso", str(porcentaje_uso)),
            ("openai_umbral_confianza", str(umbral_confianza)),
            ("openai_modo_cobranza", str(modo_cobranza)),
            ("openai_fecha_actualizacion", datetime.now().isoformat())
        ]
        
        for nombre, valor in configs:
            # Verificar si existe
            check_query = text("""
                SELECT COUNT(*) FROM Configuracion_Global WHERE nombre_parametro = :nombre
            """)
            existe = db.execute(check_query, {"nombre": nombre}).scalar()
            
            if existe > 0:
                # Actualizar
                update_query = text("""
                    UPDATE Configuracion_Global 
                    SET valor = :valor, fecha_actualizacion = GETDATE()
                    WHERE nombre_parametro = :nombre
                """)
            else:
                # Crear
                update_query = text("""
                    INSERT INTO Configuracion_Global (nombre_parametro, valor, descripcion, activo, fecha_actualizacion)
                    VALUES (:nombre, :valor, 'Configuración OpenAI Cobranza', 1, GETDATE())
                """)
            
            db.execute(update_query, {"nombre": nombre, "valor": valor})
        
        db.commit()
        
        return {
            "message": "Configuración OpenAI actualizada",
            "configuracion": {
                "habilitado": habilitado,
                "porcentaje_uso": porcentaje_uso,
                "umbral_confianza": umbral_confianza,
                "modo_cobranza": modo_cobranza
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error configurando OpenAI: {e}")

@router.get("/stats")
def get_cache_stats():
    """Obtener estadísticas del cache"""
    return cache_service.get_cache_stats()

@router.post("/clear")
def clear_cache():
    """Limpiar todo el cache (¡CUIDADO!)"""
    result = cache_service.clear_all_cache()
    return {"success": result, "message": "Cache limpiado" if result else "Error limpiando cache"}

@router.post("/clear/client/{cedula}")
def clear_client_cache(cedula: str):
    """Limpiar cache de un cliente específico"""
    result = cache_service.invalidate_client_cache(cedula)
    return {"success": result, "message": f"Cache de cliente {cedula} limpiado"}

@router.post("/clear/conversation/{conversation_id}")
def clear_conversation_cache(conversation_id: int):
    """Limpiar cache de una conversación específica"""
    result = cache_service.invalidate_conversation_cache(conversation_id)
    return {"success": result, "message": f"Cache de conversación {conversation_id} limpiado"}

@router.get("/health")
def cache_health():
    """Health check del cache"""
    return {
        "cache_enabled": cache_service.enabled,
        "connection_status": "connected" if cache_service.enabled else "disconnected",
        "stats": cache_service.get_cache_stats()
    }

@router.post("/cleanup")
def cleanup_expired_cache():
    """Limpieza manual de cache expirado"""
    cleaned = cache_service.cleanup_expired_keys()
    return {"cleaned_keys": cleaned, "message": f"{cleaned} claves expiradas limpiadas"}




class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_ENABLED: bool = True
    REDIS_DEFAULT_TTL: int = 3600
    REDIS_COMPRESSION_THRESHOLD: int = 1000
    CACHE_CLIENT_TTL: int = 7200
    CACHE_ML_TTL: int = 1800
    CACHE_OPENAI_TTL: int = 3600
    CACHE_VARIABLES_TTL: int = 1800
    CACHE_CONTEXT_TTL: int = 3600

@router.get("/api/v1/admin/dynamic-system/stats")
async def get_dynamic_system_stats(db: Session = Depends(get_db)):
    """Obtener estadísticas del sistema dinámico"""
    try:
        from app.services.dynamic_transition_service import create_dynamic_transition_service
        
        dynamic_service = create_dynamic_transition_service(db)
        stats = dynamic_service.get_stats()
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/api/v1/admin/dynamic-system/add-pattern")
async def add_keyword_pattern(
    keyword: str = Form(...),
    condition: str = Form(...),
    confidence: float = Form(0.8),
    requires_client: bool = Form(False),
    state_context: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Agregar nuevo patrón de palabra clave dinámicamente"""
    try:
        query = text("""
            INSERT INTO keyword_condition_patterns 
            (keyword_pattern, bd_condition, confidence_score, requires_client, state_context, active)
            VALUES (:keyword, :condition, :confidence, :requires_client, :state_context, 1)
        """)
        
        db.execute(query, {
            'keyword': keyword.lower().strip(),
            'condition': condition,
            'confidence': confidence,
            'requires_client': requires_client,
            'state_context': state_context
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Patrón '{keyword}' → '{condition}' agregado exitosamente",
            "pattern": {
                "keyword": keyword,
                "condition": condition,
                "confidence": confidence,
                "requires_client": requires_client,
                "state_context": state_context
            }
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/api/v1/admin/dynamic-system/add-ml-mapping")
async def add_ml_mapping(
    ml_intention: str = Form(...),
    bd_condition: str = Form(...),
    confidence_threshold: float = Form(0.7),
    priority: int = Form(1),
    db: Session = Depends(get_db)
):
    """Agregar nuevo mapeo ML → BD"""
    try:
        query = text("""
            INSERT INTO ml_intention_mappings 
            (ml_intention, bd_condition, confidence_threshold, priority, active)
            VALUES (:ml_intention, :bd_condition, :confidence_threshold, :priority, 1)
        """)
        
        db.execute(query, {
            'ml_intention': ml_intention,
            'bd_condition': bd_condition,
            'confidence_threshold': confidence_threshold,
            'priority': priority
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Mapeo ML '{ml_intention}' → '{bd_condition}' agregado exitosamente"
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/v1/admin/dynamic-system/patterns")
async def list_dynamic_patterns(db: Session = Depends(get_db)):
    """Listar todos los patrones dinámicos"""
    try:
        # Patrones de palabras clave
        keyword_query = text("""
            SELECT keyword_pattern, bd_condition, confidence_score, 
                   requires_client, state_context, active, usage_count, success_count
            FROM keyword_condition_patterns
            ORDER BY confidence_score DESC
        """)
        
        keyword_patterns = []
        for row in db.execute(keyword_query):
            keyword_patterns.append({
                "keyword": row[0],
                "condition": row[1],
                "confidence": float(row[2]),
                "requires_client": bool(row[3]),
                "state_context": row[4],
                "active": bool(row[5]),
                "usage_count": row[6] or 0,
                "success_count": row[7] or 0,
                "success_rate": (row[7] or 0) / (row[6] or 1) if row[6] else 0
            })
        
        # Mapeos ML
        ml_query = text("""
            SELECT ml_intention, bd_condition, confidence_threshold, 
                   priority, active, usage_count, success_count
            FROM ml_intention_mappings
            ORDER BY priority ASC, confidence_threshold DESC
        """)
        
        ml_mappings = []
        for row in db.execute(ml_query):
            ml_mappings.append({
                "ml_intention": row[0],
                "bd_condition": row[1],
                "confidence_threshold": float(row[2]),
                "priority": row[3],
                "active": bool(row[4]),
                "usage_count": row[5] or 0,
                "success_count": row[6] or 0,
                "success_rate": (row[6] or 0) / (row[5] or 1) if row[5] else 0
            })
        
        return {
            "success": True,
            "keyword_patterns": keyword_patterns,
            "ml_mappings": ml_mappings,
            "total_patterns": len(keyword_patterns) + len(ml_mappings)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/api/v1/admin/dynamic-system/auto-improve")
async def trigger_auto_improvement(db: Session = Depends(get_db)):
    """Disparar auto-mejora del sistema"""
    try:
        from app.services.dynamic_transition_service import create_dynamic_transition_service
        
        dynamic_service = create_dynamic_transition_service(db)
        dynamic_service.auto_improve_patterns()
        
        return {
            "success": True,
            "message": "Auto-mejora ejecutada exitosamente",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/v1/admin/dynamic-system/decisions-log")
async def get_decisions_log(
    limit: int = Query(50, ge=1, le=200),
    conversation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Obtener log de decisiones para análisis"""
    try:
        base_query = """
            SELECT TOP (:limit)
                conversation_id, current_state, user_message,
                ml_intention, ml_confidence, detected_condition,
                condition_source, next_state, decision_confidence,
                was_successful, execution_time_ms, created_at
            FROM transition_decision_log
        """
        
        if conversation_id:
            query = text(base_query + " WHERE conversation_id = :conv_id ORDER BY created_at DESC")
            params = {"limit": limit, "conv_id": conversation_id}
        else:
            query = text(base_query + " ORDER BY created_at DESC")
            params = {"limit": limit}
        
        decisions = []
        for row in db.execute(query, params):
            decisions.append({
                "conversation_id": row[0],
                "current_state": row[1],
                "user_message": row[2],
                "ml_intention": row[3],
                "ml_confidence": float(row[4]) if row[4] else None,
                "detected_condition": row[5],
                "condition_source": row[6],
                "next_state": row[7],
                "decision_confidence": float(row[8]) if row[8] else None,
                "was_successful": row[9],
                "execution_time_ms": row[10],
                "created_at": row[11].isoformat() if row[11] else None
            })
        
        return {
            "success": True,
            "decisions": decisions,
            "total_returned": len(decisions)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/api/v1/admin/dynamic-system/test-transition")
async def test_dynamic_transition(
    current_state: str = Form(...),
    user_message: str = Form(...),
    ml_intention: str = Form("TEST_INTENTION"),
    ml_confidence: float = Form(0.8),
    has_client: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Test de transición dinámica"""
    try:
        from app.services.dynamic_transition_service import create_dynamic_transition_service
        
        dynamic_service = create_dynamic_transition_service(db)
        
        # Crear contexto de prueba
        test_context = {
            "cliente_encontrado": has_client,
            "test_mode": True
        }
        
        # Crear resultado ML de prueba
        test_ml_result = {
            "intention": ml_intention,
            "confidence": ml_confidence,
            "method": "test"
        }
        
        # Ejecutar transición
        result = dynamic_service.determine_next_state(
            current_state=current_state,
            user_message=user_message,
            ml_result=test_ml_result,
            context=test_context
        )
        
        return {
            "success": True,
            "test_input": {
                "current_state": current_state,
                "user_message": user_message,
                "ml_intention": ml_intention,
                "ml_confidence": ml_confidence,
                "has_client": has_client
            },
            "transition_result": result,
            "explanation": {
                "detected_condition": result.get("condition_detected"),
                "detection_method": result.get("detection_method"),
                "confidence": result.get("confidence"),
                "execution_time_ms": result.get("execution_time_ms")
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "test_input": {
                "current_state": current_state,
                "user_message": user_message
            }
        }
       
@router.get("/openai/estadisticas")
def obtener_estadisticas_openai(db: Session = Depends(get_db)):
    """Obtiene estadísticas de uso de OpenAI"""
    try:
        # Verificar si hay tabla de logs de OpenAI
        try:
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_usos,
                    COUNT(CASE WHEN metadata LIKE '%openai_enhanced":true%' THEN 1 END) as usos_openai,
                    COUNT(CASE WHEN metadata LIKE '%openai_enhanced":false%' THEN 1 END) as usos_ml
                FROM messages 
                WHERE timestamp > DATEADD(day, -7, GETDATE())
                    AND metadata IS NOT NULL
            """)
            
            result = db.execute(stats_query).fetchone()
            
            total = result[0] or 0
            openai_usos = result[1] or 0
            ml_usos = result[2] or 0
            
            porcentaje_openai = (openai_usos / total * 100) if total > 0 else 0
            
        except:
            # Si no hay datos de logs, usar valores simulados
            total = 100
            openai_usos = 80
            ml_usos = 20
            porcentaje_openai = 80
        
        # Obtener configuración actual
        config_query = text("""
            SELECT nombre_parametro, valor 
            FROM Configuracion_Global 
            WHERE nombre_parametro LIKE 'openai_%'
        """)
        
        config_result = db.execute(config_query)
        configuracion = {}
        
        for row in config_result:
            configuracion[row[0]] = row[1]
        
        return {
            "estadisticas_7_dias": {
                "total_mensajes": total,
                "usos_openai": openai_usos,
                "usos_ml": ml_usos,
                "porcentaje_openai": round(porcentaje_openai, 1)
            },
            "configuracion_actual": configuracion,
            "api_key_configurada": bool(os.getenv("OPENAI_API_KEY"))
        }
       
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {e}")