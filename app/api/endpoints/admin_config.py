from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any
import json

from app.api.deps import get_db, get_current_active_admin
from app.schemas.chat import ConfiguracionEstado, ConfiguracionIntencion

router = APIRouter(
    prefix="/admin",
    tags=["administracion"]
)

# ======================
# GESTIÓN DE ESTADOS
# ======================

@router.get("/estados")
def listar_estados(db: Session = Depends(get_db)):
    """Lista todos los estados configurados"""
    try:
        query = text("""
            SELECT nombre, mensaje_template, accion, condicion, 
                   estado_siguiente_true, estado_siguiente_false, 
                   estado_siguiente_default, activo
            FROM Estados_Conversacion 
            ORDER BY nombre
        """)
        
        estados = []
        for row in db.execute(query):
            estados.append({
                "nombre": row[0],
                "mensaje_template": row[1],
                "accion": row[2],
                "condicion": row[3],
                "estado_siguiente_true": row[4],
                "estado_siguiente_false": row[5],
                "estado_siguiente_default": row[6],
                "activo": bool(row[7])
            })
        
        return {"estados": estados}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estados: {e}"
        )

@router.post("/estados")
def crear_estado(
    estado: ConfiguracionEstado,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Crea un nuevo estado"""
    try:
        query = text("""
            INSERT INTO Estados_Conversacion 
            (nombre, mensaje_template, accion, condicion, 
             estado_siguiente_true, estado_siguiente_false, 
             estado_siguiente_default, activo)
            VALUES (:nombre, :mensaje, :accion, :condicion,
                    :true_next, :false_next, :default_next, 1)
        """)
        
        db.execute(query, {
            "nombre": estado.nombre,
            "mensaje": estado.mensaje_template,
            "accion": estado.accion,
            "condicion": estado.condicion,
            "true_next": estado.estado_siguiente_true,
            "false_next": estado.estado_siguiente_false,
            "default_next": estado.estado_siguiente_default
        })
        
        db.commit()
        return {"message": f"Estado '{estado.nombre}' creado exitosamente"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creando estado: {e}"
        )

@router.put("/estados/{nombre_estado}")
def actualizar_estado(
    nombre_estado: str,
    estado: ConfiguracionEstado,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Actualiza un estado existente"""
    try:
        query = text("""
            UPDATE Estados_Conversacion 
            SET mensaje_template = :mensaje,
                accion = :accion,
                condicion = :condicion,
                estado_siguiente_true = :true_next,
                estado_siguiente_false = :false_next,
                estado_siguiente_default = :default_next
            WHERE nombre = :nombre
        """)
        
        result = db.execute(query, {
            "nombre": nombre_estado,
            "mensaje": estado.mensaje_template,
            "accion": estado.accion,
            "condicion": estado.condicion,
            "true_next": estado.estado_siguiente_true,
            "false_next": estado.estado_siguiente_false,
            "default_next": estado.estado_siguiente_default
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Estado no encontrado")
        
        db.commit()
        return {"message": f"Estado '{nombre_estado}' actualizado exitosamente"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando estado: {e}"
        )

# ======================
# GESTIÓN DE INTENCIONES ML
# ======================

@router.get("/intenciones")
def listar_intenciones(db: Session = Depends(get_db)):
    """Lista todas las intenciones ML configuradas"""
    try:
        query = text("""
            SELECT i.id, i.nombre, i.descripcion, i.estado_siguiente,
                   COUNT(p.id) as cantidad_patrones
            FROM Intenciones i
            LEFT JOIN Patrones_Intencion p ON i.id = p.intencion_id
            GROUP BY i.id, i.nombre, i.descripcion, i.estado_siguiente
            ORDER BY i.nombre
        """)
        
        intenciones = []
        for row in db.execute(query):
            intenciones.append({
                "id": row[0],
                "nombre": row[1],
                "descripcion": row[2],
                "estado_siguiente": row[3],
                "cantidad_patrones": row[4]
            })
        
        return {"intenciones": intenciones}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo intenciones: {e}"
        )

@router.post("/intenciones/{intencion_id}/patrones")
def agregar_patron_intencion(
    intencion_id: int,
    patron: str,
    tipo: str = "contiene",
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Agrega un patrón a una intención"""
    try:
        query = text("""
            INSERT INTO Patrones_Intencion (intencion_id, patron, tipo)
            VALUES (:intencion_id, :patron, :tipo)
        """)
        
        db.execute(query, {
            "intencion_id": intencion_id,
            "patron": patron,
            "tipo": tipo
        })
        
        db.commit()
        return {"message": f"Patrón '{patron}' agregado a intención {intencion_id}"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error agregando patrón: {e}"
        )

# ======================
# MÉTRICAS Y MONITOREO
# ======================

@router.get("/metricas/tiempo-real")
def obtener_metricas_tiempo_real(db: Session = Depends(get_db)):
    """Obtiene métricas en tiempo real del sistema"""
    from app.monitoring.monitoring_system import MonitoringSystem
    
    monitor = MonitoringSystem(db)
    return monitor.obtener_metricas_tiempo_real()

@router.get("/metricas/ml/accuracy")
def obtener_accuracy_ml(
    dias: int = 7,
    db: Session = Depends(get_db)
):
    """Obtiene la accuracy del modelo ML"""
    from app.monitoring.monitoring_system import MLMetrics
    
    ml_metrics = MLMetrics(db)
    accuracy = ml_metrics.obtener_accuracy_ml(dias)
    
    return {
        "accuracy": accuracy,
        "periodo_dias": dias,
        "timestamp": "2025-01-25T10:00:00"
    }

@router.get("/anomalias")
def detectar_anomalias(db: Session = Depends(get_db)):
    """Detecta anomalías en el sistema"""
    from app.monitoring.monitoring_system import MonitoringSystem
    
    monitor = MonitoringSystem(db)
    anomalias = monitor.detectar_anomalias()
    
    return {"anomalias": anomalias}

# ======================
# CONFIGURACIÓN GLOBAL
# ======================

@router.get("/configuracion")
def obtener_configuracion_global(db: Session = Depends(get_db)):
    """Obtiene la configuración global del sistema"""
    try:
        query = text("""
            SELECT nombre_parametro, valor, descripcion
            FROM Configuracion_Global
            WHERE activo = 1
        """)
        
        config = {}
        for row in db.execute(query):
            config[row[0]] = {
                "valor": row[1],
                "descripcion": row[2]
            }
        
        return {"configuracion": config}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración: {e}"
        )

@router.put("/configuracion/{parametro}")
def actualizar_configuracion(
    parametro: str,
    valor: str,
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Actualiza un parámetro de configuración"""
    try:
        query = text("""
            UPDATE Configuracion_Global 
            SET valor = :valor, fecha_actualizacion = GETDATE()
            WHERE nombre_parametro = :parametro
        """)
        
        result = db.execute(query, {
            "parametro": parametro,
            "valor": valor
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Parámetro no encontrado")
        
        db.commit()
        return {"message": f"Parámetro '{parametro}' actualizado a '{valor}'"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando configuración: {e}"
        )

# ======================
# REENTRENAMIENTO ML
# ======================

@router.post("/ml/reentrenar")
def forzar_reentrenamiento_ml(
    db: Session = Depends(get_db),
    admin: str = Depends(get_current_active_admin)
):
    """Fuerza un reentrenamiento del modelo ML"""
    try:
        from app.machine_learning.ml import MLIntentionClassifier
        
        ml_classifier = MLIntentionClassifier(db)
        resultado = ml_classifier.entrenar_modelo()
        
        return {
            "message": "Reentrenamiento completado",
            "accuracy": resultado["accuracy"],
            "ejemplos_entrenamiento": resultado["ejemplos_entrenamiento"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en reentrenamiento: {e}"
        )