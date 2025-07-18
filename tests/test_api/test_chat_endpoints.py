import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

class TestChatEndpoints:
    """Tests para endpoints de chat"""
    
    def test_process_message_with_cedula(self, client, sample_user, mock_db_query):
        """Test procesamiento de mensaje con cédula"""
        
        # Mock de la consulta a BD
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_session.return_value.execute.return_value = mock_db_query
            mock_session.return_value.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value.commit.return_value = None
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "mi cedula es 93388915",
                    "conversation_id": 1
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message" in data
        assert "current_state" in data
        
    def test_process_message_invalid_user(self, client):
        """Test con usuario inválido"""
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": 999,
                "message": "test",
                "conversation_id": 1
            }
        )
        
        # Debe crear el usuario automáticamente o manejar el error
        assert response.status_code in [200, 404, 500]
    
    def test_process_message_empty_content(self, client, sample_user):
        """Test con mensaje vacío"""
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": "",
                "conversation_id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_conversation_history(self, client, sample_conversation):
        """Test obtener historial de conversación"""
        response = client.get(f"/api/v1/chat/historial/{sample_conversation.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "messages" in data
        assert isinstance(data["messages"], list)
    
    def test_cedula_detection(self, client):
        """Test endpoint de detección de cédula"""
        response = client.post(
            "/api/v1/chat/test-cedula",
            json={"cedula": "93388915"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cedula" in data
        assert "cliente_encontrado" in data
    
    def test_health_check(self, client):
        """Test health check"""
        response = client.get("/api/v1/chat/test")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    @pytest.mark.parametrize("message,expected_intention", [
        ("quiero pagar", "INTENCION_PAGO"),
        ("12345678", "IDENTIFICACION"),
        ("si acepto", "CONFIRMACION"),
        ("no puedo", "RECHAZO"),
        ("opciones", "SOLICITUD_PLAN")
    ])
    def test_intention_classification(self, client, sample_user, message, expected_intention):
        """Test clasificación de intenciones"""
        with patch('app.services.nlp_service.nlp_service.predict') as mock_predict:
            mock_predict.return_value = {
                "intention": expected_intention,
                "confidence": 0.85
            }
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": message,
                    "conversation_id": 1
                }
            )
            
            assert response.status_code == 200
            # Verificar que se llamó al predictor
            mock_predict.assert_called_once_with(message)

class TestChatPerformance:
    """Tests de performance"""
    
    def test_response_time_under_500ms(self, client, sample_user, performance_tracker):
        """Test que el tiempo de respuesta sea < 500ms"""
        performance_tracker.start("chat_response")
        
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": "hola",
                "conversation_id": 1
            }
        )
        
        duration = performance_tracker.end("chat_response")
        
        assert response.status_code == 200
        assert duration < 0.5, f"Response time {duration}s exceeds 500ms limit"
    
    def test_concurrent_requests(self, client, sample_user):
        """Test manejo de requests concurrentes"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "test concurrent",
                    "conversation_id": 1
                }
            )
            results.append(response.status_code)
        
        # Crear 10 threads concurrentes
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Ejecutar todos los threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        execution_time = time.time() - start_time
        
        # Verificar resultados
        assert len(results) == 10
        assert all(status == 200 for status in results)
        assert execution_time < 5.0, f"Concurrent execution took {execution_time}s"

class TestChatErrorHandling:
    """Tests de manejo de errores"""
    
    def test_database_connection_error(self, client, sample_user):
        """Test manejo de error de conexión a BD"""
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "test error",
                    "conversation_id": 1
                }
            )
            
            # Debe manejar el error gracefully
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert "message" in data
    
    def test_ml_service_unavailable(self, client, sample_user):
        """Test cuando el servicio ML no está disponible"""
        with patch('app.services.nlp_service.nlp_service.predict') as mock_predict:
            mock_predict.side_effect = Exception("ML service unavailable")
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "test ml error",
                    "conversation_id": 1
                }
            )
            
            # Debe usar fallback
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
    
    def test_openai_service_error(self, client, sample_user):
        """Test error en servicio OpenAI"""
        with patch('app.services.openai_service.openai_cobranza_service.procesar_mensaje_cobranza') as mock_openai:
            mock_openai.side_effect = Exception("OpenAI API error")
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "test openai error",
                    "conversation_id": 1
                }
            )
            
            # Debe continuar sin OpenAI
            assert response.status_code == 200

class TestChatValidation:
    """Tests de validación de datos"""
    
    def test_invalid_json(self, client):
        """Test JSON inválido"""
        response = client.post(
            "/api/v1/chat/message",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test campos requeridos faltantes"""
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "test"}  # Falta user_id
        )
        
        assert response.status_code == 422
    
    def test_invalid_user_id_type(self, client):
        """Test tipo de user_id inválido"""
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": "invalid",
                "message": "test",
                "conversation_id": 1
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.parametrize("message_length", [0, 1, 1000, 5000])
    def test_message_length_limits(self, client, sample_user, message_length):
        """Test límites de longitud de mensaje"""
        message = "a" * message_length
        
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": message,
                "conversation_id": 1
            }
        )
        
        if message_length <= 2000:  # Límite razonable
            assert response.status_code == 200
        else:
            assert response.status_code in [200, 422]  # Puede rechazar o truncar

# ========================================
# FIXTURES ESPECÍFICAS PARA ESTOS TESTS
# ========================================

@pytest.fixture
def sample_messages():
    """Mensajes de prueba para diferentes escenarios"""
    return {
        "cedula": ["93388915", "mi cedula es 12345678", "documento: 1020428633"],
        "pago": ["quiero pagar", "necesito cancelar", "como pago mi deuda"],
        "opciones": ["que opciones tengo", "planes de pago", "facilidades"],
        "confirmacion": ["si acepto", "está bien", "de acuerdo"],
        "rechazo": ["no puedo", "imposible", "no me interesa"],
        "saludo": ["hola", "buenos dias", "buenas tardes"],
        "complex": [
            "hola, mi cedula es 93388915 y quiero pagar mi deuda",
            "buenos dias, necesito opciones de pago para mi cuenta",
            "tengo dificultades para pagar, que facilidades me ofrecen"
        ]
    }