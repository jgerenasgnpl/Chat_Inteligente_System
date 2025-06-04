import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import re
from sqlalchemy import text
from typing import Dict, List, Tuple
from datetime import datetime
import json

class MLIntentionClassifier:
    """
    Clasificador de intenciones usando Naive Bayes y TF-IDF
    Simple pero efectivo para sistemas de cobranza
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.model = None
        self.pipeline = None
        self.classes = []
        self.confidence_threshold = 0.6
        
        # Preprocesamiento específico para español
        self.stop_words_es = {
            'a', 'al', 'algo', 'algunas', 'algunos', 'ante', 'antes', 'como', 'con',
            'contra', 'cual', 'cuando', 'de', 'del', 'desde', 'donde', 'durante',
            'e', 'el', 'ella', 'ellas', 'ellos', 'en', 'entre', 'era', 'eres', 'es',
            'esa', 'ese', 'eso', 'esta', 'estas', 'este', 'esto', 'estos', 'ha',
            'había', 'han', 'has', 'hasta', 'he', 'la', 'las', 'le', 'les', 'lo',
            'los', 'me', 'mi', 'mis', 'mucho', 'muchos', 'muy', 'ni', 'no', 'nos',
            'nosotras', 'nosotros', 'nuestra', 'nuestras', 'nuestro', 'nuestros',
            'o', 'otra', 'otras', 'otro', 'otros', 'para', 'pero', 'poco', 'por',
            'porque', 'que', 'qué', 'quien', 'quienes', 'se', 'sea', 'si', 'sí',
            'sido', 'sin', 'sobre', 'sois', 'somos', 'son', 'soy', 'su', 'sus',
            'suyo', 'suyos', 'también', 'tanto', 'te', 'teneis', 'tenemos', 'tener',
            'tengo', 'ti', 'tiene', 'tienen', 'todo', 'todos', 'tu', 'tus', 'tú',
            'un', 'una', 'uno', 'unos', 'vosotras', 'vosotros', 'vuestra',
            'vuestras', 'vuestro', 'vuestros', 'y', 'ya', 'yo'
        }
    
    def generar_datos_entrenamiento_base(self) -> pd.DataFrame:
        """
        Genera dataset base para entrenar el modelo
        """
        datos_entrenamiento = [
            # CONSULTA_DEUDA
            ("cuanto debo", "CONSULTA_DEUDA"),
            ("cuánto debo", "CONSULTA_DEUDA"),
            ("cual es mi deuda", "CONSULTA_DEUDA"),
            ("saldo pendiente", "CONSULTA_DEUDA"),
            ("mi saldo", "CONSULTA_DEUDA"),
            ("información de mi deuda", "CONSULTA_DEUDA"),
            ("estado de cuenta", "CONSULTA_DEUDA"),
            ("valor que debo", "CONSULTA_DEUDA"),
            ("monto pendiente", "CONSULTA_DEUDA"),
            ("cuánto es lo que debo", "CONSULTA_DEUDA"),
            
            # INTENCION_PAGO
            ("quiero pagar", "INTENCION_PAGO"),
            ("como puedo pagar", "INTENCION_PAGO"),
            ("opciones de pago", "INTENCION_PAGO"),
            ("voy a pagar", "INTENCION_PAGO"),
            ("quiero cancelar", "INTENCION_PAGO"),
            ("formas de pago", "INTENCION_PAGO"),
            ("abonar", "INTENCION_PAGO"),
            ("liquidar deuda", "INTENCION_PAGO"),
            ("pagar completo", "INTENCION_PAGO"),
            ("hacer el pago", "INTENCION_PAGO"),
            
            # SOLICITUD_PLAN
            ("plan de pagos", "SOLICITUD_PLAN"),
            ("cuotas", "SOLICITUD_PLAN"),
            ("facilidades de pago", "SOLICITUD_PLAN"),
            ("financiación", "SOLICITUD_PLAN"),
            ("arreglo de pago", "SOLICITUD_PLAN"),
            ("acuerdo", "SOLICITUD_PLAN"),
            ("negociar", "SOLICITUD_PLAN"),
            ("pagar en cuotas", "SOLICITUD_PLAN"),
            ("plan", "SOLICITUD_PLAN"),
            ("convenio", "SOLICITUD_PLAN"),
            
            # CONFIRMACION
            ("si", "CONFIRMACION"),
            ("sí", "CONFIRMACION"),
            ("acepto", "CONFIRMACION"),
            ("de acuerdo", "CONFIRMACION"),
            ("confirmo", "CONFIRMACION"),
            ("está bien", "CONFIRMACION"),
            ("perfecto", "CONFIRMACION"),
            ("entendido", "CONFIRMACION"),
            ("correcto", "CONFIRMACION"),
            ("vale", "CONFIRMACION"),
            
            # RECHAZO
            ("no", "RECHAZO"),
            ("no puedo", "RECHAZO"),
            ("imposible", "RECHAZO"),
            ("no tengo dinero", "RECHAZO"),
            ("no me interesa", "RECHAZO"),
            ("rechazó", "RECHAZO"),
            ("no acepto", "RECHAZO"),
            ("no quiero", "RECHAZO"),
            ("no voy a pagar", "RECHAZO"),
            ("no estoy de acuerdo", "RECHAZO"),
            
            # SOLICITUD_INFO
            ("información", "SOLICITUD_INFO"),
            ("detalles", "SOLICITUD_INFO"),
            ("explicación", "SOLICITUD_INFO"),
            ("más información", "SOLICITUD_INFO"),
            ("me puedes explicar", "SOLICITUD_INFO"),
            ("no entiendo", "SOLICITUD_INFO"),
            ("qué significa", "SOLICITUD_INFO"),
            ("por qué", "SOLICITUD_INFO"),
            ("cómo", "SOLICITUD_INFO"),
            ("ayuda", "SOLICITUD_INFO"),
            
            # IDENTIFICACION
            ("mi cedula es", "IDENTIFICACION"),
            ("documento", "IDENTIFICACION"),
            ("identificación", "IDENTIFICACION"),
            ("soy", "IDENTIFICACION"),
            ("mi número", "IDENTIFICACION"),
            ("cc", "IDENTIFICACION"),
            ("cédula", "IDENTIFICACION"),
            ("mi nombre es", "IDENTIFICACION"),
            ("me llamo", "IDENTIFICACION"),
            ("identificarme", "IDENTIFICACION"),
            
            # SELECCION_OPCION
            ("opción 1", "SELECCION_OPCION"),
            ("opción 2", "SELECCION_OPCION"),
            ("opción 3", "SELECCION_OPCION"),
            ("primera", "SELECCION_OPCION"),
            ("segunda", "SELECCION_OPCION"),
            ("tercera", "SELECCION_OPCION"),
            ("1", "SELECCION_OPCION"),
            ("2", "SELECCION_OPCION"),
            ("3", "SELECCION_OPCION"),
            ("elijo", "SELECCION_OPCION"),
            
            # SALUDO
            ("hola", "SALUDO"),
            ("buenos días", "SALUDO"),
            ("buenas tardes", "SALUDO"),
            ("buenas noches", "SALUDO"),
            ("saludos", "SALUDO"),
            ("buen día", "SALUDO"),
            ("qué tal", "SALUDO"),
            ("cómo está", "SALUDO"),
            ("muy buenas", "SALUDO"),
            ("buenas", "SALUDO"),
            
            # DESPEDIDA
            ("adiós", "DESPEDIDA"),
            ("hasta luego", "DESPEDIDA"),
            ("nos vemos", "DESPEDIDA"),
            ("chao", "DESPEDIDA"),
            ("bye", "DESPEDIDA"),
            ("hasta la vista", "DESPEDIDA"),
            ("que tenga buen día", "DESPEDIDA"),
            ("gracias", "DESPEDIDA"),
            ("muchas gracias", "DESPEDIDA"),
            ("hasta pronto", "DESPEDIDA")
        ]
        
        return pd.DataFrame(datos_entrenamiento, columns=['texto', 'intencion'])
    
    def cargar_datos_conversaciones_reales(self) -> pd.DataFrame:
        """
        Carga datos de conversaciones reales para entrenamiento
        """
        try:
            query = text("""
                SELECT 
                    m.text_content,
                    dt.intencion_real
                FROM message m
                JOIN datos_entrenamiento dt ON m.id = dt.mensaje_id
                WHERE dt.intencion_real IS NOT NULL
                AND dt.feedback_usuario = 'correcto'
                AND LEN(m.text_content) > 3
            """)
            
            result = self.db.execute(query)
            datos_reales = [(row[0], row[1]) for row in result]
            
            if datos_reales:
                return pd.DataFrame(datos_reales, columns=['texto', 'intencion'])
            
        except Exception as e:
            print(f"No se pudieron cargar datos reales: {e}")
        
        return pd.DataFrame(columns=['texto', 'intencion'])
    
    def preprocesar_texto(self, texto: str) -> str:
        """
        Preprocesa el texto para mejorar la clasificación
        """
        if not texto:
            return ""
        
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Eliminar caracteres especiales pero mantener espacios
        texto = re.sub(r'[^\w\s]', ' ', texto)
        
        # Eliminar números largos (cédulas, teléfonos) pero mantener números cortos
        texto = re.sub(r'\b\d{6,}\b', ' ', texto)
        
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    def entrenar_modelo(self) -> Dict:
        """
        Entrena el modelo de clasificación de intenciones
        """
        print("🤖 Iniciando entrenamiento del modelo...")
        
        # Combinar datos base con datos reales
        datos_base = self.generar_datos_entrenamiento_base()
        datos_reales = self.cargar_datos_conversaciones_reales()
        
        # Combinar datasets
        if not datos_reales.empty:
            datos_completos = pd.concat([datos_base, datos_reales], ignore_index=True)
            print(f"📊 Datos combinados: {len(datos_base)} base + {len(datos_reales)} reales")
        else:
            datos_completos = datos_base
            print(f"📊 Usando solo datos base: {len(datos_base)} ejemplos")
        
        # Preprocesar textos
        datos_completos['texto_procesado'] = datos_completos['texto'].apply(self.preprocesar_texto)
        
        # Eliminar filas vacías
        datos_completos = datos_completos[datos_completos['texto_procesado'].str.len() > 0]
        
        # Dividir en entrenamiento y prueba
        X = datos_completos['texto_procesado']
        y = datos_completos['intencion']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Crear pipeline con TF-IDF y Naive Bayes
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words=list(self.stop_words_es),
                min_df=1,
                max_df=0.8
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        # Entrenar
        self.pipeline.fit(X_train, y_train)
        
        # Evaluar
        y_pred = self.pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Guardar clases
        self.classes = list(self.pipeline.named_steps['classifier'].classes_)
        
        # Guardar modelo
        model_path = f"models/intention_classifier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
        joblib.dump(self.pipeline, model_path)
        
        print(f"✅ Modelo entrenado con accuracy: {accuracy:.3f}")
        print(f"💾 Modelo guardado en: {model_path}")
        
        # Registrar en base de datos
        self._registrar_modelo_entrenado(model_path, accuracy, len(datos_completos))
        
        return {
            "accuracy": accuracy,
            "clases": self.classes,
            "ejemplos_entrenamiento": len(datos_completos),
            "modelo_path": model_path
        }
    
    def cargar_modelo_entrenado(self, model_path: str = None):
        """
        Carga un modelo previamente entrenado
        """
        if not model_path:
            # Buscar el modelo más reciente
            try:
                query = text("""
                    SELECT TOP 1 ruta_modelo 
                    FROM modelos_ml 
                    WHERE activo = 1 
                    ORDER BY fecha_entrenamiento DESC
                """)
                result = self.db.execute(query).fetchone()
                if result:
                    model_path = result[0]
            except:
                pass
        
        if model_path:
            try:
                self.pipeline = joblib.load(model_path)
                self.classes = list(self.pipeline.named_steps['classifier'].classes_)
                print(f"✅ Modelo cargado desde: {model_path}")
                return True
            except Exception as e:
                print(f"❌ Error cargando modelo: {e}")
        
        return False
    
    def predecir_intencion(self, mensaje: str) -> Dict:
        """
        Predice la intención de un mensaje
        """
        if not self.pipeline:
            # Intentar cargar modelo
            if not self.cargar_modelo_entrenado():
                return {
                    "intencion": "DESCONOCIDA",
                    "confianza": 0.0,
                    "todas_probabilidades": {}
                }
        
        # Preprocesar mensaje
        mensaje_procesado = self.preprocesar_texto(mensaje)
        
        if not mensaje_procesado:
            return {
                "intencion": "DESCONOCIDA",
                "confianza": 0.0,
                "todas_probabilidades": {}
            }
        
        try:
            # Predecir probabilidades
            probabilidades = self.pipeline.predict_proba([mensaje_procesado])[0]
            
            # Obtener la intención con mayor probabilidad
            max_prob_idx = np.argmax(probabilidades)
            intencion_predicha = self.classes[max_prob_idx]
            confianza = probabilidades[max_prob_idx]
            
            # Crear diccionario con todas las probabilidades
            todas_probs = dict(zip(self.classes, probabilidades))
            
            # Si la confianza es muy baja, marcar como desconocida
            if confianza < self.confidence_threshold:
                intencion_predicha = "DESCONOCIDA"
            
            return {
                "intencion": intencion_predicha,
                "confianza": float(confianza),
                "todas_probabilidades": {k: float(v) for k, v in todas_probs.items()}
            }
        
        except Exception as e:
            print(f"❌ Error en predicción: {e}")
            return {
                "intencion": "DESCONOCIDA",
                "confianza": 0.0,
                "todas_probabilidades": {}
            }
    
    def _registrar_modelo_entrenado(self, ruta_modelo: str, accuracy: float, ejemplos: int):
        """
        Registra el modelo entrenado en la base de datos
        """
        try:
            # Crear tabla si no existe
            create_table = text("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'modelos_ml')
                BEGIN
                    CREATE TABLE modelos_ml (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nombre VARCHAR(100),
                        tipo VARCHAR(50),
                        ruta_modelo VARCHAR(255),
                        accuracy DECIMAL(5,4),
                        ejemplos_entrenamiento INT,
                        fecha_entrenamiento DATETIME2 DEFAULT GETDATE(),
                        activo BIT DEFAULT 1
                    )
                END
            """)
            self.db.execute(create_table)
            
            # Desactivar modelos anteriores
            update_query = text("UPDATE modelos_ml SET activo = 0 WHERE tipo = 'intention_classifier'")
            self.db.execute(update_query)
            
            # Insertar nuevo modelo
            insert_query = text("""
                INSERT INTO modelos_ml (nombre, tipo, ruta_modelo, accuracy, ejemplos_entrenamiento)
                VALUES (:nombre, :tipo, :ruta, :accuracy, :ejemplos)
            """)
            self.db.execute(insert_query, {
                "nombre": f"Clasificador_Intenciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "tipo": "intention_classifier",
                "ruta": ruta_modelo,
                "accuracy": accuracy,
                "ejemplos": ejemplos
            })
            
            self.db.commit()
            print("📝 Modelo registrado en base de datos")
            
        except Exception as e:
            print(f"⚠️ Error registrando modelo: {e}")
            self.db.rollback()
    
    def entrenar_automaticamente_con_feedback(self):
        """
        Reentrenamiento automático basado en feedback de usuarios
        """
        try:
            # Verificar si hay suficiente feedback nuevo
            query_feedback = text("""
                SELECT COUNT(*) 
                FROM datos_entrenamiento 
                WHERE fecha_registro > DATEADD(day, -7, GETDATE())
                AND feedback_usuario IS NOT NULL
            """)
            
            nuevo_feedback = self.db.execute(query_feedback).scalar()
            
            if nuevo_feedback >= 50:  # Threshold para reentrenamiento
                print(f"🔄 Iniciando reentrenamiento automático ({nuevo_feedback} nuevos ejemplos)")
                resultado = self.entrenar_modelo()
                
                # Notificar si hay mejora significativa
                if resultado["accuracy"] > 0.85:
                    print(f"🎉 Modelo mejorado! Nueva accuracy: {resultado['accuracy']:.3f}")
                
                return True
            else:
                print(f"ℹ️ Feedback insuficiente para reentrenamiento ({nuevo_feedback}/50)")
                return False
                
        except Exception as e:
            print(f"❌ Error en reentrenamiento automático: {e}")
            return False

# Ejemplo de uso en el sistema principal
class IntegradorML:
    """
    Integra el clasificador ML con el sistema principal
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.ml_classifier = MLIntentionClassifier(db_session)
        
        # Intentar cargar modelo existente
        if not self.ml_classifier.cargar_modelo_entrenado():
            print("🚀 No hay modelo entrenado. Entrenando modelo inicial...")
            self.ml_classifier.entrenar_modelo()
    
    def detectar_intencion_inteligente(self, mensaje: str, context_data: dict) -> dict:
        """
        Detecta intención usando ML + reglas de negocio
        """
        # Predicción ML
        resultado_ml = self.ml_classifier.predecir_intencion(mensaje)
        
        # Aplicar reglas de negocio específicas del contexto
        intencion_final = self._aplicar_reglas_contexto(resultado_ml, context_data, mensaje)
        
        return intencion_final
    
    def _aplicar_reglas_contexto(self, resultado_ml: dict, context_data: dict, mensaje: str) -> dict:
        """
        Aplica reglas de negocio basadas en el contexto
        """
        intencion = resultado_ml["intencion"]
        confianza = resultado_ml["confianza"]
        
        # Regla: Si no tiene datos del cliente y menciona documento, es IDENTIFICACION
        if not context_data.get("nombre_cliente") and re.search(r'\d{6,12}', mensaje):
            return {
                "intencion": "IDENTIFICACION",
                "confianza": 0.95,
                "metodo": "regla_contexto",
                "ml_original": resultado_ml
            }
        
        # Regla: Si ya tiene datos y pregunta cuánto debe, es CONSULTA_DEUDA
        if context_data.get("nombre_cliente") and any(palabra in mensaje.lower() for palabra in ["cuanto", "cuánto", "debo", "saldo"]):
            return {
                "intencion": "CONSULTA_DEUDA",
                "confianza": 0.90,
                "metodo": "regla_contexto",
                "ml_original": resultado_ml
            }
        
        # Si ML tiene alta confianza, usar resultado ML
        if confianza >= 0.8:
            resultado_ml["metodo"] = "ml_alta_confianza"
            return resultado_ml
        
        # Si ML tiene baja confianza, usar reglas adicionales
        resultado_ml["metodo"] = "ml_baja_confianza"
        resultado_ml["intencion"] = "SOLICITUD_INFO"  # Fallback seguro
        
        return resultado_ml