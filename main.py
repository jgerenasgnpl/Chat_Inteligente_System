import uvicorn
import logging
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import httpx

from app.api.endpoints import chat
# from app.api.endpoints import admin_config  # Descomentar cuando esté listo
from app.core.config import settings

# ✅ IMPORTACIONES SEGURAS DE DB
from app.db.session import test_connection, create_tables

# ✅ PROBAR CONEXIÓN ANTES DE INICIALIZAR FASTAPI
print("🔍 Verificando conexión a base de datos...")
if not test_connection():
    print("❌ No se pudo conectar a la base de datos. Verificar configuración.")
    exit(1)

# ✅ CREAR TABLAS DE FORMA SEGURA
print("📋 Verificando/creando tablas...")
try:
    create_tables()
except Exception as e:
    print(f"❌ Error con las tablas: {e}")
    print("⚠️ Continuando sin crear tablas (pueden existir)")

# Uvicorn captura errores
logger = logging.getLogger("uvicorn.error")

# FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_prefix=settings.API_V1_STR
)

# errores no controlados
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Error no controlado: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )

@app.get("/test-main")
def read_test():
    return {"message": "Test desde main.py"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validación fallida: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RUTAS PRINCIPALES
app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["chat"]
)

# RUTAS DE ADMINISTRACIÓN (descomentar cuando estén listas)
# app.include_router(
#     admin_config.router,
#     prefix=f"{settings.API_V1_STR}/admin",
#     tags=["admin"]
# )

@app.post("/api/v1/api/v1/chat/message")
async def legacy_message_endpoint(request: Request):
    """
    Redirige las solicitudes de la URL incorrecta a la correcta.
    Temporal hasta que se actualice el frontend.
    """
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/v1/chat/message",
            json=body
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    
@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Negociacion Chat - Versión ML Integrada"}

@app.get("/health")
def health_check():
    """Endpoint de salud del sistema"""
    return {
        "status": "healthy",
        "version": "2.0.0-ml",
        "features": [
            "chat_hibrido_ml",
            "configuracion_dinamica", 
            "migracion_yaml_sql",
            "monitoreo_metricas"
        ],
        "database": "connected" if test_connection() else "error"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)