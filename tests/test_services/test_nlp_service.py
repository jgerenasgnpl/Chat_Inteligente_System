import pytest
from unittest.mock import Mock, patch
from app.services.nlp_service import ImprovedNLPService, nlp_service

class TestNLPService:
    """Tests para el servicio NLP"""
    
    def test_cedula_detection(self):
        """Test detección de cédulas"""
        test_cases = [
            ("12345678", "IDENTIFICACION"),
            ("mi cedula es 93388915", "IDENTIFICACION"),
            ("documento: 1020428633", "IDENTIFICACION"),
            ("cc 87654321", "IDENTIFICACION"),
            ("hola", None)  # No debe detectar cédula
        ]
        
        for message, expected in test_cases:
            result = nlp_service.predict(message)
            if expected:
                assert result['intention'] == expected
                assert result['confidence'] > 0.8
            else:
                assert result['intention'] != "IDENTIFICACION"
    
    def test_intention_classification_accuracy(self):
        """Test precisión de clasificación de intenciones"""
        test_cases = [
            ("quiero pagar mi deuda", "INTENCION_PAGO"),
            ("necesito opciones de pago", "SOLICITUD_PLAN"),
            ("si acepto la oferta", "CONFIRMACION"),
            ("no puedo pagar ahora", "RECHAZO"),
            ("cuanto debo", "CONSULTA_DEUDA"),
            ("hola buenos dias", "SALUDO"),
            ("gracias hasta luego", "DESPEDIDA")
        ]
        
        correct_predictions = 0
        total_predictions = len(test_cases)
        
        for message, expected_intention in test_cases:
            result = nlp_service.predict(message)
            if result['intention'] == expected_intention and result['confidence'] >= 0.6:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions
        assert accuracy >= 0.8, f"Accuracy {accuracy:.2f} is below 80% threshold"
    
    def test_confidence_thresholds(self):
        """Test umbrales de confianza"""
        # Mensaje claro - alta confianza
        result = nlp_service.predict("quiero pagar")
        assert result['confidence'] >= 0.7
        
        # Mensaje ambiguo - baja confianza
        result = nlp_service.predict("a")
        assert result['confidence'] < 0.7
    
    def test_regex_validation(self):
        """Test validación con regex"""
        service = ImprovedNLPService()
        
        # Test cédula
        result = service._validate_with_regex("93388915")
        assert result['intention'] == "IDENTIFICACION"
        assert result['confidence'] >= 0.9
        
        # Test confirmación
        result = service._validate_with_regex("si acepto")
        assert result['intention'] == "CONFIRMACION"
        assert result['confidence'] >= 0.8
    
    def test_fallback_classification(self):
        """Test clasificación de fallback"""
        service = ImprovedNLPService()
        
        # Simular fallo del ML
        with patch.object(service, 'model', None):
            result = service.predict("quiero pagar")
            assert result['intention'] in ["INTENCION_PAGO", "DESCONOCIDA"]
    
    def test_text_cleaning(self):
        """Test limpieza de texto"""
        service = ImprovedNLPService()
        
        dirty_text = "¡¡¡HOLA!!! mi cédula es: 93,388,915..."
        clean_text = service._clean_text_for_ml(dirty_text)
        
        assert "hola" in clean_text.lower()
        assert "NUMERO_DOCUMENTO" in clean_text  # Cédula debe ser normalizada
        assert "!" not in clean_text
    
    def test_confidence_adjustment(self):
        """Test ajuste de confianza"""
        service = ImprovedNLPService()
        
        # Test texto con cédula - debe aumentar confianza para IDENTIFICACION
        adjusted = service._adjust_confidence("93388915", "IDENTIFICACION", 0.7)
        assert adjusted > 0.7
        
        # Test texto sin cédula para IDENTIFICACION - debe reducir confianza
        adjusted = service._adjust_confidence("hola", "IDENTIFICACION", 0.7)
        assert adjusted < 0.7

class TestNLPPerformance:
    """Tests de performance del NLP"""
    
    def test_prediction_speed(self, performance_tracker):
        """Test velocidad de predicción"""
        performance_tracker.start("nlp_prediction")
        
        result = nlp_service.predict("quiero pagar mi deuda")
        
        duration = performance_tracker.end("nlp_prediction")
        
        assert result is not None
        assert duration < 0.1, f"NLP prediction took {duration}s, should be < 100ms"
    
    def test_batch_predictions(self, performance_tracker):
        """Test predicciones en lote"""
        messages = [
            "quiero pagar",
            "opciones de pago", 
            "si acepto",
            "no puedo",
            "93388915"
        ] * 10  # 50 mensajes total
        
        performance_tracker.start("batch_predictions")
        
        results = []
        for message in messages:
            result = nlp_service.predict(message)
            results.append(result)
        
        duration = performance_tracker.end("batch_predictions")
        
        assert len(results) == 50
        assert all('intention' in r for r in results)
        assert duration < 5.0, f"Batch predictions took {duration}s"

class TestNLPEdgeCases:
    """Tests de casos extremos"""
    
    @pytest.mark.parametrize("empty_input", ["", None, "   ", "\n\t"])
    def test_empty_inputs(self, empty_input):
        """Test inputs vacíos"""
        result = nlp_service.predict(empty_input)
        assert result['intention'] == "DESCONOCIDA"
        assert result['confidence'] == 0.0
    
    def test_very_long_text(self):
        """Test texto muy largo"""
        long_text = "palabra " * 1000  # 1000 palabras
        result = nlp_service.predict(long_text)
        
        assert 'intention' in result
        assert 'confidence' in result
    
    def test_special_characters(self):
        """Test caracteres especiales"""
        special_text = "¿Cómo puedo pagar? ñáéíóú @#$%"
        result = nlp_service.predict(special_text)
        
        assert 'intention' in result
        assert result['intention'] in ["INTENCION_PAGO", "CONSULTA_DEUDA", "DESCONOCIDA"]
    
    def test_numbers_and_mixed_content(self):
        """Test números y contenido mixto"""
        mixed_text = "mi cedula 93388915 y quiero pagar $50000"
        result = nlp_service.predict(mixed_text)
        
        # Debe detectar tanto cédula como intención de pago
        assert result['intention'] in ["IDENTIFICACION", "INTENCION_PAGO"]
        assert result['confidence'] > 0.6

# tests/test_services/test_conversation_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.conversation_service import ConversationService

class TestConversationService:
    """Tests para el servicio de conversación"""
    
    @pytest.fixture
    def conversation_service(self, test_session):
        """Instancia del servicio de conversación"""
        return ConversationService(test_session)
    
    @pytest.mark.asyncio
    async def test_process_message_with_cedula(self, conversation_service, sample_client_data):
        """Test procesamiento de mensaje con cédula"""
        with patch.object(conversation_service, '_query_client_simple') as mock_query:
            mock_query.return_value = sample_client_data
            
            result = await conversation_service.process_message(1, "93388915", 1)
            
            assert result['session_valid'] == True
            assert 'response' in result
            assert 'context' in result
            mock_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_without_client_data(self, conversation_service):
        """Test procesamiento sin datos de cliente"""
        with patch.object(conversation_service, '_query_client_simple') as mock_query:
            mock_query.return_value = {"encontrado": False}
            
            result = await conversation_service.process_message(1, "12345678", 1)
            
            assert 'response' in result
            # Debe manejar el caso de cliente no encontrado
    
    def test_cedula_extraction(self, conversation_service):
        """Test extracción de cédulas"""
        test_cases = [
            ("93388915", "93388915"),
            ("mi cedula es 12345678", "12345678"),
            ("documento: 1020428633", "1020428633"),
            ("hola como estas", None)
        ]
        
        for message, expected in test_cases:
            result = conversation_service._extract_cedula_simple(message)
            assert result == expected
    
    def test_conversation_timeout_check(self, conversation_service):
        """Test verificación de timeout"""
        # Simular conversación expirada
        expired = conversation_service._is_conversation_expired(999)
        assert expired == True  # Conversación no existente debe estar expirada
    
    def test_context_validation(self, conversation_service, sample_conversation):
        """Test validación de contexto"""
        context = conversation_service._get_validated_context(sample_conversation, "test")
        assert isinstance(context, dict)

# tests/test_services/test_variable_service.py
import pytest
from unittest.mock import patch, Mock
from app.services.variable_service import VariableService

class TestVariableService:
    """Tests para el servicio de variables"""
    
    @pytest.fixture
    def variable_service(self, test_session):
        return VariableService(test_session)
    
    def test_resolve_client_variables(self, variable_service, sample_client_data):
        """Test resolución de variables de cliente"""
        template = "Hola {{Nombre_del_cliente}}, tu saldo es {{saldo_total}}"
        
        result = variable_service.resolver_variables(template, sample_client_data)
        
        assert "CARLOS FAJARDO TEST" in result
        assert "$123,456" in result
    
    def test_resolve_offer_variables(self, variable_service, sample_client_data):
        """Test resolución de variables de ofertas"""
        template = "Oferta especial: {{oferta_2}} con descuento"
        
        result = variable_service.resolver_variables(template, sample_client_data)
        
        assert "$86,000" in result
    
    def test_currency_formatting(self, variable_service):
        """Test formateo de moneda"""
        # Test diferentes formatos de entrada
        test_cases = [
            (123456, "$123,456"),
            ("123456.78", "$123,456"),
            ("$123,456.00", "$123,456"),
            (0, "$0")
        ]
        
        for input_val, expected in test_cases:
            result = variable_service._formatear_moneda_sin_decimales(input_val)
            assert result == expected
    
    def test_missing_variables(self, variable_service):
        """Test variables faltantes"""
        template = "{{variable_inexistente}} y {{otra_variable}}"
        
        result = variable_service.resolver_variables(template, {})
        
        # Debe usar valores por defecto
        assert "[variable_inexistente]" in result
        assert "[otra_variable]" in result
    
    @patch('app.services.variable_service.text')
    def test_database_query_for_client(self, mock_text, variable_service):
        """Test consulta a BD para datos de cliente"""
        # Mock de la respuesta de BD
        mock_result = Mock()
        mock_result.fetchone.return_value = (
            "CARLOS TEST", "93388915", 100000, 70000, 80000,
            None, None, "BANCO TEST", "CREDITO", 15000, 10000, 5000,
            None, 80000, 20000, "300123456", "test@test.com"
        )
        
        variable_service.db.execute.return_value = mock_result
        
        result = variable_service._consultar_todos_datos_cliente("93388915")
        
        assert result["encontrado"] == True
        assert result["nombre_cliente"] == "CARLOS TEST"
        assert result["saldo_total"] == 100000

class TestVariableServicePerformance:
    """Tests de performance para variables"""
    
    def test_variable_resolution_speed(self, variable_service, sample_client_data, performance_tracker):
        """Test velocidad de resolución"""
        template = """
        Hola {{Nombre_del_cliente}},
        Tu saldo de {{saldo_total}} con {{banco}}.
        Ofertas: {{oferta_1}} y {{oferta_2}}.
        Cuotas: {{hasta_3_cuotas}}, {{hasta_6_cuotas}}, {{hasta_12_cuotas}}.
        """
        
        performance_tracker.start("variable_resolution")
        
        result = variable_service.resolver_variables(template, sample_client_data)
        
        duration = performance_tracker.end("variable_resolution")
        
        assert result is not None
        assert duration < 0.05, f"Variable resolution took {duration}s"