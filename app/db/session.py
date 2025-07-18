import urllib.parse
from sqlalchemy import create_engine, text 
from sqlalchemy.orm import sessionmaker
from app.db.base import Base


odbc_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=172.18.79.20,1433;"
    "DATABASE=turnosvirtuales_dev;"
    "Trusted_Connection=yes;"
)
params = urllib.parse.quote_plus(odbc_str)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={params}",
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

def get_db():
    """Generador de sesiones de BD"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Prueba la conexión a BD"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Conexión exitosa - Test result: {row[0]}")
            return True
    except Exception as e:
        print(f"❌ Error conexión: {e}")
        return False

def create_tables():
    """Crea las tablas en la BD"""
    try:
        from app.models.user import User
        from app.models.conversation import Conversation  
        from app.models.message import Message
        
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas/verificadas")
        return True
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        raise

def verify_tables():
    """Verifica que las tablas existan"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME IN ('users', 'conversations', 'messages')
            """))
            count = result.fetchone()[0]
            print(f"📊 Tablas del sistema encontradas: {count}/3")
            return count > 0
    except Exception as e:
        print(f"⚠️ Error verificando tablas: {e}")
        return False
