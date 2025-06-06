import pandas as pd
import numpy as np
import pyodbc
import os
import sys
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
from joblib import dump
import re
import string
from datetime import datetime
import argparse

class EntrenadorMLCorregido:
    """
    Entrenador ML corregido con auto-generación de datos y rutas flexibles
    """
    
    def __init__(self):
        """Inicializar entrenador con configuración automática"""
        self.proyecto_dir = self._detectar_directorio_proyecto()
        self.data_dir = os.path.join(self.proyecto_dir, "data", "training")
        self.models_dir = os.path.join(self.proyecto_dir, "models")
        
        # Crear directorios si no existen
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.models_dir, exist_ok=True)
        
        print(f"📁 Directorio proyecto: {self.proyecto_dir}")
        print(f"📁 Directorio datos: {self.data_dir}")
        print(f"📁 Directorio modelos: {self.models_dir}")
        
        self.conn = None
        self._inicializar_conexion_bd()
    
    def _detectar_directorio_proyecto(self):
        """Detecta automáticamente el directorio del proyecto"""
        # Obtener directorio actual y buscar hacia arriba
        current_dir = os.getcwd()
        
        # Buscar indicadores del proyecto
        indicadores = ['main.py', 'app', 'requirements.txt']
        
        # Verificar directorio actual
        for indicador in indicadores:
            if os.path.exists(os.path.join(current_dir, indicador)):
                print(f"✅ Proyecto detectado en: {current_dir}")
                return current_dir
        
        # Buscar en directorios padre
        parent = os.path.dirname(current_dir)
        while parent != current_dir:  # Evitar bucle infinito
            for indicador in indicadores:
                if os.path.exists(os.path.join(parent, indicador)):
                    print(f"✅ Proyecto detectado en directorio padre: {parent}")
                    return parent
            current_dir = parent
            parent = os.path.dirname(current_dir)
        
        # Si no encuentra, usar directorio actual
        print(f"⚠️ Usando directorio actual como proyecto: {os.getcwd()}")
        return os.getcwd()
    
    def _inicializar_conexion_bd(self):
        """Inicializar conexión a base de datos"""
        try:
            self.conn = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};'
                'SERVER=172.18.79.20,1433;'
                'DATABASE=turnosvirtuales_dev;'
                'Trusted_Connection=yes'
            )
            print("✅ Conexión a BD establecida")
        except Exception as e:
            print(f"❌ Error conectando a BD: {e}")
            print("⚠️ Continuando sin conexión BD - usará datos por defecto")
    
    def generar_datos_entrenamiento_excel(self):
        """
        Genera archivo Excel con datos de entrenamiento para cobranza
        """
        archivo_datos = os.path.join(self.data_dir, "datos_entrenamiento.xlsx")
        
        print(f"📝 Generando datos de entrenamiento en: {archivo_datos}")
        
        # Datos de entrenamiento específicos para cobranza
        datos = [
            # CONSULTA_DEUDA
            ("cuanto debo", "CONSULTA_DEUDA", "Cliente pregunta por su deuda"),
            ("cuánto debo", "CONSULTA_DEUDA", "Cliente pregunta por su deuda"),
            ("cual es mi deuda", "CONSULTA_DEUDA", "Cliente pregunta por su deuda"),
            ("saldo pendiente", "CONSULTA_DEUDA", "Cliente pregunta por saldo"),
            ("mi saldo", "CONSULTA_DEUDA", "Cliente consulta saldo"),
            ("información de mi deuda", "CONSULTA_DEUDA", "Cliente solicita información"),
            ("estado de cuenta", "CONSULTA_DEUDA", "Cliente pide estado de cuenta"),
            ("valor que debo", "CONSULTA_DEUDA", "Cliente pregunta valor"),
            ("monto pendiente", "CONSULTA_DEUDA", "Cliente consulta monto"),
            ("cuánto es lo que debo", "CONSULTA_DEUDA", "Cliente pregunta deuda"),
            ("me pueden decir cuanto debo", "CONSULTA_DEUDA", "Cliente solicita información"),
            ("necesito saber mi deuda", "CONSULTA_DEUDA", "Cliente necesita información"),
            
            # INTENCION_PAGO
            ("quiero pagar", "INTENCION_PAGO", "Cliente expresa intención de pagar"),
            ("como puedo pagar", "INTENCION_PAGO", "Cliente pregunta forma de pago"),
            ("opciones de pago", "INTENCION_PAGO", "Cliente solicita opciones"),
            ("voy a pagar", "INTENCION_PAGO", "Cliente confirma intención"),
            ("quiero cancelar", "INTENCION_PAGO", "Cliente quiere cancelar deuda"),
            ("formas de pago", "INTENCION_PAGO", "Cliente pregunta formas"),
            ("abonar", "INTENCION_PAGO", "Cliente quiere abonar"),
            ("liquidar deuda", "INTENCION_PAGO", "Cliente quiere liquidar"),
            ("pagar completo", "INTENCION_PAGO", "Cliente quiere pago total"),
            ("hacer el pago", "INTENCION_PAGO", "Cliente quiere hacer pago"),
            ("realizar pago", "INTENCION_PAGO", "Cliente quiere realizar pago"),
            ("efectuar pago", "INTENCION_PAGO", "Cliente quiere efectuar pago"),
            
            # SOLICITUD_PLAN
            ("plan de pagos", "SOLICITUD_PLAN", "Cliente solicita plan"),
            ("cuotas", "SOLICITUD_PLAN", "Cliente pregunta por cuotas"),
            ("facilidades de pago", "SOLICITUD_PLAN", "Cliente solicita facilidades"),
            ("financiación", "SOLICITUD_PLAN", "Cliente solicita financiación"),
            ("arreglo de pago", "SOLICITUD_PLAN", "Cliente solicita arreglo"),
            ("acuerdo", "SOLICITUD_PLAN", "Cliente busca acuerdo"),
            ("negociar", "SOLICITUD_PLAN", "Cliente quiere negociar"),
            ("pagar en cuotas", "SOLICITUD_PLAN", "Cliente quiere cuotas"),
            ("plan", "SOLICITUD_PLAN", "Cliente solicita plan"),
            ("convenio", "SOLICITUD_PLAN", "Cliente busca convenio"),
            ("descuento", "SOLICITUD_PLAN", "Cliente solicita descuento"),
            ("rebaja", "SOLICITUD_PLAN", "Cliente solicita rebaja"),
            
            # CONFIRMACION
            ("si", "CONFIRMACION", "Cliente confirma"),
            ("sí", "CONFIRMACION", "Cliente confirma"),
            ("acepto", "CONFIRMACION", "Cliente acepta"),
            ("de acuerdo", "CONFIRMACION", "Cliente está de acuerdo"),
            ("confirmo", "CONFIRMACION", "Cliente confirma"),
            ("está bien", "CONFIRMACION", "Cliente acepta"),
            ("perfecto", "CONFIRMACION", "Cliente está conforme"),
            ("entendido", "CONFIRMACION", "Cliente entiende"),
            ("correcto", "CONFIRMACION", "Cliente confirma"),
            ("vale", "CONFIRMACION", "Cliente acepta"),
            ("ok", "CONFIRMACION", "Cliente acepta"),
            ("bueno", "CONFIRMACION", "Cliente acepta"),
            
            # RECHAZO
            ("no", "RECHAZO", "Cliente rechaza"),
            ("no puedo", "RECHAZO", "Cliente no puede"),
            ("imposible", "RECHAZO", "Cliente dice que es imposible"),
            ("no tengo dinero", "RECHAZO", "Cliente no tiene recursos"),
            ("no me interesa", "RECHAZO", "Cliente no está interesado"),
            ("rechazo", "RECHAZO", "Cliente rechaza"),
            ("no acepto", "RECHAZO", "Cliente no acepta"),
            ("no quiero", "RECHAZO", "Cliente no quiere"),
            ("no voy a pagar", "RECHAZO", "Cliente se rehúsa"),
            ("no estoy de acuerdo", "RECHAZO", "Cliente no está de acuerdo"),
            ("no me conviene", "RECHAZO", "Cliente dice que no conviene"),
            ("muy caro", "RECHAZO", "Cliente considera caro"),
            
            # SOLICITUD_INFO
            ("información", "SOLICITUD_INFO", "Cliente solicita información"),
            ("detalles", "SOLICITUD_INFO", "Cliente solicita detalles"),
            ("explicación", "SOLICITUD_INFO", "Cliente solicita explicación"),
            ("más información", "SOLICITUD_INFO", "Cliente solicita más info"),
            ("me puedes explicar", "SOLICITUD_INFO", "Cliente solicita explicación"),
            ("no entiendo", "SOLICITUD_INFO", "Cliente no entiende"),
            ("qué significa", "SOLICITUD_INFO", "Cliente pregunta significado"),
            ("por qué", "SOLICITUD_INFO", "Cliente pregunta razón"),
            ("cómo", "SOLICITUD_INFO", "Cliente pregunta cómo"),
            ("ayuda", "SOLICITUD_INFO", "Cliente solicita ayuda"),
            ("explique mejor", "SOLICITUD_INFO", "Cliente solicita mejor explicación"),
            ("no comprendo", "SOLICITUD_INFO", "Cliente no comprende"),
            
            # IDENTIFICACION
            ("mi cedula es", "IDENTIFICACION", "Cliente proporciona cédula"),
            ("documento", "IDENTIFICACION", "Cliente menciona documento"),
            ("identificación", "IDENTIFICACION", "Cliente menciona identificación"),
            ("soy", "IDENTIFICACION", "Cliente se identifica"),
            ("mi número", "IDENTIFICACION", "Cliente proporciona número"),
            ("cc", "IDENTIFICACION", "Cliente menciona CC"),
            ("cédula", "IDENTIFICACION", "Cliente menciona cédula"),
            ("mi nombre es", "IDENTIFICACION", "Cliente dice su nombre"),
            ("me llamo", "IDENTIFICACION", "Cliente dice su nombre"),
            ("identificarme", "IDENTIFICACION", "Cliente quiere identificarse"),
            ("1020428633", "IDENTIFICACION", "Ejemplo de cédula"),
            ("12345678", "IDENTIFICACION", "Ejemplo de documento"),
            
            # SELECCION_OPCION
            ("opción 1", "SELECCION_OPCION", "Cliente selecciona opción"),
            ("opción 2", "SELECCION_OPCION", "Cliente selecciona opción"),
            ("opción 3", "SELECCION_OPCION", "Cliente selecciona opción"),
            ("primera", "SELECCION_OPCION", "Cliente selecciona primera"),
            ("segunda", "SELECCION_OPCION", "Cliente selecciona segunda"),
            ("tercera", "SELECCION_OPCION", "Cliente selecciona tercera"),
            ("1", "SELECCION_OPCION", "Cliente selecciona 1"),
            ("2", "SELECCION_OPCION", "Cliente selecciona 2"),
            ("3", "SELECCION_OPCION", "Cliente selecciona 3"),
            ("elijo", "SELECCION_OPCION", "Cliente elige"),
            ("escojo", "SELECCION_OPCION", "Cliente escoge"),
            ("prefiero", "SELECCION_OPCION", "Cliente prefiere"),
            
            # SALUDO
            ("hola", "SALUDO", "Cliente saluda"),
            ("buenos días", "SALUDO", "Cliente saluda"),
            ("buenas tardes", "SALUDO", "Cliente saluda"),
            ("buenas noches", "SALUDO", "Cliente saluda"),
            ("saludos", "SALUDO", "Cliente saluda"),
            ("buen día", "SALUDO", "Cliente saluda"),
            ("qué tal", "SALUDO", "Cliente saluda"),
            ("cómo está", "SALUDO", "Cliente pregunta como está"),
            ("muy buenas", "SALUDO", "Cliente saluda"),
            ("buenas", "SALUDO", "Cliente saluda"),
            ("hey", "SALUDO", "Cliente saluda informal"),
            ("holi", "SALUDO", "Cliente saluda informal"),
            
            # DESPEDIDA
            ("adiós", "DESPEDIDA", "Cliente se despide"),
            ("hasta luego", "DESPEDIDA", "Cliente se despide"),
            ("nos vemos", "DESPEDIDA", "Cliente se despide"),
            ("chao", "DESPEDIDA", "Cliente se despide"),
            ("bye", "DESPEDIDA", "Cliente se despide"),
            ("hasta la vista", "DESPEDIDA", "Cliente se despide"),
            ("que tenga buen día", "DESPEDIDA", "Cliente se despide"),
            ("gracias", "DESPEDIDA", "Cliente agradece"),
            ("muchas gracias", "DESPEDIDA", "Cliente agradece"),
            ("hasta pronto", "DESPEDIDA", "Cliente se despide"),
            ("buen día", "DESPEDIDA", "Cliente se despide"),
            ("que esté bien", "DESPEDIDA", "Cliente se despide")
        ]
        
        # Crear DataFrame
        df = pd.DataFrame(datos, columns=['texto_mensaje', 'intencion_real', 'contexto_adicional'])
        
        # Guardar en Excel
        df.to_excel(archivo_datos, index=False)
        
        print(f"✅ Archivo de datos generado: {len(datos)} ejemplos")
        print(f"📊 Distribución por intención:")
        distribucion = df['intencion_real'].value_counts()
        for intencion, count in distribucion.items():
            print(f"   {intencion}: {count} ejemplos")
        
        return archivo_datos
    
    def generar_estados_conversacion_excel(self):
        """
        Genera archivo Excel con estados de conversación
        """
        archivo_estados = os.path.join(self.data_dir, "estados_conversacion.xlsx")
        
        print(f"📝 Generando estados de conversación en: {archivo_estados}")
        
        # Estados de conversación para cobranza
        estados = [
            {
                'nombre': 'validar_documento',
                'mensaje_template': '¡Hola! Soy tu asistente de Systemgroup. Para ayudarte mejor, ¿podrías proporcionarme tu número de cédula?',
                'accion': 'validar_documento',
                'condicion': 'tiene_documento_valido',
                'estado_sig_true': 'informar_deuda',
                'estado_sig_false': 'validar_documento',
                'estado_sig_default': 'informar_deuda'
            },
            {
                'nombre': 'informar_deuda',
                'mensaje_template': 'Hola {{nombre_cliente}}, encontré tu información. Tu saldo actual con {{banco}} es de {{saldo_total}}. ¿Te gustaría conocer las opciones de pago disponibles?',
                'accion': 'consultar_base_datos',
                'condicion': 'cliente_acepta',
                'estado_sig_true': 'proponer_planes_pago',
                'estado_sig_false': 'evaluar_intencion_pago',
                'estado_sig_default': 'proponer_planes_pago'
            },
            {
                'nombre': 'proponer_planes_pago',
                'mensaje_template': 'Te ofrezco estas opciones: 1️⃣ Pago único de {{oferta_2}} con descuento 2️⃣ Plan en cuotas desde {{hasta_3_cuotas}}. ¿Cuál te interesa?',
                'accion': 'crear_planes_pago',
                'condicion': 'cliente_selecciona_plan',
                'estado_sig_true': 'generar_acuerdo',
                'estado_sig_false': 'gestionar_objecion',
                'estado_sig_default': 'seleccionar_plan'
            },
            {
                'nombre': 'seleccionar_plan',
                'mensaje_template': 'Has elegido un plan de pago. ¿Confirmas tu selección?',
                'accion': None,
                'condicion': 'cliente_acepta',
                'estado_sig_true': 'generar_acuerdo',
                'estado_sig_false': 'proponer_planes_pago',
                'estado_sig_default': 'generar_acuerdo'
            },
            {
                'nombre': 'evaluar_intencion_pago',
                'mensaje_template': '¿Está interesado en realizar un acuerdo de pago?',
                'accion': None,
                'condicion': 'cliente_acepta',
                'estado_sig_true': 'proponer_planes_pago',
                'estado_sig_false': 'gestionar_objecion',
                'estado_sig_default': 'proponer_planes_pago'
            },
            {
                'nombre': 'gestionar_objecion',
                'mensaje_template': 'Entiendo tu situación. ¿Te gustaría que exploremos otras alternativas flexibles?',
                'accion': None,
                'condicion': 'cliente_acepta',
                'estado_sig_true': 'proponer_planes_pago',
                'estado_sig_false': 'finalizar_conversacion',
                'estado_sig_default': 'proponer_planes_pago'
            },
            {
                'nombre': 'generar_acuerdo',
                'mensaje_template': '¡Excelente! Voy a generar tu acuerdo de pago. Te enviaré los detalles completos.',
                'accion': 'registrar_plan_pago',
                'condicion': None,
                'estado_sig_true': 'finalizar_conversacion',
                'estado_sig_false': 'finalizar_conversacion',
                'estado_sig_default': 'finalizar_conversacion'
            },
            {
                'nombre': 'cliente_no_encontrado',
                'mensaje_template': 'No encontré información para ese documento. Por favor verifica el número o contacta al 123-456-7890.',
                'accion': None,
                'condicion': None,
                'estado_sig_true': 'validar_documento',
                'estado_sig_false': 'validar_documento',
                'estado_sig_default': 'validar_documento'
            },
            {
                'nombre': 'finalizar_conversacion',
                'mensaje_template': 'Perfecto. Hemos completado tu proceso de negociación. ¡Gracias por confiar en nosotros!',
                'accion': None,
                'condicion': None,
                'estado_sig_true': None,
                'estado_sig_false': None,
                'estado_sig_default': None
            }
        ]
        
        # Crear DataFrame
        df_estados = pd.DataFrame(estados)
        
        # Guardar en Excel
        df_estados.to_excel(archivo_estados, index=False)
        
        print(f"✅ Archivo de estados generado: {len(estados)} estados")
        
        return archivo_estados
    
    def limpiar_texto(self, texto):
        """Limpiar y normalizar texto para ML"""
        if not texto or pd.isna(texto):
            return ""
        
        texto = str(texto).lower()
        texto = re.sub(f"[{re.escape(string.punctuation)}]", "", texto)
        
        # Stopwords básicas en español
        stopwords_es = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las'}
        palabras = [w for w in texto.split() if w not in stopwords_es and len(w) > 2]
        return " ".join(palabras)
    
    def entrenar_modelo_automatico(self, archivo_datos=None, archivo_estados=None):
        """
        Entrenamiento automático con generación de datos si no existen
        """
        print("🚀 === INICIANDO ENTRENAMIENTO AUTOMÁTICO ===")
        
        # Generar archivos si no se proporcionan
        if not archivo_datos:
            archivo_datos = self.generar_datos_entrenamiento_excel()
        
        if not archivo_estados:
            archivo_estados = self.generar_estados_conversacion_excel()
        
        # Verificar que existen los archivos
        if not os.path.exists(archivo_datos):
            raise FileNotFoundError(f"Archivo de datos no encontrado: {archivo_datos}")
        
        try:
            # 1. Cargar datos
            print(f"📂 Cargando datos desde: {archivo_datos}")
            df = pd.read_excel(archivo_datos)
            
            print(f"✅ Datos cargados: {len(df)} ejemplos")
            print(f"📊 Columnas: {list(df.columns)}")
            
            # 2. Verificar columnas requeridas
            if 'texto_mensaje' not in df.columns or 'intencion_real' not in df.columns:
                raise ValueError("El archivo debe tener columnas 'texto_mensaje' e 'intencion_real'")
            
            # 3. Limpiar datos
            print("🧹 Limpiando datos...")
            df['texto_limpio'] = df['texto_mensaje'].apply(self.limpiar_texto)
            df = df[df['texto_limpio'].str.len() > 0]  # Remover filas vacías
            df = df.drop_duplicates(subset=['texto_limpio'])  # Remover duplicados
            
            print(f"✅ Datos limpiados: {len(df)} ejemplos únicos")
            
            # 4. Preparar datos para entrenamiento
            X = df['texto_limpio']
            y = df['intencion_real']
            
            print(f"📊 Distribución de intenciones:")
            for intencion, count in y.value_counts().items():
                print(f"   {intencion}: {count}")
            
            # 5. Dividir datos
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # 6. Crear pipeline
            print("🤖 Creando pipeline ML...")
            pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=5000,
                    ngram_range=(1, 2),
                    stop_words=None,
                    min_df=1,
                    max_df=0.8
                )),
                ('clf', LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                    class_weight='balanced'
                ))
            ])
            
            # 7. Entrenar
            print("🎯 Entrenando modelo...")
            pipeline.fit(X_train, y_train)
            
            # 8. Evaluar
            print("📊 Evaluando modelo...")
            y_pred = pipeline.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            print(f"✅ Entrenamiento completado!")
            print(f"🎯 Accuracy: {accuracy:.3f}")
            print("\n📊 Reporte detallado:")
            print(classification_report(y_test, y_pred))
            
            # 9. Probar con ejemplos
            self._probar_modelo(pipeline)
            
            # 10. Guardar modelo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            modelo_path = os.path.join(self.models_dir, f"intention_classifier_{timestamp}.joblib")
            
            dump(pipeline, modelo_path)
            print(f"💾 Modelo guardado: {modelo_path}")
            
            # 11. Registrar en BD si hay conexión
            if self.conn:
                self._registrar_modelo_bd(modelo_path, accuracy, len(df))
            
            # 12. Cargar estados si están disponibles
            if os.path.exists(archivo_estados):
                self._cargar_estados_bd(archivo_estados)
            
            print("\n🎉 ¡ENTRENAMIENTO COMPLETADO EXITOSAMENTE!")
            print(f"📈 Accuracy: {accuracy:.1%}")
            print(f"💾 Modelo: {modelo_path}")
            
            return {
                "success": True,
                "accuracy": accuracy,
                "modelo_path": modelo_path,
                "ejemplos": len(df)
            }
            
        except Exception as e:
            print(f"❌ Error durante entrenamiento: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _probar_modelo(self, pipeline):
        """Probar modelo con ejemplos"""
        ejemplos_prueba = [
            "cuanto debo",
            "quiero hacer un pago", 
            "no puedo pagar",
            "1020428633",
            "hola buenos dias",
            "gracias",
            "plan de cuotas",
            "acepto la propuesta",
            "no me interesa"
        ]
        
        print("\n🧪 === PRUEBAS DEL MODELO ===")
        for ejemplo in ejemplos_prueba:
            ejemplo_limpio = self.limpiar_texto(ejemplo)
            if ejemplo_limpio:  # Solo si hay texto después de limpiar
                prediccion = pipeline.predict([ejemplo_limpio])[0]
                probabilidades = pipeline.predict_proba([ejemplo_limpio])[0]
                confianza = max(probabilidades)
                
                print(f"'{ejemplo}' → {prediccion} (confianza: {confianza:.2f})")
    
    def _registrar_modelo_bd(self, modelo_path, accuracy, ejemplos):
        """Registrar modelo en base de datos"""
        try:
            cursor = self.conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute("""
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
            
            # Desactivar modelos anteriores
            cursor.execute("UPDATE modelos_ml SET activo = 0 WHERE tipo = 'intention_classifier'")
            
            # Insertar nuevo modelo
            cursor.execute("""
                INSERT INTO modelos_ml (nombre, tipo, ruta_modelo, accuracy, ejemplos_entrenamiento)
                VALUES (?, ?, ?, ?, ?)
            """, 
                f'Modelo_Auto_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'intention_classifier', 
                modelo_path, 
                accuracy, 
                ejemplos
            )
            
            self.conn.commit()
            print("✅ Modelo registrado en BD")
            
        except Exception as e:
            print(f"⚠️ Error registrando modelo en BD: {e}")
    
    def _cargar_estados_bd(self, archivo_estados):
        """Cargar estados en base de datos"""
        if not self.conn:
            print("⚠️ Sin conexión BD, saltando carga de estados")
            return
        
        try:
            print(f"📊 Cargando estados desde: {archivo_estados}")
            df_estados = pd.read_excel(archivo_estados)
            
            cursor = self.conn.cursor()
            
            for _, row in df_estados.iterrows():
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM Estados_Conversacion WHERE nombre = ?)
                    BEGIN
                        INSERT INTO Estados_Conversacion 
                        (nombre, mensaje_template, accion, condicion, 
                         estado_siguiente_true, estado_siguiente_false, estado_siguiente_default, activo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    END
                    ELSE
                    BEGIN
                        UPDATE Estados_Conversacion 
                        SET mensaje_template = ?, accion = ?, condicion = ?,
                            estado_siguiente_true = ?, estado_siguiente_false = ?, estado_siguiente_default = ?
                        WHERE nombre = ?
                    END
                """, 
                    row['nombre'],  # Para el EXISTS
                    row['nombre'], row['mensaje_template'], row.get('accion'), row.get('condicion'),
                    row.get('estado_sig_true'), row.get('estado_sig_false'), row.get('estado_sig_default'),
                    # Para el UPDATE
                    row['mensaje_template'], row.get('accion'), row.get('condicion'),
                    row.get('estado_sig_true'), row.get('estado_sig_false'), row.get('estado_sig_default'),
                    row['nombre']
                )
            
            self.conn.commit()
            print(f"✅ {len(df_estados)} estados cargados/actualizados en BD")
            
        except Exception as e:
            print(f"❌ Error cargando estados: {e}")

def main():
    """Función principal mejorada"""
    parser = argparse.ArgumentParser(description='Entrenador ML Automatizado para Cobranza')
    parser.add_argument('--datos', help='Ruta al Excel con datos (opcional - se generará automáticamente)')
    parser.add_argument('--estados', help='Ruta al Excel con estados (opcional - se generará automáticamente)')
    parser.add_argument('--auto', action='store_true', help='Modo automático - genera todos los archivos')
    
    args = parser.parse_args()
    
    print("🤖 === ENTRENADOR ML AUTOMATIZADO ===")
    print("Para sistema de cobranza y negociación")
    print("="*50)
    
    # Crear entrenador
    entrenador = EntrenadorMLCorregido()
    
    if args.auto or (not args.datos and not args.estados):
        print("🚀 Modo automático activado - generando archivos y entrenando...")
        resultado = entrenador.entrenar_modelo_automatico()
    else:
        print("📂 Usando archivos especificados...")
        resultado = entrenador.entrenar_modelo_automatico(args.datos, args.estados)
    
    if resultado["success"]:
        print(f"\n🎉 ¡ENTRENAMIENTO EXITOSO!")
        print(f"📈 Accuracy: {resultado['accuracy']:.1%}")
        print(f"💾 Modelo guardado en: {resultado['modelo_path']}")
        print(f"📊 Ejemplos entrenados: {resultado['ejemplos']}")
        print(f"\n✅ Para usar el modelo, ejecuta:")
        print(f"python main.py")
    else:
        print(f"\n❌ Entrenamiento falló: {resultado['error']}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())