from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Crear la URI de conexión para SQL Server
DATABASE_URI = (
    f"mssql+pyodbc://{settings.SQLSERVER_USER}:{settings.SQLSERVER_PASSWORD}"
    f"@{settings.SQLSERVER_SERVER}:{settings.SQLSERVER_PORT}/{settings.SQLSERVER_DB}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)

# Crear el motor de SQLAlchemy
engine = create_engine(settings.DATABASE_URI, pool_pre_ping=True)

# Crear la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Función para obtener una sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()