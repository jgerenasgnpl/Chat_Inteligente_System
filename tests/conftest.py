import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, MagicMock
import tempfile
import os

from main import app
from app.db.session import get_db
from app.db.base import Base
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

# ========================================
# DATABASE TEST SETUP
# ========================================

@pytest.fixture(scope="session")
def test_engine():
    """Crear engine de prueba en memoria"""
    # Usar SQLite para tests (más rápido que SQL Server)
    engine = create_engine(
        "sqlite:///./test.db", 
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(scope="function")
def test_session(test_engine):
    """Crear sesión de test que se rollback después de cada test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()

@pytest.fixture(scope="function")
def client(test_session):
    """Cliente de test con BD mockeada"""
    def override_get_db():
        try:
            yield test_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# ========================================
# DATA FIXTURES
# ========================================

@pytest.fixture
def sample_user(test_session):
    """Usuario de prueba"""
    user = User(
        id=1,
        email="test@systemgroup.com",
        hashed_password="hashed_password",
        full_name="Usuario Test",
        is_active=True
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user

@pytest.fixture
def sample_conversation(test_session, sample_user):
    """Conversación de prueba"""
    conversation = Conversation(
        id=1,
        user_id=sample_user.id,
        current_state="inicial",
        context_data='{"test": true}',
        is_active=True
    )
    test_session.add(conversation)
    test_session.commit()
    test_session.refresh(conversation)
    return conversation

@pytest.fixture
def sample_client_data():
    """Datos de cliente para tests"""
    return {
        "cedula_detectada": "93388915",
        "Nombre_del_cliente": "CARLOS FAJARDO TEST",
        "saldo_total": 123456,
        "banco": "BANCO TEST",
        "oferta_1": 80000,
        "oferta_2": 86000,
        "hasta_3_cuotas": 17000,
        "hasta_6_cuotas": 10000,
        "hasta_12_cuotas": 5000,
        "cliente_encontrado": True
    }

# ========================================
# SERVICE MOCKS
# ========================================

@pytest.fixture
def mock_nlp_service():
    """Mock del servicio NLP"""
    mock = Mock()
    mock.predict.return_value = {
        "intention": "INTENCION_PAGO",
        "confidence": 0.85,
        "method": "ml_prediction"
    }
    return mock

@pytest.fixture
def mock_openai_service():
    """Mock del servicio OpenAI"""
    mock = Mock()
    mock.disponible = True
    mock.should_use_openai.return_value = True
    mock.procesar_mensaje_cobranza.return_value = {
        "enhanced": True,
        "message": "Respuesta generada por OpenAI de prueba",
        "method": "openai_enhancement"
    }
    return mock

@pytest.fixture
def mock_db_query():
    """Mock para consultas de BD"""
    mock = Mock()
    mock.fetchone.return_value = (
        "CARLOS FAJARDO TEST",  # Nombre_del_cliente
        "93388915",             # Cedula
        123456.00,              # Saldo_total
        80000.00,               # Oferta_1
        86000.00,               # Oferta_2
        None,                   # Oferta_3
        None,                   # Oferta_4
        "BANCO TEST",           # banco
        "CREDITO",              # Producto
        17000.00,               # Hasta_3_cuotas
        10000.00,               # Hasta_6_cuotas
        5000.00,                # Hasta_12_cuotas
        None,                   # Hasta_18_cuotas
        100000.00,              # Capital
        23456.00,               # Intereses
        "3001234567",           # Telefono
        "test@email.com"        # Email
    )
    return mock

# ========================================
# ASYNC HELPERS
# ========================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ========================================
# PERFORMANCE FIXTURES
# ========================================

@pytest.fixture
def performance_tracker():
    """Tracker para medir performance de tests"""
    import time
    
    class PerformanceTracker:
        def __init__(self):
            self.times = {}
        
        def start(self, operation):
            self.times[operation] = time.time()
        
        def end(self, operation):
            if operation in self.times:
                duration = time.time() - self.times[operation]
                print(f"⏱️ {operation}: {duration:.3f}s")
                return duration
            return None
    
    return PerformanceTracker()

# ========================================
# ENVIRONMENT SETUP
# ========================================

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup automático del entorno de test"""
    # Variables de entorno para tests
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ML_CONFIDENCE_THRESHOLD", "0.5")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    
    # Disable external services
    monkeypatch.setenv("DISABLE_SCHEDULER", "true")
    monkeypatch.setenv("DISABLE_EXTERNAL_APIS", "true")