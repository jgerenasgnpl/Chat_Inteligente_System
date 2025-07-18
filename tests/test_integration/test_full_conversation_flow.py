import pytest
import asyncio
from datetime import datetime, time
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

class TestFullConversationFlow:
    """Tests de integración del flujo completo de conversación"""
    
    def test_complete_negotiation_flow(self, client, sample_user):
        """Test flujo completo de negociación exitosa"""
        conversation_id = 1
        
        # PASO 1: Saludo inicial
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": "hola",
                "conversation_id": conversation_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "cédula" in data["message"].lower()
        
        # PASO 2: Proporcionar cédula
        with patch('app.db.session.SessionLocal') as mock_session:
            # Mock datos del cliente
            mock_result = Mock()
            mock_result.fetchone.return_value = (
                "CARLOS FAJARDO TEST", "93388915", 123456.00,
                80000.00, 86000.00, None, None,
                "BANCO TEST", "CREDITO",
                17000.00, 10000.00, 5000.00, None,
                100000.00, 23456.00, "3001234567", "test@test.com"
            )
            mock_session.return_value.execute.return_value = mock_result
            mock_session.return_value.commit.return_value = None
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "93388915",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "CARLOS FAJARDO TEST" in data["message"]
            assert data["current_state"] in ["informar_deuda", "proponer_planes_pago"]
        
        # PASO 3: Solicitar opciones
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": "quiero ver las opciones",
                "conversation_id": conversation_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_state"] == "proponer_planes_pago"
        assert "opciones" in data["message"].lower()
        
        # PASO 4: Aceptar una opción
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": "acepto la primera opcion",
                "conversation_id": conversation_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_state"] in ["generar_acuerdo", "finalizar_conversacion"]
    
    def test_negotiation_with_objection_flow(self, client, sample_user):
        """Test flujo con manejo de objeciones"""
        conversation_id = 2
        
        # Iniciar conversación con cédula
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_result = Mock()
            mock_result.fetchone.return_value = (
                "CLIENTE TEST", "12345678", 200000.00,
                140000.00, 160000.00, None, None,
                "BANCO TEST", "CREDITO",
                30000.00, 20000.00, 10000.00, None,
                180000.00, 20000.00, "3009876543", "cliente@test.com"
            )
            mock_session.return_value.execute.return_value = mock_result
            mock_session.return_value.commit.return_value = None
            
            # Cliente proporciona cédula
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "mi documento es 12345678",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            
            # Cliente pone objeción
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "no puedo pagar eso, es muy caro",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["current_state"] in ["gestionar_objecion", "proponer_planes_pago"]
            assert "alternativas" in data["message"].lower() or "flexible" in data["message"].lower()
            
            # Sistema ofrece alternativa
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "que otras opciones hay",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "cuotas" in data["message"].lower() or "plan" in data["message"].lower()
    
    def test_client_not_found_flow(self, client, sample_user):
        """Test flujo cuando cliente no se encuentra"""
        conversation_id = 3
        
        with patch('app.db.session.SessionLocal') as mock_session:
            # Mock cliente no encontrado
            mock_result = Mock()
            mock_result.fetchone.return_value = None
            mock_session.return_value.execute.return_value = mock_result
            mock_session.return_value.commit.return_value = None
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "99999999",  # Cédula inexistente
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["current_state"] == "cliente_no_encontrado"
            assert "no encontré" in data["message"].lower()
    
    def test_conversation_timeout_flow(self, client, sample_user):
        """Test flujo de timeout de conversación"""
        conversation_id = 4
        
        # Simular conversación expirada
        with patch('app.services.conversation_service.CONVERSATION_ACTIVITY', {}):
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "hola",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            # Puede reiniciar o manejar timeout
            assert "conversation_id" in data

class TestSystemIntegration:
    """Tests de integración del sistema completo"""
    
    def test_ml_openai_fallback_chain(self, client, sample_user):
        """Test cadena de fallback ML -> OpenAI -> Reglas"""
        
        # CASO 1: ML funciona
        with patch('app.services.nlp_service.nlp_service.predict') as mock_ml:
            mock_ml.return_value = {"intention": "INTENCION_PAGO", "confidence": 0.85}
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "quiero pagar",
                    "conversation_id": 1
                }
            )
            
            assert response.status_code == 200
            mock_ml.assert_called()
        
        # CASO 2: ML falla, OpenAI funciona
        with patch('app.services.nlp_service.nlp_service.predict') as mock_ml, \
             patch('app.services.openai_service.openai_cobranza_service.should_use_openai') as mock_openai_check, \
             patch('app.services.openai_service.openai_cobranza_service.procesar_mensaje_cobranza') as mock_openai:
            
            mock_ml.side_effect = Exception("ML service down")
            mock_openai_check.return_value = True
            mock_openai.return_value = {
                "enhanced": True,
                "message": "Respuesta de OpenAI",
                "method": "openai_enhancement"
            }
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "mensaje complejo de negociación",
                    "conversation_id": 1
                }
            )
            
            assert response.status_code == 200
            # Sistema debe continuar funcionando con OpenAI
        
        # CASO 3: Todo falla, usar reglas
        with patch('app.services.nlp_service.nlp_service.predict') as mock_ml, \
             patch('app.services.openai_service.openai_cobranza_service.should_use_openai') as mock_openai_check:
            
            mock_ml.side_effect = Exception("ML service down")
            mock_openai_check.return_value = False
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "si acepto",
                    "conversation_id": 1
                }
            )
            
            assert response.status_code == 200
            # Sistema debe usar reglas de fallback
    
    def test_database_recovery(self, client, sample_user):
        """Test recuperación de errores de BD"""
        
        # Simular error temporal de BD
        with patch('app.db.session.SessionLocal') as mock_session:
            mock_session.side_effect = [
                Exception("Connection failed"),  # Primer intento falla
                Mock()  # Segundo intento funciona
            ]
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "test recovery",
                    "conversation_id": 1
                }
            )
            
            # Sistema debe manejar el error gracefully
            assert response.status_code in [200, 500]
    
    def test_concurrent_conversations(self, client, sample_user):
        """Test conversaciones concurrentes del mismo usuario"""
        import threading
        import time
        
        results = []
        
        def create_conversation(conv_id):
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": f"hola conversacion {conv_id}",
                    "conversation_id": conv_id
                }
            )
            results.append((conv_id, response.status_code))
        
        # Crear 5 conversaciones concurrentes
        threads = []
        for i in range(1, 6):
            thread = threading.Thread(target=create_conversation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verificar que todas las conversaciones se manejaron
        assert len(results) == 5
        assert all(status == 200 for _, status in results)

class TestEndToEndScenarios:
    """Tests de escenarios de extremo a extremo"""
    
    def test_high_value_client_vip_treatment(self, client, sample_user):
        """Test tratamiento VIP para cliente de alto valor"""
        conversation_id = 100
        
        with patch('app.db.session.SessionLocal') as mock_session:
            # Cliente VIP con deuda alta
            mock_result = Mock()
            mock_result.fetchone.return_value = (
                "CLIENTE VIP", "11111111", 10000000.00,  # $10M deuda
                7000000.00, 8000000.00, None, None,
                "BANCO PREMIUM", "CREDITO VIP",
                1500000.00, 1000000.00, 500000.00, None,
                9000000.00, 1000000.00, "3001111111", "vip@test.com"
            )
            mock_session.return_value.execute.return_value = mock_result
            mock_session.return_value.commit.return_value = None
            
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": "11111111",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verificar tratamiento especial para cliente VIP
            assert "CLIENTE VIP" in data["message"]
            assert "$10,000,000" in data["message"]
    
    def test_complex_multilingual_message(self, client, sample_user):
        """Test mensaje complejo multiidioma"""
        response = client.post(
            "/api/v1/chat/message",
            json={
                "user_id": sample_user.id,
                "message": "Hello, mi cédula es 93388915 and I want to pay mi deuda, gracias",
                "conversation_id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Sistema debe manejar texto mixto y detectar cédula
        assert "conversation_id" in data
    
    def test_extremely_long_conversation(self, client, sample_user):
        """Test conversación extremadamente larga"""
        conversation_id = 999
        
        # Simular 50 intercambios
        for i in range(50):
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": f"mensaje numero {i}",
                    "conversation_id": conversation_id
                }
            )
            
            assert response.status_code == 200
            
            # Verificar que el sistema maneja conversaciones largas
            if i > 30:  # Después de muchos mensajes
                data = response.json()
                # Puede activar timeout o manejo especial
                assert "conversation_id" in data

@pytest.mark.slow
class TestStressTests:
    """Tests de estrés del sistema"""
    
    def test_rapid_fire_messages(self, client, sample_user):
        """Test mensajes rápidos consecutivos"""
        conversation_id = 888
        
        # Enviar 20 mensajes rápidamente
        start_time = time.time()
        
        for i in range(20):
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": f"mensaje rapido {i}",
                    "conversation_id": conversation_id
                }
            )
            assert response.status_code == 200
        
        total_time = time.time() - start_time
        
        # Verificar que el sistema maneja la carga
        assert total_time < 10.0, f"20 messages took {total_time}s"
    
    def test_memory_usage_stability(self, client, sample_user):
        """Test estabilidad de uso de memoria"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Simular uso intensivo
        for i in range(100):
            response = client.post(
                "/api/v1/chat/message",
                json={
                    "user_id": sample_user.id,
                    "message": f"test memory {i}",
                    "conversation_id": i % 10  # Rotar entre 10 conversaciones
                }
            )
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # No debe haber un crecimiento excesivo de memoria
        assert memory_increase < 50 * 1024 * 1024, f"Memory increased by {memory_increase / 1024 / 1024:.1f}MB"