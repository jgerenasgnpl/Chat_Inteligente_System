# app/db/session.py
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
# Importa tus modelos para que Base.metadata los conozca (aunque ya no creará tablas)
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

# Cadena ODBC
odbc_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=172.18.79.20,1433;"
    "DATABASE=turnosvirtuales_dev;"
    "Trusted_Connection=yes;"
)
params = urllib.parse.quote_plus(odbc_str)

# Engine
engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={params}",
    pool_pre_ping=True
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Dependencia para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()