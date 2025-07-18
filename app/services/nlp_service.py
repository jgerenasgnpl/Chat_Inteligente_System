"""
NLP_SERVICE.PY MEJORADO
- Mejor confianza en las predicciones
- Datos de entrenamiento expandidos
- Validación y mejoras automáticas
- Compatible con el sistema inteligente
"""

import re
import string
import logging
from collections import Counter
from typing import Dict, List, Any, Set
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
import glob
from pathlib import Path
import numpy as np
from app.services.cache_service import cache_service, cache_result

logger = logging.getLogger(__name__)

def obtener_modelo_mas_reciente():
    """Obtener modelo más reciente con búsqueda mejorada"""
    from pathlib import Path
    
    models_dir = Path("models")
    
    print(f"🔍 Buscando modelos en: {models_dir.absolute()}")
    
    if not models_dir.exists():
        print(f"❌ Directorio models no existe")
        try:
            models_dir.mkdir(exist_ok=True)
            print(f"✅ Directorio models creado")
        except Exception as e:
            print(f"❌ Error creando directorio: {e}")
        return None
    
    # Buscar modelos
    patterns = [
        "intention_classifier_IMPROVED_*.joblib",
        "intention_classifier_FIXED_*.joblib",
        "intention_classifier_optimizado_*.joblib", 
        "transformer_classifier_*.joblib",
        "intention_classifier_*.joblib",
        "*classifier*.joblib",
        "*.joblib"
    ]
    
    print(f"📂 Contenido del directorio models:")
    try:
        all_files = list(models_dir.iterdir())
        for file in all_files:
            print(f"   - {file.name}")
        
        if not all_files:
            print(f"   (directorio vacío)")
    except Exception as e:
        print(f"❌ Error listando directorio: {e}")
    
    # Buscar por patrones
    for pattern in patterns:
        try:
            files = list(models_dir.glob(pattern))
            print(f"🔍 Patrón '{pattern}': {len(files)} archivos")
            
            if files:
                latest_file = max(files, key=lambda x: x.stat().st_mtime)
                print(f"✅ Modelo encontrado: {latest_file}")
                return str(latest_file)
                
        except Exception as e:
            print(f"⚠️ Error con patrón {pattern}: {e}")
    
    print(f"❌ No se encontró ningún modelo")
    return None

class ImprovedNLPService:
    """
    🧠 SERVICIO NLP MEJORADO
    - Mejor precisión y confianza
    - Datos de entrenamiento expandidos
    - Validación automática
    - Fallbacks inteligentes
    """
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.label_encoder = None
        self.confidence_threshold = 0.6
        
        # Datos de entrenamiento expandidos y mejorados
        self.expanded_training_data = self._get_expanded_training_data()
        
        # Patrones de regex para validación
        self.regex_patterns = {
            'IDENTIFICACION': [
                r'\b\d{7,12}\b',
                r'cedula\s*:?\s*\d{7,12}',
                r'documento\s*:?\s*\d{7,12}',
                r'cc\s*:?\s*\d{7,12}'
            ],
            'CONFIRMACION': [
                r'\b(si|sí|acepto|ok|está bien|de acuerdo|confirmo|dale|bueno)\b',
                r'\b(acepta|acept|confirm)\w*\b'
            ],
            'RECHAZO': [
                r'\b(no|nop|negativo|imposible|no puedo|no me interesa)\b',
                r'\b(rechaz|neg)\w*\b'
            ],
            'INTENCION_PAGO': [
                r'\b(quiero|necesito|deseo)\s+(pagar|cancelar|liquidar)\b',
                r'\b(pagar|cancelar|liquidar|abonar)\b'
            ],
            'SOLICITUD_PLAN': [
                r'\b(opciones|planes|facilidades|descuento|rebaja)\b',
                r'\b(plan\s+de\s+pago|cuotas|facilidad)\b'
            ]
        }
        
        # Cargar o entrenar modelo
        self._load_model()
    
    def _get_expanded_training_data(self):
        """Datos de entrenamiento expandidos para mejor precisión"""
        return [
            # ===== IDENTIFICACION =====
            ("12345678", "IDENTIFICACION"),
            ("93388915", "IDENTIFICACION"),
            ("1020428633", "IDENTIFICACION"),
            ("mi cedula es 12345678", "IDENTIFICACION"),
            ("documento 93388915", "IDENTIFICACION"),
            ("cc 1020428633", "IDENTIFICACION"),
            ("cedula: 12345678", "IDENTIFICACION"),
            ("mi documento es 93388915", "IDENTIFICACION"),
            ("soy el 12345678", "IDENTIFICACION"),
            ("tengo la cedula 93388915", "IDENTIFICACION"),
            
            # ===== SOLICITUD_PLAN =====
            ("quiero opciones", "SOLICITUD_PLAN"),
            ("necesito plan", "SOLICITUD_PLAN"),
            ("facilidades", "SOLICITUD_PLAN"),
            ("opciones de pago", "SOLICITUD_PLAN"),
            ("plan de pagos", "SOLICITUD_PLAN"),
            ("cuotas", "SOLICITUD_PLAN"),
            ("descuento", "SOLICITUD_PLAN"),
            ("rebaja", "SOLICITUD_PLAN"),
            ("que opciones tengo", "SOLICITUD_PLAN"),
            ("como puedo pagar", "SOLICITUD_PLAN"),
            ("planes de cuotas", "SOLICITUD_PLAN"),
            ("facilidades de pago", "SOLICITUD_PLAN"),
            ("ver opciones", "SOLICITUD_PLAN"),
            ("mostrar planes", "SOLICITUD_PLAN"),
            ("quiero ver las opciones", "SOLICITUD_PLAN"),
            ("que facilidades hay", "SOLICITUD_PLAN"),
            ("hay descuentos", "SOLICITUD_PLAN"),
            ("puedo pagar en cuotas", "SOLICITUD_PLAN"),
            
            # ===== CONFIRMACION =====
            ("si", "CONFIRMACION"),
            ("sí", "CONFIRMACION"),
            ("acepto", "CONFIRMACION"),
            ("está bien", "CONFIRMACION"),
            ("de acuerdo", "CONFIRMACION"),
            ("confirmo", "CONFIRMACION"),
            ("ok", "CONFIRMACION"),
            ("bueno", "CONFIRMACION"),
            ("dale", "CONFIRMACION"),
            ("perfecto", "CONFIRMACION"),
            ("excelente", "CONFIRMACION"),
            ("si acepto", "CONFIRMACION"),
            ("si quiero", "CONFIRMACION"),
            ("si me interesa", "CONFIRMACION"),
            ("si está bien", "CONFIRMACION"),
            ("me parece bien", "CONFIRMACION"),
            ("estoy de acuerdo", "CONFIRMACION"),
            
            # ===== INTENCION_PAGO =====
            ("quiero pagar", "INTENCION_PAGO"),
            ("necesito pagar", "INTENCION_PAGO"),
            ("como pagar", "INTENCION_PAGO"),
            ("pagar deuda", "INTENCION_PAGO"),
            ("realizar pago", "INTENCION_PAGO"),
            ("cancelar deuda", "INTENCION_PAGO"),
            ("liquidar", "INTENCION_PAGO"),
            ("abonar", "INTENCION_PAGO"),
            ("consignar", "INTENCION_PAGO"),
            ("pagar mi cuenta", "INTENCION_PAGO"),
            ("quiero cancelar", "INTENCION_PAGO"),
            ("voy a pagar", "INTENCION_PAGO"),
            ("necesito cancelar mi deuda", "INTENCION_PAGO"),
            
            # ===== CONSULTA_DEUDA =====
            ("cuanto debo", "CONSULTA_DEUDA"),
            ("mi saldo", "CONSULTA_DEUDA"),
            ("información", "CONSULTA_DEUDA"),
            ("cual es mi deuda", "CONSULTA_DEUDA"),
            ("saldo pendiente", "CONSULTA_DEUDA"),
            ("valor de mi deuda", "CONSULTA_DEUDA"),
            ("cuanto tengo pendiente", "CONSULTA_DEUDA"),
            ("mi cuenta", "CONSULTA_DEUDA"),
            ("estado de cuenta", "CONSULTA_DEUDA"),
            ("consultar saldo", "CONSULTA_DEUDA"),
            ("ver mi deuda", "CONSULTA_DEUDA"),
            ("información de mi cuenta", "CONSULTA_DEUDA"),
            
            # ===== RECHAZO =====
            ("no puedo", "RECHAZO"),
            ("no me interesa", "RECHAZO"),
            ("imposible", "RECHAZO"),
            ("no tengo dinero", "RECHAZO"),
            ("no", "RECHAZO"),
            ("nop", "RECHAZO"),
            ("negativo", "RECHAZO"),
            ("no acepto", "RECHAZO"),
            ("no quiero", "RECHAZO"),
            ("muy caro", "RECHAZO"),
            ("no me sirve", "RECHAZO"),
            ("no me conviene", "RECHAZO"),
            ("rechazo", "RECHAZO"),
            ("no gracias", "RECHAZO"),
            
            # ===== SALUDO =====
            ("hola", "SALUDO"),
            ("buenos días", "SALUDO"),
            ("buenas", "SALUDO"),
            ("buenas tardes", "SALUDO"),
            ("buenas noches", "SALUDO"),
            ("hi", "SALUDO"),
            ("que tal", "SALUDO"),
            ("como estas", "SALUDO"),
            ("buen día", "SALUDO"),
            ("saludos", "SALUDO"),
            
            # ===== DESPEDIDA =====
            ("gracias", "DESPEDIDA"),
            ("hasta luego", "DESPEDIDA"),
            ("adios", "DESPEDIDA"),
            ("chao", "DESPEDIDA"),
            ("bye", "DESPEDIDA"),
            ("muchas gracias", "DESPEDIDA"),
            ("que tengas buen día", "DESPEDIDA"),
            ("nos vemos", "DESPEDIDA"),
            ("hasta pronto", "DESPEDIDA"),
            
            # ===== CASOS MIXTOS Y COMPLEJOS =====
            ("hola quiero pagar", "INTENCION_PAGO"),
            ("buenos días, cuanto debo", "CONSULTA_DEUDA"),
            ("si quiero ver las opciones", "SOLICITUD_PLAN"),
            ("no puedo pagar todo", "RECHAZO"),
            ("acepto el plan de cuotas", "CONFIRMACION"),
            ("mi cedula es 12345 y quiero pagar", "IDENTIFICACION"),
            ("opciones para pagar por cuotas", "SOLICITUD_PLAN"),
            ("está muy caro, hay descuento", "SOLICITUD_PLAN"),
            ("confirmo la primera opción", "CONFIRMACION"),
        ]
    
    def _load_model(self):
        """Cargar modelo con entrenamiento mejorado si es necesario"""
        try:
            from joblib import load
            model_path = obtener_modelo_mas_reciente()
            
            if model_path and os.path.exists(model_path):
                try:
                    saved_data = load(model_path)
                    
                    # Verificar estructura del modelo guardado
                    if isinstance(saved_data, dict):
                        self.model = saved_data.get('model')
                        self.vectorizer = saved_data.get('vectorizer')
                        self.label_encoder = saved_data.get('label_encoder')
                    else:
                        self.model = saved_data
                    
                    # Test del modelo
                    if hasattr(self.model, 'predict') and self.vectorizer:
                        test_result = self._test_model_safely()
                        if test_result:
                            print(f"✅ Modelo ML cargado y validado: {model_path}")
                            return
                    
                    print(f"⚠️ Modelo cargado pero falló validación")
                    self.model = None
                    
                except Exception as load_error:
                    print(f"❌ Error cargando modelo {model_path}: {load_error}")
                    self.model = None
            
            # Entrenar modelo mejorado si no se pudo cargar
            print("🔄 Entrenando modelo mejorado...")
            self._train_improved_model()
                
        except Exception as e:
            print(f"❌ Error general en carga ML: {e}")
            self.model = None
    
    def _test_model_safely(self):
        """Test seguro del modelo cargado"""
        try:
            test_texts = ["quiero pagar", "12345678", "si acepto"]
            
            if self.vectorizer:
                features = self.vectorizer.transform(test_texts)
                predictions = self.model.predict(features)
                probabilities = self.model.predict_proba(features)
                
                return len(predictions) == len(test_texts) and len(probabilities) == len(test_texts)
            else:
                # Para modelos que no usan vectorizer separado
                predictions = self.model.predict(test_texts)
                return len(predictions) == len(test_texts)
                
        except Exception as e:
            print(f"⚠️ Error en test del modelo: {e}")
            return False
    
    def _train_improved_model(self):
        """Entrenar modelo mejorado con datos expandidos"""
        try:
            print("🔄 Entrenando modelo NLP mejorado...")
            
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.preprocessing import LabelEncoder
            from sklearn.pipeline import Pipeline
            from sklearn.model_selection import cross_val_score
            import joblib
            from pathlib import Path
            from datetime import datetime
            
            # Preparar datos
            texts = [item[0] for item in self.expanded_training_data]
            labels = [item[1] for item in self.expanded_training_data]
            
            print(f"📊 Entrenando con {len(texts)} ejemplos")
            print(f"📊 Intenciones: {set(labels)}")
            
            # Crear vectorizador mejorado
            self.vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 3),  # Incluir trigramas
                lowercase=True,
                stop_words=None,
                min_df=1,
                max_df=0.95,
                analyzer='word',
                token_pattern=r'\b\w+\b'
            )
            
            # Crear codificador de etiquetas
            self.label_encoder = LabelEncoder()
            encoded_labels = self.label_encoder.fit_transform(labels)
            
            # Vectorizar textos
            X = self.vectorizer.fit_transform(texts)
            
            # Entrenar clasificador mejorado
            self.model = MultinomialNB(alpha=0.5)  # Suavizado reducido para mejor precisión
            self.model.fit(X, encoded_labels)
            
            # Validación cruzada
            scores = cross_val_score(self.model, X, encoded_labels, cv=3, scoring='accuracy')
            print(f"📊 Precisión promedio: {scores.mean():.3f} (+/- {scores.std() * 2:.3f})")
            
            # Test con casos específicos
            self._test_trained_model()
            
            # Guardar modelo mejorado
            self._save_improved_model()
            
            print("✅ Modelo mejorado entrenado correctamente")
            
        except Exception as e:
            print(f"❌ Error entrenando modelo: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
    
    def _test_trained_model(self):
        """Test del modelo recién entrenado"""
        test_cases = [
            ("quiero opciones", "SOLICITUD_PLAN"),
            ("12345678", "IDENTIFICACION"),
            ("si acepto", "CONFIRMACION"),
            ("cuanto debo", "CONSULTA_DEUDA"),
            ("no puedo", "RECHAZO"),
            ("hola", "SALUDO"),
            ("quiero pagar", "INTENCION_PAGO")
        ]
        
        print("🧪 Testing modelo entrenado:")
        correct_predictions = 0
        
        for test_text, expected in test_cases:
            result = self.predict(test_text)
            prediction = result.get('intention', 'DESCONOCIDA')
            confidence = result.get('confidence', 0.0)
            
            is_correct = prediction == expected
            if is_correct:
                correct_predictions += 1
            
            status = "✅" if is_correct else "❌"
            print(f"   {status} '{test_text}' → {prediction} ({confidence:.3f}) [esperado: {expected}]")
        
        accuracy = correct_predictions / len(test_cases)
        print(f"📊 Precisión en test: {accuracy:.3f} ({correct_predictions}/{len(test_cases)})")
        
        return accuracy >= 0.7
    
    def _save_improved_model(self):
        """Guardar modelo mejorado"""
        try:
            from pathlib import Path
            import joblib
            from datetime import datetime
            
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = models_dir / f"intention_classifier_IMPROVED_{timestamp}.joblib"
            
            # Guardar todo junto
            model_data = {
                'model': self.model,
                'vectorizer': self.vectorizer,
                'label_encoder': self.label_encoder,
                'training_data_size': len(self.expanded_training_data),
                'created_at': datetime.now().isoformat(),
                'version': 'improved_v2'
            }
            
            joblib.dump(model_data, model_path)
            print(f"💾 Modelo mejorado guardado en: {model_path}")
            
        except Exception as e:
            print(f"❌ Error guardando modelo: {e}")
    
    def predict(self, text: str) -> dict:
        """Predicción mejorada con validaciones múltiples"""
        try:
            if not text or len(text.strip()) == 0:
                return {"intention": "DESCONOCIDA", "confidence": 0.0}
            
            # 1. VALIDACIÓN CON REGEX (ALTA CONFIANZA)
            regex_result = self._validate_with_regex(text)
            if regex_result['confidence'] >= 0.9:
                return regex_result
            
            # 2. PREDICCIÓN CON ML
            if self.model and self.vectorizer:
                ml_result = self._predict_with_ml(text)
                
                # Combinar con validación regex si hay coincidencia parcial
                if regex_result['confidence'] > 0.0 and ml_result['confidence'] > 0.6:
                    # Si regex y ML coinciden, aumentar confianza
                    if regex_result['intention'] == ml_result['intention']:
                        ml_result['confidence'] = min(ml_result['confidence'] + 0.2, 1.0)
                
                return ml_result
            
            # 3. FALLBACK CON REGLAS
            return self._fallback_classification(text)
            
        except Exception as e:
            print(f"❌ Error en predicción: {e}")
            return {"intention": "DESCONOCIDA", "confidence": 0.0}
    
    def _validate_with_regex(self, text: str) -> dict:
        """Validación con patrones regex"""
        text_lower = text.lower().strip()
        
        for intention, patterns in self.regex_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Calcular confianza basada en la especificidad del patrón
                    confidence = 0.95 if len(pattern) > 20 else 0.85
                    
                    return {
                        "intention": intention,
                        "confidence": confidence,
                        "method": "regex_validation"
                    }
        
        return {"intention": "DESCONOCIDA", "confidence": 0.0}
    
    def _predict_with_ml(self, text: str) -> dict:
        """Predicción con modelo ML"""
        try:
            # Limpiar texto
            text_clean = self._clean_text_for_ml(text)
            
            if not text_clean:
                return {"intention": "DESCONOCIDA", "confidence": 0.0}
            
            # Vectorizar
            features = self.vectorizer.transform([text_clean])
            
            # Predecir
            prediction_encoded = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            
            # Decodificar
            prediction = self.label_encoder.inverse_transform([prediction_encoded])[0]
            confidence = max(probabilities)
            
            # Ajustar confianza basada en características del texto
            adjusted_confidence = self._adjust_confidence(text, prediction, confidence)
            
            return {
                "intention": prediction,
                "confidence": float(adjusted_confidence),
                "method": "ml_prediction"
            }
            
        except Exception as e:
            print(f"❌ Error en ML prediction: {e}")
            return {"intention": "DESCONOCIDA", "confidence": 0.0}
    
    def _clean_text_for_ml(self, text: str) -> str:
        """Limpiar texto para ML optimizado"""
        if not text:
            return ""
        
        import re
        
        # Convertir a minúsculas
        text = str(text).lower().strip()
        
        # Preservar números importantes (cédulas)
        text = re.sub(r'\b(\d{7,12})\b', r'NUMERO_DOCUMENTO', text)
        
        # Limpiar caracteres especiales pero preservar espacios
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _adjust_confidence(self, original_text: str, prediction: str, confidence: float) -> float:
        """Ajustar confianza basada en características del texto"""
        
        # Ajustes por longitud del texto
        text_length = len(original_text.strip())
        if text_length < 3:
            confidence *= 0.7  # Reducir confianza para textos muy cortos
        elif text_length > 50:
            confidence *= 1.1  # Aumentar ligeramente para textos más descriptivos
        
        # Ajustes por tipo de predicción
        if prediction == 'IDENTIFICACION':
            # Para identificación, verificar que realmente hay un número
            if re.search(r'\b\d{7,12}\b', original_text):
                confidence = min(confidence * 1.2, 1.0)
            else:
                confidence *= 0.5
        
        elif prediction == 'CONFIRMACION':
            # Para confirmaciones, verificar palabras clave específicas
            confirmacion_keywords = ['si', 'sí', 'acepto', 'ok', 'confirmo']
            if any(keyword in original_text.lower() for keyword in confirmacion_keywords):
                confidence = min(confidence * 1.15, 1.0)
        
        elif prediction == 'SOLICITUD_PLAN':
            # Para solicitudes de plan, verificar contexto
            plan_keywords = ['opciones', 'planes', 'cuotas', 'facilidades']
            if any(keyword in original_text.lower() for keyword in plan_keywords):
                confidence = min(confidence * 1.1, 1.0)
        
        return min(confidence, 1.0)
    
    def _fallback_classification(self, text: str) -> dict:
        """Clasificación de fallback con reglas simples"""
        text_lower = text.lower()
        
        # Reglas básicas de fallback
        if re.search(r'\b\d{7,12}\b', text):
            return {"intention": "IDENTIFICACION", "confidence": 0.8}
        
        if any(word in text_lower for word in ['si', 'sí', 'acepto', 'ok']):
            return {"intention": "CONFIRMACION", "confidence": 0.7}
        
        if any(word in text_lower for word in ['no', 'imposible', 'no puedo']):
            return {"intention": "RECHAZO", "confidence": 0.7}
        
        if any(word in text_lower for word in ['opciones', 'planes', 'cuotas']):
            return {"intention": "SOLICITUD_PLAN", "confidence": 0.6}
        
        if any(word in text_lower for word in ['pagar', 'cancelar', 'liquidar']):
            return {"intention": "INTENCION_PAGO", "confidence": 0.6}
        
        if any(word in text_lower for word in ['cuanto', 'debo', 'saldo']):
            return {"intention": "CONSULTA_DEUDA", "confidence": 0.6}
        
        if any(word in text_lower for word in ['hola', 'buenas', 'buenos']):
            return {"intention": "SALUDO", "confidence": 0.7}
        
        return {"intention": "DESCONOCIDA", "confidence": 0.0}
    
    def actualizar_cache(self, db: Session):
        """Actualizar cache (compatibilidad)"""
        print("✅ NLP Service mejorado - Cache actualizado")
        return True
    
    def get_model_info(self) -> dict:
        """Obtener información del modelo"""
        return {
            "model_loaded": self.model is not None,
            "vectorizer_loaded": self.vectorizer is not None,
            "training_data_size": len(self.expanded_training_data),
            "confidence_threshold": self.confidence_threshold,
            "intentions_supported": list(set([item[1] for item in self.expanded_training_data])),
            "regex_patterns_count": sum(len(patterns) for patterns in self.regex_patterns.values()),
            "version": "improved_v2"
        }

# Instancia global mejorada
nlp_service = ImprovedNLPService()

class ImprovedNLPServiceWithCache(ImprovedNLPService):
    """NLP Service con Redis Cache"""
    
    def __init__(self):
        super().__init__()
        self.cache = cache_service
    
    def predict(self, text: str) -> dict:
        """Predicción con cache"""
        
        if not text or len(text.strip()) == 0:
            return {"intention": "DESCONOCIDA", "confidence": 0.0}
        
        # 1. Verificar cache de predicciones ML
        cached_prediction = self.cache.get_cached_ml_prediction(text)
        if cached_prediction:
            logger.debug(f"🎯 ML Cache HIT: {text[:20]}...")
            return cached_prediction
        
        # 2. Ejecutar predicción normal
        logger.debug(f"💾 ML Cache MISS: {text[:20]}... - ejecutando ML")
        result = super().predict(text)
        
        # 3. Guardar en cache si la confianza es suficiente
        if result.get('confidence', 0) >= 0.6:
            self.cache.cache_ml_prediction(text, result, ttl=1800)  # 30 minutos
            logger.debug(f"💾 ML prediction guardada en cache")
        
        return result
    
# Test automático al importar
def test_nlp_service_automatically():
    """Test automático del servicio"""
    test_cases = [
        ("12345678", "IDENTIFICACION"),
        ("quiero opciones", "SOLICITUD_PLAN"),
        ("si acepto", "CONFIRMACION"),
        ("no puedo", "RECHAZO"),
        ("cuanto debo", "CONSULTA_DEUDA"),
        ("quiero pagar", "INTENCION_PAGO")
    ]
    
    print("🧪 Test automático NLP Service:")
    passed = 0
    
    for text, expected in test_cases:
        result = nlp_service.predict(text)
        prediction = result.get('intention')
        confidence = result.get('confidence', 0)
        
        is_correct = prediction == expected and confidence >= 0.6
        if is_correct:
            passed += 1
        
        status = "✅" if is_correct else "❌"
        print(f"   {status} '{text}' → {prediction} ({confidence:.2f})")
    
    print(f"📊 Test resultado: {passed}/{len(test_cases)} casos correctos")
    
    if passed >= len(test_cases) * 0.8:
        print("🎉 NLP Service funcionando correctamente")
    else:
        print("⚠️ NLP Service necesita mejoras")

# Ejecutar test automático
if __name__ == "__main__":
    test_nlp_service_automatically()
    print(f"\n📋 Información del modelo:")
    info = nlp_service.get_model_info()
    for key, value in info.items():
        print(f"   {key}: {value}")