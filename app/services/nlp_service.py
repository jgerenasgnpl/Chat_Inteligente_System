import re
import string
from collections import Counter
from typing import Dict, List, Any, Set
from sqlalchemy import text
from sqlalchemy.orm import Session

class SimpleNLPService:
    def __init__(self):
        # Lista básica de stopwords en español (sin necesidad de descargar)
        self.stop_words = {
            'a', 'al', 'algo', 'algunas', 'algunos', 'ante', 'antes', 'como', 'con', 
            'contra', 'cual', 'cuando', 'de', 'del', 'desde', 'donde', 'durante', 'e',
            'el', 'ella', 'ellas', 'ellos', 'en', 'entre', 'era', 'eres', 'es', 'esa', 
            'ese', 'eso', 'esta', 'estas', 'este', 'esto', 'estos', 'ha', 'ha', 'había',
            'han', 'has', 'hasta', 'he', 'la', 'las', 'le', 'les', 'lo', 'los', 'me', 
            'mi', 'mis', 'mucho', 'muchos', 'muy', 'ni', 'no', 'nos', 'nosotras', 
            'nosotros', 'nuestra', 'nuestras', 'nuestro', 'nuestros', 'o', 'otra', 
            'otras', 'otro', 'otros', 'para', 'pero', 'poco', 'por', 'porque', 'que', 
            'qué', 'quien', 'quienes', 'se', 'sea', 'si', 'sí', 'sido', 'sin', 'sobre', 
            'sois', 'somos', 'son', 'soy', 'su', 'sus', 'suyo', 'suyos', 'también', 
            'tanto', 'te', 'teneis', 'tenemos', 'tener', 'tengo', 'ti', 'tiene', 'tienen',
            'todo', 'todos', 'tu', 'tus', 'tú', 'un', 'una', 'uno', 'unos', 'vosotras',
            'vosotros', 'vuestra', 'vuestras', 'vuestro', 'vuestros', 'y', 'ya', 'yo'
        }
        
        # Reglas simples de stemming para español (sufijos comunes)
        self.stemming_rules = [
            ('ando$', 'ar'), ('iendo$', 'er'), ('iendo$', 'ir'),
            ('ará$', 'ar'), ('erá$', 'er'), ('irá$', 'ir'),
            ('aría$', 'ar'), ('ería$', 'er'), ('iría$', 'ir'),
            ('aba$', 'ar'), ('ía$', 'er'), ('ía$', 'ir'),
            ('aste$', 'ar'), ('iste$', 'er'), ('iste$', 'ir'),
            ('aron$', 'ar'), ('ieron$', 'er'), ('ieron$', 'ir'),
            ('aremos$', 'ar'), ('eremos$', 'er'), ('iremos$', 'ir'),
            ('adores$', 'ador'), ('adores$', 'ar'),
            ('mente$', ''), ('ables$', 'able'), ('ibles$', 'ible'),
            ('idades$', 'idad'), ('ezas$', 'eza'),
            ('icos$', 'ico'), ('icas$', 'ica'), ('ismos$', 'ismo'),
            ('ables$', 'ar'), ('ibles$', 'ir'),
            ('aciones$', 'ar'), ('uciones$', 'uir'),
            ('logías$', 'logía'),
            ('os$', 'o'), ('as$', 'a'), ('es$', 'e'),
            ('s$', '')
        ]
        
        # Patrones regex comunes
        self.regex_patterns = {
            'dinero': r'\b(dinero|plata|pesos|euros|dólares|dolares)\b',
            'numero': r'\b\d+\b',
            'porcentaje': r'\b\d+\s*%\b',
            'cedula': r'\b\d{6,12}\b',
            'fecha': r'\b\d{1,2}\/\d{1,2}\/\d{2,4}\b'
        }
        
        # Cache para intenciones y patrones
        self.intenciones_cache = {}
        self.patrones_cache = {}
        self.sinonimos_cache = {}
        self.cache_actualizado = False
        
        # Definición de patrones por defecto (si no se puede acceder a la BD)
        self._definir_patrones_por_defecto()
    
    def _definir_patrones_por_defecto(self):
        """Define patrones por defecto para usar si no hay acceso a la BD"""
        self.default_intenciones = {
            1: {'nombre': 'consulta_deuda', 'estado_siguiente': 'informar_deuda'},
            2: {'nombre': 'pago', 'estado_siguiente': 'proponer_planes_pago'},
            3: {'nombre': 'acuerdo', 'estado_siguiente': 'proponer_planes_pago'},
            4: {'nombre': 'rechazo', 'estado_siguiente': 'gestionar_objecion'},
            5: {'nombre': 'identificacion', 'estado_siguiente': 'validar_documento'}
        }
        
        self.default_patrones = {
            1: [  # consulta_deuda
                {'patron': 'cuanto debo', 'tipo': 'contiene'},
                {'patron': 'cuánto debo', 'tipo': 'contiene'},
                {'patron': 'deuda', 'tipo': 'contiene'},
                {'patron': 'saldo', 'tipo': 'contiene'},
                {'patron': 'pendiente', 'tipo': 'contiene'},
                {'patron': 'valor', 'tipo': 'contiene'},
                {'patron': 'debo', 'tipo': 'contiene'},
                {'patron': 'total', 'tipo': 'contiene'}
            ],
            2: [  # pago
                {'patron': 'pagar', 'tipo': 'contiene'},
                {'patron': 'abonar', 'tipo': 'contiene'},
                {'patron': 'transferir', 'tipo': 'contiene'},
                {'patron': 'consignar', 'tipo': 'contiene'},
                {'patron': 'cancelar', 'tipo': 'contiene'},
                {'patron': 'liquidar', 'tipo': 'contiene'}
            ],
            3: [  # acuerdo
                {'patron': 'acuerdo', 'tipo': 'contiene'},
                {'patron': 'plan', 'tipo': 'contiene'},
                {'patron': 'cuota', 'tipo': 'contiene'},
                {'patron': 'facilidad', 'tipo': 'contiene'},
                {'patron': 'descuento', 'tipo': 'contiene'},
                {'patron': 'negociar', 'tipo': 'contiene'},
                {'patron': 'propuesta', 'tipo': 'contiene'}
            ],
            4: [  # rechazo
                {'patron': 'no voy a pagar', 'tipo': 'contiene'},
                {'patron': 'imposible', 'tipo': 'contiene'},
                {'patron': 'no puedo', 'tipo': 'contiene'},
                {'patron': 'no tengo', 'tipo': 'contiene'},
                {'patron': 'no reconozco', 'tipo': 'contiene'}
            ],
            5: [  # identificacion 
                {'patron': 'cedula', 'tipo': 'contiene'},
                {'patron': 'cédula', 'tipo': 'contiene'},
                {'patron': 'documento', 'tipo': 'contiene'},
                {'patron': 'identificacion', 'tipo': 'contiene'},
                {'patron': 'identificación', 'tipo': 'contiene'}
            ]
        }
        
        self.default_sinonimos = {
            'deuda': ['obligacion', 'obligación', 'pendiente', 'saldo'],
            'pagar': ['cancelar', 'abonar', 'consignar', 'liquidar'],
            'acuerdo': ['plan', 'convenio', 'arreglo', 'negociacion', 'negociación'],
            'descuento': ['rebaja', 'reducción', 'reduccion', 'quita', 'condonación', 'condonacion'],
            'dinero': ['plata', 'efectivo', 'recursos', 'fondos']
        }
    
    def _tokenizar(self, texto: str) -> List[str]:
        """Tokeniza un texto en palabras sin usar NLTK"""
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Eliminar puntuación
        for p in string.punctuation:
            texto = texto.replace(p, ' ')
        
        # Dividir en tokens
        tokens = texto.split()
        
        # Eliminar tokens vacíos
        return [t for t in tokens if t]
    
    def _eliminar_stopwords(self, tokens: List[str]) -> List[str]:
        """Elimina palabras comunes (stopwords)"""
        return [t for t in tokens if t not in self.stop_words]
    
    def _aplicar_stemming(self, palabra: str) -> str:
        """Aplica reglas de stemming simples para español"""
        palabra_original = palabra
        
        # Aplicar reglas de stemming
        for sufijo, reemplazo in self.stemming_rules:
            if re.search(sufijo, palabra):
                palabra = re.sub(sufijo, reemplazo, palabra)
                break
        
        # Si la palabra es muy corta, mantener la original
        if len(palabra) < 3:
            return palabra_original
        
        return palabra
    
    def _limpiar_texto(self, texto: str) -> str:
        """Limpia el texto: tokeniza, elimina stopwords y aplica stemming"""
        if not texto:
            return ""
            
        # Tokenizar
        tokens = self._tokenizar(texto)
        
        # Eliminar stopwords
        tokens = self._eliminar_stopwords(tokens)
        
        # Aplicar stemming
        tokens = [self._aplicar_stemming(token) for token in tokens]
        
        return ' '.join(tokens)
    
    def _actualizar_cache_desde_bd(self, db: Session):
        """Actualiza la caché desde la base de datos"""
        try:
            # Verificar si existen las tablas
            verifica_tablas = text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME IN ('Intenciones', 'Patrones_Intencion', 'Sinonimos')
            """)
            tablas_count = db.execute(verifica_tablas).scalar()
            
            if tablas_count < 3:
                print("ADVERTENCIA: Tablas NLP no existen - usando configuración por defecto")
                self._crear_tablas_nlp(db)
                return False
            
            # Cargar intenciones
            query_intenciones = text("SELECT id, nombre, estado_siguiente FROM Intenciones")
            for row in db.execute(query_intenciones):
                self.intenciones_cache[row[0]] = {
                    'nombre': row[1],
                    'estado_siguiente': row[2]
                }
            
            # Cargar patrones
            query_patrones = text("SELECT intencion_id, patron, tipo FROM Patrones_Intencion")
            for row in db.execute(query_patrones):
                intencion_id = row[0]
                if intencion_id not in self.patrones_cache:
                    self.patrones_cache[intencion_id] = []
                
                self.patrones_cache[intencion_id].append({
                    'patron': row[1].lower(),
                    'patron_limpio': self._limpiar_texto(row[1]),
                    'tipo': row[2]
                })
            
            # Cargar sinónimos
            query_sinonimos = text("SELECT palabra, sinonimo FROM Sinonimos")
            for row in db.execute(query_sinonimos):
                palabra = row[0].lower()
                if palabra not in self.sinonimos_cache:
                    self.sinonimos_cache[palabra] = []
                self.sinonimos_cache[palabra].append(row[1].lower())
            
            return True
            
        except Exception as e:
            print(f"Error al actualizar cache desde BD: {e}")
            return False
    
    def _crear_tablas_nlp(self, db: Session):
        """Crea las tablas en la base de datos si no existen"""
        try:
            # Crear tablas
            crear_tabla_intenciones = text("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Intenciones')
                BEGIN
                    CREATE TABLE Intenciones (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        nombre VARCHAR(50) NOT NULL,
                        descripcion VARCHAR(255),
                        estado_siguiente VARCHAR(50),
                        prioridad INT DEFAULT 1
                    )
                END
            """)
            
            crear_tabla_patrones = text("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Patrones_Intencion')
                BEGIN
                    CREATE TABLE Patrones_Intencion (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        intencion_id INT,
                        patron VARCHAR(100) NOT NULL,
                        tipo VARCHAR(20) DEFAULT 'exacto'
                    )
                END
            """)
            
            crear_tabla_sinonimos = text("""
                IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Sinonimos')
                BEGIN
                    CREATE TABLE Sinonimos (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        palabra VARCHAR(50) NOT NULL,
                        sinonimo VARCHAR(50) NOT NULL
                    )
                END
            """)
            
            db.execute(crear_tabla_intenciones)
            db.execute(crear_tabla_patrones)
            db.execute(crear_tabla_sinonimos)
            db.commit()
            
            # Insertar datos por defecto
            self._cargar_datos_predeterminados(db)
            
        except Exception as e:
            print(f"Error al crear tablas NLP: {e}")
            db.rollback()
    
    def _cargar_datos_predeterminados(self, db: Session):
        """Carga datos predefinidos en la base de datos"""
        try:
            # Cargar intenciones
            for intent_id, intent_data in self.default_intenciones.items():
                insert = text("""
                    IF NOT EXISTS (SELECT 1 FROM Intenciones WHERE nombre = :nombre)
                    BEGIN
                        INSERT INTO Intenciones (nombre, estado_siguiente)
                        VALUES (:nombre, :estado)
                    END
                """)
                db.execute(insert, {
                    "nombre": intent_data['nombre'],
                    "estado": intent_data['estado_siguiente']
                })
            
            # Obtener IDs reales
            id_map = {}
            id_query = text("SELECT id, nombre FROM Intenciones")
            for row in db.execute(id_query):
                id_map[row[1]] = row[0]
            
            # Cargar patrones
            for default_id, patrones in self.default_patrones.items():
                intencion_nombre = self.default_intenciones[default_id]['nombre']
                intencion_id = id_map.get(intencion_nombre)
                
                if intencion_id:
                    for p in patrones:
                        insert = text("""
                            IF NOT EXISTS (SELECT 1 FROM Patrones_Intencion 
                                          WHERE intencion_id = :intencion_id AND patron = :patron)
                            BEGIN
                                INSERT INTO Patrones_Intencion (intencion_id, patron, tipo)
                                VALUES (:intencion_id, :patron, :tipo)
                            END
                        """)
                        db.execute(insert, {
                            "intencion_id": intencion_id, 
                            "patron": p['patron'],
                            "tipo": p['tipo']
                        })
            
            # Cargar sinónimos
            for palabra, sinonimos in self.default_sinonimos.items():
                for sinonimo in sinonimos:
                    insert = text("""
                        IF NOT EXISTS (SELECT 1 FROM Sinonimos 
                                      WHERE palabra = :palabra AND sinonimo = :sinonimo)
                        BEGIN
                            INSERT INTO Sinonimos (palabra, sinonimo)
                            VALUES (:palabra, :sinonimo)
                        END
                    """)
                    db.execute(insert, {"palabra": palabra, "sinonimo": sinonimo})
            
            db.commit()
            print("Datos predeterminados cargados correctamente")
            
        except Exception as e:
            print(f"Error al cargar datos predeterminados: {e}")
            db.rollback()
    
    def actualizar_cache(self, db: Session):
        """Actualiza la caché de intenciones, patrones y sinónimos"""
        # Intentar cargar desde la base de datos
        if self._actualizar_cache_desde_bd(db):
            self.cache_actualizado = True
            print(f"Cache actualizado desde BD: {len(self.intenciones_cache)} intenciones")
        else:
            # Si falla, usar la configuración por defecto
            self.intenciones_cache = self.default_intenciones
            self.patrones_cache = self.default_patrones
            self.sinonimos_cache = self.default_sinonimos
            self.cache_actualizado = True
            print("Cache actualizado con configuración por defecto")
    
    def expandir_texto_con_sinonimos(self, texto: str) -> str:
        """Expande el texto con sinónimos conocidos"""
        if not texto:
            return ""
            
        palabras = texto.lower().split()
        texto_expandido = texto.lower()
        
        # Buscar sinónimos para cada palabra
        for palabra in palabras:
            if palabra in self.sinonimos_cache:
                for sinonimo in self.sinonimos_cache[palabra]:
                    if sinonimo not in texto_expandido:
                        texto_expandido += f" {sinonimo}"
        
        return texto_expandido
    
    def detectar_documento_identidad(self, texto: str) -> str:
        """Intenta extraer un número de documento del texto"""
        # Patrones comunes para documentos
        patrones = [
            r'\b\d{6,12}\b',            # Números de 6 a 12 dígitos
            r'cédula\s+(\d{6,12})',      # "cédula" seguido de números
            r'cedula\s+(\d{6,12})',      # "cedula" sin tilde
            r'cc\s+(\d{6,12})',          # "cc" seguido de números
            r'documento\s+(\d{6,12})'    # "documento" seguido de números
        ]
        
        texto = texto.lower()
        for patron in patrones:
            match = re.search(patron, texto)
            if match:
                # Si hay grupos capturados, devolver el primer grupo
                if match.groups():
                    return match.group(1)
                # Si no hay grupos, devolver la coincidencia completa
                return match.group(0)
        
        return None
    
    def detectar_intencion(self, db: Session, mensaje: str) -> dict:
        """
        Detecta la intención del usuario en el mensaje utilizando
        técnicas simples de procesamiento de texto.
        """
        # Actualizar caché si es necesario
        if not self.cache_actualizado:
            self.actualizar_cache(db)
        
        if not mensaje:
            return {
                "intencion": "desconocida", 
                "confianza": 0, 
                "estado_siguiente": None
            }
        
        # Preprocesamiento del mensaje
        mensaje_original = mensaje.lower()
        mensaje_expandido = self.expandir_texto_con_sinonimos(mensaje_original)
        mensaje_limpio = self._limpiar_texto(mensaje_expandido)
        
        print(f"Mensaje original: '{mensaje_original}'")
        print(f"Mensaje expandido: '{mensaje_expandido}'")
        print(f"Mensaje limpio: '{mensaje_limpio}'")
        
        # Detectar documento de identidad
        documento = self.detectar_documento_identidad(mensaje_original)
        if documento:
            print(f"Documento detectado: {documento}")
        
        # Lista para almacenar coincidencias
        coincidencias = []
        
        # 1. Verificar coincidencias por contención
        for intencion_id, patrones in self.patrones_cache.items():
            for patron_info in patrones:
                patron = patron_info['patron']
                patron_limpio = patron_info.get('patron_limpio', self._limpiar_texto(patron))
                
                # Verificar si el patrón está contenido en el mensaje original
                if patron in mensaje_original:
                    coincidencias.append({
                        'intencion_id': intencion_id,
                        'confianza': 0.9,
                        'patron': patron
                    })
                # Verificar con el mensaje limpio
                elif patron_limpio and patron_limpio in mensaje_limpio:
                    coincidencias.append({
                        'intencion_id': intencion_id,
                        'confianza': 0.8,
                        'patron': patron
                    })
        
        # 2. Si se detectó un documento, dar prioridad a la intención de identificación
        if documento:
            for intencion_id, info in self.intenciones_cache.items():
                if info['nombre'] == 'identificacion':
                    coincidencias.append({
                        'intencion_id': intencion_id,
                        'confianza': 0.95,
                        'patron': 'documento_detectado'
                    })
                    break
        
        # 3. Si no hay coincidencias claras, contar ocurrencias de palabras clave
        if not coincidencias:
            palabras_mensaje = set(mensaje_limpio.split())
            
            for intencion_id, patrones in self.patrones_cache.items():
                contador = 0
                patrones_palabras = set()
                
                # Recopilar todas las palabras de los patrones de esta intención
                for patron_info in patrones:
                    patron = patron_info.get('patron_limpio', self._limpiar_texto(patron_info['patron']))
                    for palabra in patron.split():
                        if len(palabra) > 2:  # Solo palabras significativas
                            patrones_palabras.add(palabra)
                
                # Contar cuántas palabras del mensaje coinciden con palabras de patrones
                for palabra in palabras_mensaje:
                    if palabra in patrones_palabras:
                        contador += 1
                
                # Si hay coincidencias, añadir a la lista
                if contador > 0 and len(patrones_palabras) > 0:
                    ratio = contador / len(patrones_palabras)
                    if ratio > 0.2:  # Umbral mínimo
                        confianza = 0.5 + (0.3 * ratio)
                        coincidencias.append({
                            'intencion_id': intencion_id,
                            'confianza': confianza,
                            'patron': f"{contador} palabras clave"
                        })
        
        # Si no hay coincidencias, devolver desconocida
        if not coincidencias:
            return {
                "intencion": "desconocida", 
                "confianza": 0, 
                "estado_siguiente": None
            }
        
        # Imprimir coincidencias para debugging
        print("Coincidencias encontradas:")
        for c in coincidencias:
            intent_info = self.intenciones_cache.get(c['intencion_id'], {'nombre': 'desconocida'})
            print(f"  - {intent_info['nombre']}: {c['confianza']:.2f} ({c['patron']})")
        
        # Obtener la mejor coincidencia
        mejor_coincidencia = max(coincidencias, key=lambda x: x['confianza'])
        intencion_id = mejor_coincidencia['intencion_id']
        intencion_info = self.intenciones_cache.get(intencion_id, {'nombre': 'desconocida', 'estado_siguiente': None})
        
        return {
            "intencion": intencion_info['nombre'],
            "confianza": mejor_coincidencia['confianza'],
            "estado_siguiente": intencion_info['estado_siguiente'],
            "patron_detectado": mejor_coincidencia['patron'],
            "documento_detectado": documento
        }

# Instancia global del servicio
nlp_service = SimpleNLPService()