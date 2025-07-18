import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import joblib
import re
from sqlalchemy import text
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
import json
import torch
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
import warnings
import os
warnings.filterwarnings('ignore')

class TransformerIntentionClassifier:
    
    
    def __init__(self, db_session, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.db = db_session
        self.model_name = model_name
        self.sentence_model = None
        self.classifier = None
        self.classes = []
        self.confidence_threshold = 0.6
        self.feature_cache = {}
        
        self._initialize_transformer_model()
        self.pattern_rules = {
            'IDENTIFICACION': [
                r'\b\d{7,12}\b',
                r'\bcedula\b', r'\bdocumento\b', r'\bcc\b'
            ],
            'CONSULTA_DEUDA': [
                r'\bcuanto.*debo\b', r'\bsaldo\b', r'\bdeuda\b',
                r'\bestado.*cuenta\b', r'\bmonto.*pendiente\b'
            ],
            'INTENCION_PAGO': [
                r'\bquiero.*pagar\b', r'\bopciones.*pago\b',
                r'\bcomo.*pagar\b', r'\bvoy.*pagar\b'
            ],
            'SOLICITUD_PLAN': [
                r'\bplan.*pago\b', r'\bcuotas\b', r'\bfacilidades\b',
                r'\bacuerdo\b', r'\bnegociar\b', r'\bconvenio\b'
            ]
        }
    
    def _initialize_transformer_model(self):
        try:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"✅ sentence-transformers disponible")
            except ImportError:
                print("⚠️ sentence-transformers no instalado")
                print("💡 Instalando: pip install sentence-transformers")
                os.system("pip install sentence-transformers")
                from sentence_transformers import SentenceTransformer
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"🤖 Cargando modelo Sentence-BERT (intento {attempt+1}/{max_retries})")
                    self.sentence_model = SentenceTransformer(self.model_name)
                    print("✅ Modelo Sentence-BERT cargado exitosamente")
                    return
                except Exception as e:
                    print(f"❌ Error intento {attempt+1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        print("⚠️ Fallback a modelo simple")
                        self.sentence_model = None
                        return
            
        except Exception as e:
            print(f"❌ Error crítico inicializando transformers: {e}")
            self.sentence_model = None
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        if self.sentence_model is None:
            # Fallback a embeddings simples
            return self._generate_simple_embeddings(texts)
        
        try:
            cleaned_texts = [self._clean_text(text) for text in texts]
            embeddings = self.sentence_model.encode(
                cleaned_texts,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 100
            )
            return embeddings
        except Exception as e:
            print(f"⚠️ Error generando embeddings: {e}")
            return self._generate_simple_embeddings(texts)
    
    def _generate_simple_embeddings(self, texts: List[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        if not hasattr(self, '_simple_vectorizer'):
            self._simple_vectorizer = TfidfVectorizer(
                max_features=300,
                ngram_range=(1, 2),
                stop_words=None
            )
            cleaned_texts = [self._clean_text(text) for text in texts]
            return self._simple_vectorizer.fit_transform(cleaned_texts).toarray()
        else:
            cleaned_texts = [self._clean_text(text) for text in texts]
            return self._simple_vectorizer.transform(cleaned_texts).toarray()
    
    def _clean_text(self, texto: str) -> str:
        if not texto or pd.isna(texto):
            return ""
        texto = str(texto).lower().strip()
        texto = re.sub(r'[^\w\s\d]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto
    
    def load_training_data_enhanced(self) -> pd.DataFrame:
        print("📂 Cargando datos de entrenamiento desde BD...")
        
        all_data = []
        
        try:
            query_labeled = text("""
                SELECT 
                    texto_mensaje,
                    intencion_real,
                    confianza_etiqueta,
                    contexto_adicional
                FROM datos_entrenamiento 
                WHERE intencion_real IS NOT NULL 
                    AND validado = 1
                    AND LEN(texto_mensaje) > 2
            """)
            
            result = self.db.execute(query_labeled)
            for row in result:
                all_data.append({
                    'texto': row[0],
                    'intencion': row[1],
                    'peso': float(row[2]) if row[2] else 1.0,
                    'contexto': row[3] or '',
                    'fuente': 'etiquetado'
                })
            
            print(f"✅ Cargados {len(all_data)} ejemplos etiquetados")
        except Exception as e:
            print(f"⚠️ Error cargando datos etiquetados: {e}")
        
        try:
            query_conversations = text("""
                SELECT DISTINCT
                    m.text_content,
                    CASE 
                        WHEN m.text_content LIKE '%[0-9][0-9][0-9][0-9][0-9][0-9][0-9]%' THEN 'IDENTIFICACION'
                        WHEN m.next_state = 'informar_deuda' THEN 'CONSULTA_DEUDA'
                        WHEN m.next_state = 'proponer_planes_pago' THEN 'INTENCION_PAGO'
                        WHEN m.next_state = 'generar_acuerdo' THEN 'CONFIRMACION'
                        ELSE NULL
                    END as intencion_inferida
                FROM messages m
                WHERE m.sender_type = 'user'
                    AND LEN(m.text_content) > 3
                    AND LEN(m.text_content) < 200
                    AND m.timestamp > DATEADD(day, -30, GETDATE())
            """)
            
            result = self.db.execute(query_conversations)
            inferred_count = 0
            for row in result:
                if row[1]:  # Si hay intención inferida
                    all_data.append({
                        'texto': row[0],
                        'intencion': row[1],
                        'peso': 0.7,  # Menor peso para datos inferidos
                        'contexto': '',
                        'fuente': 'inferido'
                    })
                    inferred_count += 1
            
            print(f"✅ Cargados {inferred_count} ejemplos inferidos de conversaciones")
        except Exception as e:
            print(f"⚠️ Error cargando datos de conversaciones: {e}")
        
        # Datos base (si no hay suficientes datos)
        if len(all_data) < 100:
            base_data = self._generate_base_training_data()
            all_data.extend(base_data)
            print(f"✅ Agregados {len(base_data)} ejemplos base")
        
        # Convertir a DataFrame
        df = pd.DataFrame(all_data)
        
        if df.empty:
            raise ValueError("No se pudieron cargar datos de entrenamiento")
        
        print(f"📊 Total datos cargados: {len(df)}")
        print(f"📊 Distribución de intenciones:")
        print(df['intencion'].value_counts())
        
        return df
    
    def _generate_base_training_data(self) -> List[Dict]:
        base_examples = [
            # IDENTIFICACION
            {"texto": "mi cedula es 1020428633", "intencion": "IDENTIFICACION", "peso": 1.0},
            {"texto": "documento 93388915", "intencion": "IDENTIFICACION", "peso": 1.0},
            {"texto": "soy carlos perez cc 12345678", "intencion": "IDENTIFICACION", "peso": 1.0},
            
            # CONSULTA_DEUDA
            {"texto": "cuanto debo", "intencion": "CONSULTA_DEUDA", "peso": 1.0},
            {"texto": "cual es mi saldo", "intencion": "CONSULTA_DEUDA", "peso": 1.0},
            {"texto": "informacion de mi deuda", "intencion": "CONSULTA_DEUDA", "peso": 1.0},
            
            # INTENCION_PAGO
            {"texto": "quiero pagar", "intencion": "INTENCION_PAGO", "peso": 1.0},
            {"texto": "como puedo cancelar", "intencion": "INTENCION_PAGO", "peso": 1.0},
            {"texto": "opciones de pago", "intencion": "INTENCION_PAGO", "peso": 1.0},
            
            # SOLICITUD_PLAN
            {"texto": "plan de pagos", "intencion": "SOLICITUD_PLAN", "peso": 1.0},
            {"texto": "facilidades", "intencion": "SOLICITUD_PLAN", "peso": 1.0},
            {"texto": "acuerdo de pago", "intencion": "SOLICITUD_PLAN", "peso": 1.0},
            
            # CONFIRMACION
            {"texto": "si acepto", "intencion": "CONFIRMACION", "peso": 1.0},
            {"texto": "está bien", "intencion": "CONFIRMACION", "peso": 1.0},
            {"texto": "de acuerdo", "intencion": "CONFIRMACION", "peso": 1.0},
            
            # RECHAZO
            {"texto": "no puedo", "intencion": "RECHAZO", "peso": 1.0},
            {"texto": "no me interesa", "intencion": "RECHAZO", "peso": 1.0},
            {"texto": "imposible", "intencion": "RECHAZO", "peso": 1.0},
            
            # SALUDO
            {"texto": "hola", "intencion": "SALUDO", "peso": 1.0},
            {"texto": "buenos dias", "intencion": "SALUDO", "peso": 1.0},
            {"texto": "buenas tardes", "intencion": "SALUDO", "peso": 1.0},
            
            # DESPEDIDA
            {"texto": "gracias", "intencion": "DESPEDIDA", "peso": 1.0},
            {"texto": "hasta luego", "intencion": "DESPEDIDA", "peso": 1.0},
            {"texto": "adios", "intencion": "DESPEDIDA", "peso": 1.0}
        ]
        
        for example in base_examples:
            example['contexto'] = ''
            example['fuente'] = 'base'
        
        return base_examples
    
    def train_enhanced_model(self) -> Dict:
        print("🚀 Iniciando entrenamiento con Transformers...")
        
        # Cargar datos
        df = self.load_training_data_enhanced()
        
        # Generar embeddings
        print("🔄 Generando embeddings...")
        texts = df['texto'].tolist()
        embeddings = self.generate_embeddings(texts)
        
        print(f"✅ Embeddings generados: {embeddings.shape}")
        
        # Preparar datos
        X = embeddings
        y = df['intencion']
        sample_weights = df['peso'].values
        
        # División estratificada
        X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
            X, y, sample_weights, 
            test_size=0.2, 
            random_state=42, 
            stratify=y
        )
        
        # Entrenar ensemble de clasificadores
        print("🤖 Entrenando ensemble de clasificadores...")
        
        # Clasificador 1: Random Forest
        rf_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        rf_classifier.fit(X_train, y_train, sample_weight=weights_train)
        
        # Clasificador 2: Logistic Regression
        lr_classifier = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced'
        )
        lr_classifier.fit(X_train, y_train, sample_weight=weights_train)
        
        # Ensemble (votación)
        self.classifier = {
            'rf': rf_classifier,
            'lr': lr_classifier,
            'classes': list(rf_classifier.classes_)
        }
        self.classes = list(rf_classifier.classes_)
        
        # Evaluar
        y_pred_rf = rf_classifier.predict(X_test)
        y_pred_lr = lr_classifier.predict(X_test)
        
        # Votación simple para ensemble
        y_pred_ensemble = []
        for i in range(len(y_test)):
            votes = [y_pred_rf[i], y_pred_lr[i]]
            # Tomar voto mayoritario o RF si empate
            pred = max(set(votes), key=votes.count) if len(set(votes)) > 1 else y_pred_rf[i]
            y_pred_ensemble.append(pred)
        
        accuracy_rf = accuracy_score(y_test, y_pred_rf)
        accuracy_lr = accuracy_score(y_test, y_pred_lr)
        accuracy_ensemble = accuracy_score(y_test, y_pred_ensemble)
        
        print(f"🎯 Accuracy Random Forest: {accuracy_rf:.3f}")
        print(f"🎯 Accuracy Logistic Regression: {accuracy_lr:.3f}")
        print(f"🎯 Accuracy Ensemble: {accuracy_ensemble:.3f}")
        
        print("📊 Reporte detallado (Ensemble):")
        print(classification_report(y_test, y_pred_ensemble))
        
        # Guardar modelo
        model_data = {
            'sentence_model_name': self.model_name,
            'classifier': self.classifier,
            'classes': self.classes,
            'confidence_threshold': self.confidence_threshold,
            'training_stats': {
                'accuracy_rf': accuracy_rf,
                'accuracy_lr': accuracy_lr,
                'accuracy_ensemble': accuracy_ensemble,
                'training_samples': len(df),
                'test_samples': len(y_test)
            }
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"models/transformer_classifier_{timestamp}.joblib"
        joblib.dump(model_data, model_path)
        
        print(f"💾 Modelo guardado en: {model_path}")
        
        # Registrar en BD
        self._register_model_in_db(model_path, accuracy_ensemble, len(df))
        
        return {
            "model_path": model_path,
            "accuracy_ensemble": accuracy_ensemble,
            "accuracy_rf": accuracy_rf,
            "accuracy_lr": accuracy_lr,
            "training_samples": len(df),
            "classes": self.classes
        }
    
    def load_model(self, model_path: str = None):
        if not model_path:
            try:
                query = text("""
                    SELECT TOP 1 ruta_modelo 
                    FROM modelos_ml 
                    WHERE activo = 1 AND tipo LIKE '%transformer%'
                    ORDER BY fecha_entrenamiento DESC
                """)
                result = self.db.execute(query).fetchone()
                if result:
                    model_path = result[0]
            except:
                pass
        
        if model_path and model_path.endswith('.joblib'):
            try:
                model_data = joblib.load(model_path)
                
                # Cargar Sentence-BERT si es diferente
                if model_data['sentence_model_name'] != self.model_name:
                    self.model_name = model_data['sentence_model_name']
                    self._initialize_transformer_model()
                
                self.classifier = model_data['classifier']
                self.classes = model_data['classes']
                self.confidence_threshold = model_data.get('confidence_threshold', 0.6)
                
                print(f"✅ Modelo Transformer cargado desde: {model_path}")
                return True
            except Exception as e:
                print(f"❌ Error cargando modelo: {e}")
        
        return False
    
    def predict_intention(self, mensaje: str, context: Dict = None) -> Dict:
        if not self.classifier:
            return {
                "intencion": "DESCONOCIDA",
                "confianza": 0.0,
                "metodo": "no_model"
            }
        
        try:
            rule_result = self._apply_priority_rules(mensaje, context)
            if rule_result['confianza'] > 0.9:
                return rule_result
            

            embedding = self.generate_embeddings([mensaje])
            

            rf_proba = self.classifier['rf'].predict_proba(embedding)[0]
            lr_proba = self.classifier['lr'].predict_proba(embedding)[0]
            

            ensemble_proba = (rf_proba * 0.6 + lr_proba * 0.4)
            

            max_idx = np.argmax(ensemble_proba)
            intencion = self.classes[max_idx]
            confianza = ensemble_proba[max_idx]
            
            if confianza < self.confidence_threshold:
                intencion = "DESCONOCIDA"
            
            return {
                "intencion": intencion,
                "confianza": float(confianza),
                "metodo": "transformer_ensemble",
                "all_probabilities": {
                    cls: float(prob) for cls, prob in zip(self.classes, ensemble_proba)
                }
            }
            
        except Exception as e:
            print(f"❌ Error en predicción Transformer: {e}")
            return self._apply_priority_rules(mensaje, context)
    
    def _apply_priority_rules(self, mensaje: str, context: Dict = None) -> Dict:
        mensaje_lower = mensaje.lower()
        
        for intencion, patterns in self.pattern_rules.items():
            for pattern in patterns:
                if re.search(pattern, mensaje_lower):
                    return {
                        "intencion": intencion,
                        "confianza": 0.95,
                        "metodo": "priority_rule",
                        "pattern_matched": pattern
                    }
        
        return {
            "intencion": "DESCONOCIDA", 
            "confianza": 0.0,
            "metodo": "no_match"
        }
    
    def _register_model_in_db(self, model_path: str, accuracy: float, samples: int):
        try:
            update_query = text("""
                UPDATE modelos_ml 
                SET activo = 0 
                WHERE tipo = 'transformer_ensemble'
            """)
            self.db.execute(update_query)
            

            insert_query = text("""
                INSERT INTO modelos_ml 
                (nombre, tipo, ruta_modelo, accuracy, ejemplos_entrenamiento, activo)
                VALUES (:nombre, :tipo, :ruta, :accuracy, :ejemplos, 1)
            """)
            self.db.execute(insert_query, {
                "nombre": f"Transformer_Ensemble_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "tipo": "transformer_ensemble",
                "ruta": model_path,
                "accuracy": accuracy,
                "ejemplos": samples
            })
            
            self.db.commit()
            print("✅ Modelo registrado en BD")
            
        except Exception as e:
            print(f"⚠️ Error registrando modelo: {e}")
            self.db.rollback()


class IncrementalTrainer:
    def __init__(self, db_session):
        self.db = db_session
        self.classifier = TransformerIntentionClassifier(db_session)
    
    def add_training_example(self, texto: str, intencion_real: str, confianza: float = 1.0):
        try:
            insert_query = text("""
                INSERT INTO datos_entrenamiento 
                (texto_mensaje, intencion_real, confianza_etiqueta, fecha_registro, validado)
                VALUES (:texto, :intencion, :confianza, GETDATE(), 1)
            """)
            self.db.execute(insert_query, {
                "texto": texto,
                "intencion": intencion_real,
                "confianza": confianza
            })
            self.db.commit()
            print(f"✅ Ejemplo agregado: '{texto}' -> {intencion_real}")
            return True
        except Exception as e:
            print(f"❌ Error agregando ejemplo: {e}")
            self.db.rollback()
            return False
    
    def retrain_if_needed(self, min_new_examples: int = 20) -> bool:
        try:

            query = text("""
                SELECT COUNT(*) 
                FROM datos_entrenamiento 
                WHERE fecha_registro > DATEADD(day, -7, GETDATE())
                    AND validado = 1
            """)
            new_examples = self.db.execute(query).scalar()
            
            if new_examples >= min_new_examples:
                print(f"🔄 Reentrenando con {new_examples} ejemplos nuevos...")
                result = self.classifier.train_enhanced_model()
                return result['accuracy_ensemble'] > 0.8
            else:
                print(f"ℹ️ Solo {new_examples} ejemplos nuevos (mínimo: {min_new_examples})")
                return False
                
        except Exception as e:
            print(f"❌ Error en reentrenamiento: {e}")
            return False



def create_transformer_classifier(db_session) -> TransformerIntentionClassifier:
    return TransformerIntentionClassifier(db_session)