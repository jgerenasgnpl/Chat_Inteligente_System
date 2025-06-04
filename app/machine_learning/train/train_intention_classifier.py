import pandas as pd
import pyodbc
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from joblib import dump
import re
import string
import os
from datetime import datetime
import argparse

class EntrenadorML:
    def __init__(self, conexion_bd=None):
        """
        Inicializar el entrenador ML
        Args:
            conexion_bd: String de conexión a SQL Server
        """
        if conexion_bd:
            self.conn = pyodbc.connect(conexion_bd)
        else:

            self.conn = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};'
                'SERVER=172.18.79.20,1433;'
                'DATABASE=turnosvirtuales_dev;'
                'Trusted_Connection=yes'
            )
    
    def limpiar_texto(self, texto):
        """Limpiar y normalizar texto"""
        if not texto or pd.isna(texto):
            return ""
        
        texto = str(texto).lower()
        texto = re.sub(f"[{re.escape(string.punctuation)}]", "", texto)
        # Remover palabras que confundirian el modelo
        stopwords_es = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las'}
        palabras = [w for w in texto.split() if w not in stopwords_es and len(w) > 2]
        return " ".join(palabras)
    
    def cargar_desde_excel(self, ruta_excel):
        """
        Cargar datos de entrenamiento desde Excel
        Args:
            ruta_excel: Ruta al archivo Excel con datos de entrenamiento
        Returns:
            DataFrame con datos procesados
        """
        print(f"📂 Cargando datos desde: {ruta_excel}")
        
        try:
            # Leer Excel
            df = pd.read_excel(ruta_excel, sheet_name=0)
            
            # Validar columnas requeridas
            columnas_requeridas = ['texto_mensaje', 'intencion_real']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                raise ValueError(f"Faltan columnas: {columnas_faltantes}")
            
            # Limpiar datos
            df['texto_mensaje_limpio'] = df['texto_mensaje'].apply(self.limpiar_texto)
            df['contexto_adicional'] = df.get('contexto_adicional', '').fillna('').apply(self.limpiar_texto)
            
            # Crear texto completo para entrenamiento
            df['texto_completo'] = df['texto_mensaje_limpio'] + " " + df['contexto_adicional']
            
            # Remover duplicados y filas vacías
            df = df[df['texto_mensaje_limpio'].str.len() > 0]
            df = df.drop_duplicates(subset=['texto_completo'])
            
            print(f"✅ Datos cargados: {len(df)} ejemplos")
            print(f"📊 Intenciones encontradas: {df['intencion_real'].unique()}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error cargando Excel: {e}")
            raise
    
    def entrenar_modelo(self, df):
        """
        Entrenar el modelo ML
        Args:
            df: DataFrame con datos de entrenamiento
        Returns:
            Pipeline entrenado y métricas
        """
        print("🤖 Iniciando entrenamiento del modelo...")
        
        # Preparar datos
        X = df['texto_completo']
        y = df['intencion_real']
        
        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # pipeline
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words=None 
            )),
            ('clf', LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced'
            ))
        ])
        
        # Entrenar
        pipeline.fit(X_train, y_train)
        
        # Evaluar
        y_pred = pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ Entrenamiento completado")
        print(f"🎯 Accuracy: {accuracy:.3f}")
        print("📊 Reporte detallado:")
        print(classification_report(y_test, y_pred))
        
        return pipeline, accuracy, len(df)
    
    def probar_modelo(self, pipeline):
        """Probar el modelo con ejemplos"""
        ejemplos_prueba = [
            "cuanto debo",
            "hacer un acuerdo", 
            "no puedo pagar",
            "1020428633",
            "hola buenos dias",
            "gracias por la ayuda",
            "me interesa el plan"
        ]
        
        print("\n === PRUEBAS DEL MODELO ===")
        for ejemplo in ejemplos_prueba:
            ejemplo_limpio = self.limpiar_texto(ejemplo)
            prediccion = pipeline.predict([ejemplo_limpio])[0]
            probabilidades = pipeline.predict_proba([ejemplo_limpio])[0]
            confianza = max(probabilidades)
            
            print(f"'{ejemplo}' → {prediccion} (confianza: {confianza:.2f})")
    
    def guardar_modelo(self, pipeline, accuracy, ejemplos_entrenamiento, ruta_modelo="models/intention_classifier.joblib"):
        """
        Guardar modelo entrenado
        Args:
            pipeline: Modelo entrenado
            accuracy: Precisión del modelo
            ejemplos_entrenamiento: Número de ejemplos usados
            ruta_modelo: Ruta donde guardar el modelo
        """
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)
        
        # Guardar
        dump(pipeline, ruta_modelo)
        print(f"💾 Modelo guardado en: {ruta_modelo}")
        
        # Registrar en BD
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO dbo.modelos_ml 
                (nombre, tipo, ruta_modelo, accuracy, ejemplos_entrenamiento, fecha_entrenamiento, activo)
                VALUES (?, ?, ?, ?, ?, GETDATE(), 1)
            """, 
                'Modelo_Intenciones_Excel',
                'Clasificador_TF-IDF_LogReg', 
                ruta_modelo, 
                accuracy, 
                ejemplos_entrenamiento
            )
            self.conn.commit()
            print("✅ Modelo registrado en base de datos")
            
        except Exception as e:
            print(f"⚠️ Error registrando en BD: {e}")
    
    def cargar_estados_desde_excel(self, ruta_excel):
        """
        Cargar configuración de estados desde Excel
        Args:
            ruta_excel: Ruta al archivo Excel con estados
        """
        print(f"📂 Cargando estados desde: {ruta_excel}")
        
        try:
            df_estados = pd.read_excel(ruta_excel, sheet_name=0)
            
            # Validar
            columnas_requeridas = ['nombre', 'mensaje_template']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df_estados.columns]
            
            if columnas_faltantes:
                raise ValueError(f"Faltan columnas en estados: {columnas_faltantes}")
            
            # Insertar/actualizar estados en BD
            cursor = self.conn.cursor()
            
            for _, row in df_estados.iterrows():
                cursor.execute("""
                    MERGE Estados_Conversacion AS target
                    USING (VALUES (?, ?, ?, ?, ?, ?, ?)) AS source 
                        (nombre, mensaje_template, accion, condicion, estado_siguiente_true, estado_siguiente_false, estado_siguiente_default)
                    ON target.nombre = source.nombre
                    WHEN MATCHED THEN
                        UPDATE SET 
                            mensaje_template = source.mensaje_template,
                            accion = source.accion,
                            condicion = source.condicion,
                            estado_siguiente_true = source.estado_siguiente_true,
                            estado_siguiente_false = source.estado_siguiente_false,
                            estado_siguiente_default = source.estado_siguiente_default
                    WHEN NOT MATCHED THEN
                        INSERT (nombre, mensaje_template, accion, condicion, estado_siguiente_true, estado_siguiente_false, estado_siguiente_default, activo)
                        VALUES (source.nombre, source.mensaje_template, source.accion, source.condicion, 
                               source.estado_siguiente_true, source.estado_siguiente_false, source.estado_siguiente_default, 1);
                """, 
                    row['nombre'],
                    row['mensaje_template'],
                    row.get('accion'),
                    row.get('condicion'),
                    row.get('estado_sig_true'),
                    row.get('estado_sig_false'),
                    row.get('estado_sig_default')
                )
            
            self.conn.commit()
            print(f"✅ {len(df_estados)} estados cargados/actualizados")
            
        except Exception as e:
            print(f"❌ Error cargando estados: {e}")
            raise
    
    def ejecutar_entrenamiento_completo(self, ruta_datos_excel, ruta_estados_excel=None):
        """
        Ejecutar proceso completo de entrenamiento
        Args:
            ruta_datos_excel: Excel con datos de entrenamiento
            ruta_estados_excel: Excel con estados (opcional)
        """
        print("🚀 === INICIANDO ENTRENAMIENTO COMPLETO ===")
        
        try:
            # 1. Cargar estados
            if ruta_estados_excel and os.path.exists(ruta_estados_excel):
                self.cargar_estados_desde_excel(ruta_estados_excel)
            
            # Cargar datos
            df = self.cargar_desde_excel(ruta_datos_excel)
            
            # Entrenar
            pipeline, accuracy, ejemplos = self.entrenar_modelo(df)
            
            # Probar
            self.probar_modelo(pipeline)
            
            # 5. Guardar
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_modelo = f"models/intention_classifier_{timestamp}.joblib"
            self.guardar_modelo(pipeline, accuracy, ejemplos, ruta_modelo)
            
            print(" === ENTRENAMIENTO COMPLETADO EXITOSAMENTE ===")
            return True
            
        except Exception as e:
            print(f"❌ Error en entrenamiento: {e}")
            return False
        
        finally:
            if hasattr(self, 'conn'):
                self.conn.close()

# ejecución del modelo
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Entrenar modelo ML desde Excel')
    parser.add_argument('--datos', required=True, help='Ruta al Excel con datos de entrenamiento')
    parser.add_argument('--estados', help='Ruta al Excel con estados (opcional)')
    parser.add_argument('--conexion', help='String de conexión BD (opcional)')
    
    args = parser.parse_args()
    
    # Entrenador
    entrenador = EntrenadorML(args.conexion)
    
    # Ejecutar
    exito = entrenador.ejecutar_entrenamiento_completo(
        ruta_datos_excel=args.datos,
        ruta_estados_excel=args.estados
    )
    
    if exito:
        print("✅ Proceso completado exitosamente")
    else:
        print("❌ Proceso falló")