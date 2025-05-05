import os
from typing import Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "NegotiationChat"
    API_V1_STR: str = "/api/v1"
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 
    
    # Database
    SQLSERVER_SERVER: str = os.getenv("SQLSERVER_SERVER", "localhost")
    SQLSERVER_USER: str = os.getenv("SQLSERVER_USER", "sa")
    SQLSERVER_PASSWORD: str = os.getenv("SQLSERVER_PASSWORD", "password")
    SQLSERVER_DB: str = os.getenv("SQLSERVER_DB", "negotiation_chat")
    SQLSERVER_PORT: str = os.getenv("SQLSERVER_PORT", "1433")
    DATABASE_URI: Optional[str] = None

    @validator("DATABASE_URI", pre=True, always=True)
    def assemble_db_connection(cls, v, values):
        if v:
            return v
        user = values.get("SQLSERVER_USER")
        pwd  = values.get("SQLSERVER_PASSWORD")
        srv  = values.get("SQLSERVER_SERVER")
        port = values.get("SQLSERVER_PORT")
        db   = values.get("SQLSERVER_DB")
        return (
            f"mssql+pyodbc://{user}:{pwd}@{srv}:{port}/{db}"
            "?driver=ODBC+Driver+17+for+SQL+Server"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()