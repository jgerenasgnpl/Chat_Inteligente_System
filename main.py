import uvicorn
import logging
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session, sessionmaker
import httpx
import os
import traceback

# ✅ IMPORTS SEGUROS CON MANEJO DE ERRORES
try:
    from app.api.endpoints import chat
    print("✅ Chat endpoint importado")
except ImportError as e:
    print(f"❌ Error importando chat endpoint: {e}")
    chat = None

try:
    from app.api.endpoints import admin_config 
    print("✅ Admin config importado")
except ImportError as e:
    print(f"❌ Error importando admin config: {e}")
    admin_config = None

try:
    from app.core.config import settings
    print("✅ Settings importado")
except ImportError as e:
    print(f"❌ Error importando settings: {e}")
    # Configuración por defecto
    class DefaultSettings:
        PROJECT_NAME = "Sistema Chat Cobranza"
        API_V1_STR = "/api/v1"
    settings = DefaultSettings()

try:
    from app.db.session import test_connection, create_tables, SessionLocal
    print("✅ Database session importado")
except ImportError as e:
    print(f"❌ Error importando database session: {e}")
    # Crear función dummy
    def test_connection():
        return False
    def create_tables():
        pass
    SessionLocal = None

# ✅ IMPORTS OPCIONALES DEL SCHEDULER
scheduler_available = False
global_scheduler = None

try:
    from app.services.conversation_scheduler import (
        ConversationScheduler, 
        set_global_scheduler, 
        stop_global_scheduler,
        create_conversation_scheduler
    )
    print("✅ Conversation scheduler importado")
    scheduler_available = True
except ImportError as e:
    print(f"⚠️ Scheduler no disponible: {e}")
    # Crear funciones dummy
    def set_global_scheduler(scheduler):
        pass
    def stop_global_scheduler():
        pass
    def create_conversation_scheduler(session_factory):
        return None

try:
    from app.services.conversation_timeout import ConversationTimeoutManager
    print("✅ Timeout manager importado")
    timeout_manager_available = True
except ImportError as e:
    print(f"⚠️ Timeout manager no disponible: {e}")
    timeout_manager_available = False

# ✅ VERIFICAR CONEXIÓN BD SOLO SI ESTÁ DISPONIBLE
if test_connection and test_connection():
    print("✅ Conexión a base de datos exitosa")
    
    if create_tables:
        try:
            create_tables()
            print("✅ Tablas verificadas/creadas")
        except Exception as e:
            print(f"⚠️ Error con las tablas: {e}")
else:
    print("❌ No se pudo conectar a la base de datos")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ FUNCIONES DE SCHEDULER SEGURAS
def get_session():
    """Factory function para crear sesiones de BD"""
    if SessionLocal:
        return SessionLocal()
    return None

def initialize_scheduler():
    """Inicializar el scheduler global de forma segura"""
    global global_scheduler
    
    if not scheduler_available:
        print("⚠️ Scheduler no disponible - omitiendo inicialización")
        return False
    
    try:
        global_scheduler = create_conversation_scheduler(get_session)
        set_global_scheduler(global_scheduler)
        print("✅ Scheduler inicializado correctamente")
        return True
    except Exception as e:
        print(f"❌ Error inicializando scheduler: {e}")
        return False

# ✅ CREAR FASTAPI APP CON CONFIGURACIÓN SEGURA
app = FastAPI(
    title=getattr(settings, 'PROJECT_NAME', 'Sistema Chat Cobranza'),
    openapi_prefix=getattr(settings, 'API_V1_STR', '/api/v1')
)

# ✅ MANEJADORES DE ERRORES MEJORADOS
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Error no controlado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error_type": type(exc).__name__,
            "path": str(request.url),
            "traceback": traceback.format_exc() if logger.level == logging.DEBUG else None
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validación fallida: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# ✅ CORS CONFIGURACIÓN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ INCLUIR ROUTERS DE FORMA SEGURA
if chat:
    try:
        app.include_router(
            chat.router,
            prefix="/api/v1",
            tags=["chat"]
        )
        print("✅ Chat router incluido")
    except Exception as e:
        print(f"❌ Error incluyendo chat router: {e}")

if admin_config:
    try:
        app.include_router(
            admin_config.router,
            prefix=f"{getattr(settings, 'API_V1_STR', '/api/v1')}/admin",
            tags=["admin"]
        )
        print("✅ Admin router incluido")
    except Exception as e:
        print(f"❌ Error incluyendo admin router: {e}")

# ✅ ENDPOINT DE REDIRECCIÓN TEMPORAL (MEJORADO)
@app.post("/api/v1/api/v1/chat/message")
async def legacy_message_endpoint(request: Request):
    """Redirige las solicitudes de la URL incorrecta a la correcta"""
    try:
        body = await request.json()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/chat/message",
                json=body
            )
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
    except Exception as e:
        logger.error(f"Error en redirección: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Error en redirección de URL", "error": str(e)}
        )

# ✅ EVENTOS DE STARTUP/SHUTDOWN SEGUROS
@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al arrancar"""
    try:
        print("🚀 Iniciando sistema...")
        
        # ✅ INICIALIZAR SCHEDULER SOLO SI ESTÁ DISPONIBLE
        if scheduler_available:
            if initialize_scheduler() and global_scheduler:
                try:
                    global_scheduler.start_scheduler()
                    print("🚀 Sistema de auto-cierre activado")
                except Exception as e:
                    print(f"⚠️ Error iniciando scheduler: {e}")
            else:
                print("⚠️ Scheduler no se pudo inicializar")
        else:
            print("⚠️ Sistema iniciado sin auto-cierre (scheduler no disponible)")
        
        # ✅ VERIFICAR SERVICIOS CRÍTICOS
        try:
            from app.services.cache_service import cache_service
            stats = cache_service.get_cache_stats()
            print(f"✅ Cache service: {stats.get('type', 'unknown')}")
        except Exception as e:
            print(f"⚠️ Cache service no disponible: {e}")
        
        print("✅ Sistema iniciado correctamente")
        
    except Exception as e:
        logger.error(f"Error en startup: {e}")
        print(f"⚠️ Error en startup: {e}")

@app.on_event("shutdown") 
async def shutdown_event():
    """Limpiar recursos al cerrar"""
    try:
        print("🛑 Cerrando sistema...")
        
        if scheduler_available and global_scheduler:
            try:
                global_scheduler.stop_scheduler()
                print("🛑 Sistema de auto-cierre detenido")
            except Exception as e:
                print(f"⚠️ Error deteniendo scheduler: {e}")
        
        try:
            stop_global_scheduler()
        except:
            pass
        
        print("✅ Sistema cerrado correctamente")
            
    except Exception as e:
        logger.error(f"Error en shutdown: {e}")
        print(f"⚠️ Error en shutdown: {e}")

# ✅ ENDPOINTS ADMINISTRATIVOS SEGUROS
@app.post("/api/v1/admin/process-timeouts")
async def manual_timeout_process():
    """Procesar timeouts manualmente"""
    if not timeout_manager_available:
        return {
            "success": False,
            "error": "Timeout manager no disponible"
        }
    
    try:
        db = get_session()
        if not db:
            return {
                "success": False,
                "error": "Base de datos no disponible"
            }
        
        try:
            timeout_manager = ConversationTimeoutManager(db)
            stats = timeout_manager.process_all_conversations()
            return {
                "success": True, 
                "message": "Proceso de timeouts ejecutado manualmente",
                "stats": stats
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en proceso manual de timeouts: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/v1/admin/scheduler-status")
async def get_scheduler_status():
    """Obtener estado del scheduler"""
    try:
        if scheduler_available and global_scheduler:
            status = global_scheduler.get_scheduler_status()
            return {
                "scheduler_available": True,
                "status": status
            }
        else:
            return {
                "scheduler_available": False,
                "message": "Scheduler no disponible o no inicializado"
            }
    except Exception as e:
        return {
            "scheduler_available": False,
            "error": str(e)
        }

@app.post("/api/v1/admin/scheduler/{action}")
async def control_scheduler(action: str):
    """Controlar scheduler (start/stop/restart)"""
    if not scheduler_available or not global_scheduler:
        return {
            "success": False, 
            "message": "Scheduler no disponible"
        }
    
    try:
        if action == "start":
            global_scheduler.start_scheduler()
            message = "Scheduler iniciado"
        elif action == "stop":
            global_scheduler.stop_scheduler()
            message = "Scheduler detenido"
        elif action == "restart":
            global_scheduler.restart_scheduler()
            message = "Scheduler reiniciado"
        else:
            return {"success": False, "message": f"Acción no válida: {action}"}
        
        return {"success": True, "message": message}
        
    except Exception as e:
        logger.error(f"Error controlando scheduler: {e}")
        return {"success": False, "error": str(e)}

# ✅ ENDPOINTS BÁSICOS
@app.get("/test-main")
def read_test():
    return {"message": "Test desde main.py - Sistema Chat con Auto-cierre"}

@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a la API de Negociacion Chat - Versión ML Integrada",
        "version": "2.1.0-fixed",
        "features": [
            "chat_hibrido_ml",
            "auto_timeout_management", 
            "scheduler_integrado",
            "configuracion_dinamica",
            "error_handling_mejorado",
            "imports_seguros"
        ],
        "status": "operational"
    }

@app.get("/health")
def health_check():
    """Endpoint de salud del sistema mejorado"""
    try:
        # ✅ VERIFICACIONES SEGURAS
        db_status = "connected" if (test_connection and test_connection()) else "disconnected"
        
        scheduler_status = "stopped"
        if scheduler_available and global_scheduler:
            scheduler_status = "running" if global_scheduler._running else "stopped"
        elif not scheduler_available:
            scheduler_status = "not_available"
        
        # ✅ VERIFICAR SERVICIOS
        services_status = {
            "database": db_status,
            "scheduler": scheduler_status,
            "timeout_manager": "available" if timeout_manager_available else "not_available"
        }
        
        # ✅ VERIFICAR CACHE
        try:
            from app.services.cache_service import cache_service
            cache_stats = cache_service.get_cache_stats()
            services_status["cache"] = cache_stats.get("type", "unknown")
        except:
            services_status["cache"] = "not_available"
        
        # ✅ VERIFICAR ML
        try:
            from app.services.nlp_service import nlp_service
            ml_test = nlp_service.predict("test")
            services_status["ml"] = "available" if ml_test else "not_loaded"
        except:
            services_status["ml"] = "not_available"
        
        # ✅ DETERMINAR STATUS GENERAL
        critical_services = ["database"]
        critical_ok = all(services_status.get(service) == "connected" for service in critical_services)
        
        overall_status = "healthy" if critical_ok else "degraded"
        
        return {
            "status": overall_status,
            "version": "2.1.0-fixed",
            "features": [
                "chat_hibrido_ml",
                "auto_timeout_12h",
                "conversation_scheduler", 
                "configuracion_dinamica",
                "migracion_yaml_sql",
                "monitoreo_metricas",
                "error_handling_robusto"
            ],
            "services": services_status,
            "timestamp": "2025-01-25T10:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-01-25T10:00:00Z"
        }

@app.get("/api/v1/admin/test-openai")
async def test_openai_service():
    """Test específico del servicio OpenAI"""
    try:
        from app.services.openai_service import openai_cobranza_service
        
        # Test de conexión
        connection_test = openai_cobranza_service.test_connection()
        
        # Estadísticas del servicio
        stats = openai_cobranza_service.get_stats()
        
        return {
            "connection_test": connection_test,
            "service_stats": stats,
            "recommendations": [
                "Si el test falla, verificar API_KEY",
                "Si hay timeout, verificar conectividad",
                "Si hay quota error, revisar créditos en OpenAI Dashboard"
            ]
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__,
            "solution": "Seguir pasos de actualización de librería"
        }
    
# ✅ ENDPOINT DE DIAGNÓSTICO
@app.get("/api/v1/admin/diagnostics")
async def system_diagnostics():
    """Diagnóstico completo del sistema"""
    diagnostics = {
        "imports": {},
        "services": {},
        "database": {},
        "recommendations": []
    }
    
    # ✅ VERIFICAR IMPORTS
    imports_to_test = [
        ("app.services.cache_service", "Cache Service"),
        ("app.services.nlp_service", "NLP Service"),
        ("app.services.openai_service", "OpenAI Service"),
        ("app.db.session", "Database Session"),
        ("app.core.config", "Configuration")
    ]
    
    for module, name in imports_to_test:
        try:
            __import__(module)
            diagnostics["imports"][name] = "OK"
        except Exception as e:
            diagnostics["imports"][name] = f"ERROR: {str(e)}"
    
    # ✅ VERIFICAR SERVICIOS
    diagnostics["services"]["scheduler"] = scheduler_available
    diagnostics["services"]["timeout_manager"] = timeout_manager_available
    
    # ✅ GENERAR RECOMENDACIONES
    if not scheduler_available:
        diagnostics["recommendations"].append("Instalar APScheduler: pip install apscheduler==3.10.4")
    
    if diagnostics["imports"].get("Cache Service", "").startswith("ERROR"):
        diagnostics["recommendations"].append("Verificar instalación de Redis: pip install redis==5.0.1")
    
    return diagnostics

def setup_models():
    """Importar modelos de forma segura"""
    try:
        from app.models.user import User
        from app.models.conversation import Conversation
        from app.models.message import Message
        print("✅ Modelos importados correctamente")
        return User, Conversation, Message
    except Exception as e:
        print(f"⚠️ Error importando modelos: {e}")
        return None, None, None

# ✅ CONFIGURAR MODELOS AL FINAL
User, Conversation, Message = setup_models()

# ✅ FUNCIÓN PRINCIPAL CON MANEJO DE ERRORES
if __name__ == "__main__":
    try:
        print("🚀 Iniciando servidor...")
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            reload_excludes=["*.log", "backup_*", "models/*"]
        )
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error crítico iniciando servidor: {e}")
        traceback.print_exc()