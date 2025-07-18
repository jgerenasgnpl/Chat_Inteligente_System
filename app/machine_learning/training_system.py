"""
🚀 SISTEMA DE ENTRENAMIENTO MEJORADO
Permite actualizar mapas de entrenamiento por archivo o manualmente
"""
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path

class TrainingMapManager:
    """
    🗺️ GESTOR DE MAPAS DE ENTRENAMIENTO
    
    Funciones:
    - Cargar/guardar mapas desde Excel/JSON
    - Actualización manual de mapas
    - Validación de consistencia
    - Backup automático
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.maps_dir = Path("data/training_maps")
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        
        self.intention_map = {}
        self.state_transitions = {}
        self.response_templates = {}
        self.validation_rules = {}
    
    def load_training_map_from_file(self, file_path: str) -> bool:
        """Cargar mapa de entrenamiento desde archivo"""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.xlsx':
                return self._load_from_excel(file_path)
            elif file_path.suffix.lower() == '.json':
                return self._load_from_json(file_path)
            else:
                print(f"❌ Formato no soportado: {file_path.suffix}")
                return False
                
        except Exception as e:
            print(f"❌ Error cargando archivo: {e}")
            return False
    
    def _load_from_excel(self, file_path: Path) -> bool:
        """Cargar desde Excel con múltiples hojas"""
        try:
            print(f"📂 Cargando mapa desde Excel: {file_path}")
            
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            for sheet_name, df in excel_data.items():
                sheet_lower = sheet_name.lower()
                
                if 'intenciones' in sheet_lower or 'intentions' in sheet_lower:
                    self._process_intentions_sheet(df)
                elif 'estados' in sheet_lower or 'states' in sheet_lower:
                    self._process_states_sheet(df)
                elif 'respuestas' in sheet_lower or 'responses' in sheet_lower:
                    self._process_responses_sheet(df)
                elif 'entrenamiento' in sheet_lower or 'training' in sheet_lower:
                    self._process_training_sheet(df)
                else:
                    print(f"⚠️ Hoja no reconocida: {sheet_name}")
            
            print("✅ Mapa cargado desde Excel exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error procesando Excel: {e}")
            return False
    
    def _process_intentions_sheet(self, df: pd.DataFrame):
        """Procesar hoja de intenciones"""
        for _, row in df.iterrows():
            try:
                intention_id = row.get('id') or row.get('nombre', '')
                self.intention_map[intention_id] = {
                    'nombre': row.get('nombre', intention_id),
                    'descripcion': row.get('descripcion', ''),
                    'estado_siguiente': row.get('estado_siguiente', ''),
                    'prioridad': int(row.get('prioridad', 1)),
                    'activo': bool(row.get('activo', True)),
                    'ejemplos': str(row.get('ejemplos', '')).split(',') if row.get('ejemplos') else []
                }
            except Exception as e:
                print(f"⚠️ Error procesando intención: {e}")
    
    def _process_states_sheet(self, df: pd.DataFrame):
        """Procesar hoja de estados"""
        for _, row in df.iterrows():
            try:
                state_name = row.get('nombre', '')
                self.state_transitions[state_name] = {
                    'mensaje_template': row.get('mensaje_template', ''),
                    'accion': row.get('accion', ''),
                    'condicion': row.get('condicion', ''),
                    'estado_siguiente_true': row.get('estado_siguiente_true', ''),
                    'estado_siguiente_false': row.get('estado_siguiente_false', ''),
                    'estado_siguiente_default': row.get('estado_siguiente_default', ''),
                    'timeout_segundos': int(row.get('timeout_segundos', 1800)),
                    'activo': bool(row.get('activo', True))
                }
            except Exception as e:
                print(f"⚠️ Error procesando estado: {e}")
    
    def _process_responses_sheet(self, df: pd.DataFrame):
        """Procesar hoja de respuestas"""
        for _, row in df.iterrows():
            try:
                response_id = row.get('id', '')
                self.response_templates[response_id] = {
                    'template': row.get('template', ''),
                    'variables': str(row.get('variables', '')).split(',') if row.get('variables') else [],
                    'contexto_requerido': str(row.get('contexto_requerido', '')).split(',') if row.get('contexto_requerido') else [],
                    'tipo': row.get('tipo', 'informativo'),
                    'prioridad': int(row.get('prioridad', 1))
                }
            except Exception as e:
                print(f"⚠️ Error procesando respuesta: {e}")
    
    def _process_training_sheet(self, df: pd.DataFrame):
        """Procesar hoja de datos de entrenamiento"""
        try:
            for _, row in df.iterrows():
                texto = row.get('texto_mensaje', '')
                intencion = row.get('intencion_real', '')
                confianza = float(row.get('confianza_etiqueta', 1.0))
                
                if texto and intencion:
                    self.add_training_example_to_db(texto, intencion, confianza)
        except Exception as e:
            print(f"⚠️ Error procesando datos de entrenamiento: {e}")
    
    def _load_from_json(self, file_path: Path) -> bool:
        """Cargar desde JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.intention_map = data.get('intenciones', {})
            self.state_transitions = data.get('estados', {})
            self.response_templates = data.get('respuestas', {})
            self.validation_rules = data.get('validaciones', {})
            
            print("✅ Mapa cargado desde JSON exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando JSON: {e}")
            return False
    
    def save_training_map_to_file(self, file_path: str, format_type: str = 'json') -> bool:
        """Guardar mapa actual a archivo"""
        try:
            file_path = Path(file_path)
            
            if format_type.lower() == 'json':
                return self._save_to_json(file_path)
            elif format_type.lower() == 'excel':
                return self._save_to_excel(file_path)
            else:
                print(f"❌ Formato no soportado: {format_type}")
                return False
                
        except Exception as e:
            print(f"❌ Error guardando archivo: {e}")
            return False
    
    def _save_to_json(self, file_path: Path) -> bool:
        """Guardar a JSON"""
        try:
            data = {
                'intenciones': self.intention_map,
                'estados': self.state_transitions,
                'respuestas': self.response_templates,
                'validaciones': self.validation_rules,
                'metadata': {
                    'fecha_creacion': datetime.now().isoformat(),
                    'version': '2.0',
                    'total_intenciones': len(self.intention_map),
                    'total_estados': len(self.state_transitions)
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Mapa guardado en JSON: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")
            return False
    
    def _save_to_excel(self, file_path: Path) -> bool:
        """Guardar a Excel con múltiples hojas"""
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Hoja de intenciones
                intentions_df = pd.DataFrame([
                    {
                        'id': k,
                        'nombre': v['nombre'],
                        'descripcion': v['descripcion'],
                        'estado_siguiente': v['estado_siguiente'],
                        'prioridad': v['prioridad'],
                        'activo': v['activo'],
                        'ejemplos': ','.join(v['ejemplos'])
                    }
                    for k, v in self.intention_map.items()
                ])
                intentions_df.to_excel(writer, sheet_name='Intenciones', index=False)
                
                # Hoja de estados
                states_df = pd.DataFrame([
                    {
                        'nombre': k,
                        'mensaje_template': v['mensaje_template'],
                        'accion': v['accion'],
                        'condicion': v['condicion'],
                        'estado_siguiente_true': v['estado_siguiente_true'],
                        'estado_siguiente_false': v['estado_siguiente_false'],
                        'estado_siguiente_default': v['estado_siguiente_default'],
                        'timeout_segundos': v['timeout_segundos'],
                        'activo': v['activo']
                    }
                    for k, v in self.state_transitions.items()
                ])
                states_df.to_excel(writer, sheet_name='Estados', index=False)
                
                # Hoja de respuestas
                responses_df = pd.DataFrame([
                    {
                        'id': k,
                        'template': v['template'],
                        'variables': ','.join(v['variables']),
                        'contexto_requerido': ','.join(v['contexto_requerido']),
                        'tipo': v['tipo'],
                        'prioridad': v['prioridad']
                    }
                    for k, v in self.response_templates.items()
                ])
                responses_df.to_excel(writer, sheet_name='Respuestas', index=False)
            
            print(f"✅ Mapa guardado en Excel: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error guardando Excel: {e}")
            return False
    
    def add_intention_manually(self, nombre: str, descripcion: str = '', 
                              estado_siguiente: str = '', prioridad: int = 1,
                              ejemplos: List[str] = None) -> bool:
        """Agregar intención manualmente"""
        try:
            if ejemplos is None:
                ejemplos = []
            
            self.intention_map[nombre] = {
                'nombre': nombre,
                'descripcion': descripcion,
                'estado_siguiente': estado_siguiente,
                'prioridad': prioridad,
                'activo': True,
                'ejemplos': ejemplos,
                'fecha_creacion': datetime.now().isoformat()
            }
            
            print(f"✅ Intención agregada: {nombre}")
            return True
            
        except Exception as e:
            print(f"❌ Error agregando intención: {e}")
            return False
    
    def add_state_manually(self, nombre: str, mensaje_template: str,
                          estado_siguiente_default: str = '',
                          accion: str = '', condicion: str = '') -> bool:
        """Agregar estado manualmente"""
        try:
            self.state_transitions[nombre] = {
                'mensaje_template': mensaje_template,
                'accion': accion,
                'condicion': condicion,
                'estado_siguiente_true': '',
                'estado_siguiente_false': '',
                'estado_siguiente_default': estado_siguiente_default,
                'timeout_segundos': 1800,
                'activo': True,
                'fecha_creacion': datetime.now().isoformat()
            }
            
            print(f"✅ Estado agregado: {nombre}")
            return True
            
        except Exception as e:
            print(f"❌ Error agregando estado: {e}")
            return False
    
    def add_training_example_to_db(self, texto: str, intencion: str, confianza: float = 1.0) -> bool:
        """Agregar ejemplo de entrenamiento a BD"""
        try:
            insert_query = text("""
                INSERT INTO datos_entrenamiento 
                (texto_mensaje, intencion_real, confianza_etiqueta, 
                 fecha_registro, feedback_usuario, validado)
                VALUES (:texto, :intencion, :confianza, GETDATE(), 'correcto', 1)
            """)
            
            self.db.execute(insert_query, {
                'texto': texto,
                'intencion': intencion,
                'confianza': confianza
            })
            self.db.commit()
            
            print(f"✅ Ejemplo agregado a BD: '{texto}' -> {intencion}")
            return True
            
        except Exception as e:
            print(f"❌ Error agregando a BD: {e}")
            self.db.rollback()
            return False
    
    def sync_to_database(self) -> bool:
        """Sincronizar mapas a base de datos"""
        try:
            print("🔄 Sincronizando mapas a base de datos...")
            
            # Sincronizar intenciones
            self._sync_intentions_to_db()
            
            # Sincronizar estados
            self._sync_states_to_db()
            
            print("✅ Sincronización completada")
            return True
            
        except Exception as e:
            print(f"❌ Error en sincronización: {e}")
            return False
    
    def _sync_intentions_to_db(self):
        """Sincronizar intenciones a BD"""
        for intention_id, data in self.intention_map.items():
            try:
                # Verificar si existe
                check_query = text("SELECT COUNT(*) FROM Intenciones WHERE nombre = :nombre")
                exists = self.db.execute(check_query, {'nombre': data['nombre']}).scalar()
                
                if exists > 0:
                    # Actualizar
                    update_query = text("""
                        UPDATE Intenciones 
                        SET descripcion = :desc, estado_siguiente = :estado, prioridad = :prioridad
                        WHERE nombre = :nombre
                    """)
                    self.db.execute(update_query, {
                        'nombre': data['nombre'],
                        'desc': data['descripcion'],
                        'estado': data['estado_siguiente'],
                        'prioridad': data['prioridad']
                    })
                else:
                    # Insertar
                    insert_query = text("""
                        INSERT INTO Intenciones (nombre, descripcion, estado_siguiente, prioridad)
                        VALUES (:nombre, :desc, :estado, :prioridad)
                    """)
                    self.db.execute(insert_query, {
                        'nombre': data['nombre'],
                        'desc': data['descripcion'],
                        'estado': data['estado_siguiente'],
                        'prioridad': data['prioridad']
                    })
                
                # Agregar ejemplos como datos de entrenamiento
                for ejemplo in data.get('ejemplos', []):
                    if ejemplo.strip():
                        self.add_training_example_to_db(ejemplo.strip(), data['nombre'])
                        
            except Exception as e:
                print(f"⚠️ Error sincronizando intención {intention_id}: {e}")
    
    def _sync_states_to_db(self):
        """Sincronizar estados a BD"""
        for state_name, data in self.state_transitions.items():
            try:
                # Verificar si existe
                check_query = text("SELECT COUNT(*) FROM Estados_Conversacion WHERE nombre = :nombre")
                exists = self.db.execute(check_query, {'nombre': state_name}).scalar()
                
                if exists > 0:
                    # Actualizar
                    update_query = text("""
                        UPDATE Estados_Conversacion 
                        SET mensaje_template = :template, accion = :accion, 
                            condicion = :condicion, estado_siguiente_default = :default_state,
                            timeout_segundos = :timeout, activo = :activo
                        WHERE nombre = :nombre
                    """)
                    self.db.execute(update_query, {
                        'nombre': state_name,
                        'template': data['mensaje_template'],
                        'accion': data['accion'],
                        'condicion': data['condicion'],
                        'default_state': data['estado_siguiente_default'],
                        'timeout': data['timeout_segundos'],
                        'activo': data['activo']
                    })
                else:
                    # Insertar
                    insert_query = text("""
                        INSERT INTO Estados_Conversacion 
                        (nombre, mensaje_template, accion, condicion, 
                         estado_siguiente_default, timeout_segundos, activo)
                        VALUES (:nombre, :template, :accion, :condicion, 
                                :default_state, :timeout, :activo)
                    """)
                    self.db.execute(insert_query, {
                        'nombre': state_name,
                        'template': data['mensaje_template'],
                        'accion': data['accion'],
                        'condicion': data['condicion'],
                        'default_state': data['estado_siguiente_default'],
                        'timeout': data['timeout_segundos'],
                        'activo': data['activo']
                    })
                    
            except Exception as e:
                print(f"⚠️ Error sincronizando estado {state_name}: {e}")
    
    def load_from_database(self) -> bool:
        """Cargar mapas desde base de datos"""
        try:
            print("📂 Cargando mapas desde base de datos...")
            
            # Cargar intenciones
            intentions_query = text("""
                SELECT nombre, descripcion, estado_siguiente, prioridad 
                FROM Intenciones WHERE activo = 1
            """)
            
            for row in self.db.execute(intentions_query):
                self.intention_map[row[0]] = {
                    'nombre': row[0],
                    'descripcion': row[1] or '',
                    'estado_siguiente': row[2] or '',
                    'prioridad': row[3] or 1,
                    'activo': True,
                    'ejemplos': []
                }
            
            # Cargar estados
            states_query = text("""
                SELECT nombre, mensaje_template, accion, condicion,
                       estado_siguiente_default, timeout_segundos, activo
                FROM Estados_Conversacion
            """)
            
            for row in self.db.execute(states_query):
                self.state_transitions[row[0]] = {
                    'mensaje_template': row[1] or '',
                    'accion': row[2] or '',
                    'condicion': row[3] or '',
                    'estado_siguiente_true': '',
                    'estado_siguiente_false': '',
                    'estado_siguiente_default': row[4] or '',
                    'timeout_segundos': row[5] or 1800,
                    'activo': bool(row[6])
                }
            
            print(f"✅ Cargadas {len(self.intention_map)} intenciones y {len(self.state_transitions)} estados")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando desde BD: {e}")
            return False
    
    def validate_maps(self) -> Dict[str, List[str]]:
        """Validar consistencia de mapas"""
        errors = {
            'intenciones': [],
            'estados': [],
            'flujos': []
        }
        
        # Validar intenciones
        for name, data in self.intention_map.items():
            if not data.get('nombre'):
                errors['intenciones'].append(f"Intención {name} sin nombre")
            if not data.get('estado_siguiente'):
                errors['intenciones'].append(f"Intención {name} sin estado siguiente")
        
        # Validar estados
        for name, data in self.state_transitions.items():
            if not data.get('mensaje_template'):
                errors['estados'].append(f"Estado {name} sin template de mensaje")
        
        # Validar flujos (estados referenciados existen)
        all_states = set(self.state_transitions.keys())
        for name, data in self.intention_map.items():
            next_state = data.get('estado_siguiente')
            if next_state and next_state not in all_states:
                errors['flujos'].append(f"Intención {name} refiere a estado inexistente: {next_state}")
        
        return errors
    
    def create_backup(self) -> str:
        """Crear backup de mapas actuales"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.maps_dir / f"backup_training_map_{timestamp}.json"
            
            if self._save_to_json(backup_path):
                print(f"💾 Backup creado: {backup_path}")
                return str(backup_path)
            else:
                return ""
                
        except Exception as e:
            print(f"❌ Error creando backup: {e}")
            return ""

# ==========================================
# INTERFAZ DE ADMINISTRACIÓN
# ==========================================

class TrainingAdminInterface:
    """Interfaz administrativa para gestión de entrenamiento"""
    
    def __init__(self, db: Session):
        self.db = db
        self.map_manager = TrainingMapManager(db)
    
    def import_training_data(self, file_path: str) -> Dict[str, Any]:
        """Importar datos de entrenamiento desde archivo"""
        try:
            # Crear backup antes de importar
            backup_path = self.map_manager.create_backup()
            
            # Importar
            success = self.map_manager.load_training_map_from_file(file_path)
            
            if success:
                # Validar
                errors = self.map_manager.validate_maps()
                
                if any(errors.values()):
                    return {
                        'success': False,
                        'errors': errors,
                        'backup_path': backup_path
                    }
                
                # Sincronizar a BD
                sync_success = self.map_manager.sync_to_database()
                
                return {
                    'success': sync_success,
                    'message': 'Datos importados y sincronizados exitosamente',
                    'intenciones_count': len(self.map_manager.intention_map),
                    'estados_count': len(self.map_manager.state_transitions),
                    'backup_path': backup_path
                }
            else:
                return {
                    'success': False,
                    'message': 'Error importando archivo'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_training_data(self, file_path: str, format_type: str = 'excel') -> Dict[str, Any]:
        """Exportar datos actuales"""
        try:
            # Cargar desde BD
            self.map_manager.load_from_database()
            
            # Exportar
            success = self.map_manager.save_training_map_to_file(file_path, format_type)
            
            return {
                'success': success,
                'file_path': file_path if success else None,
                'message': f'Datos exportados a {format_type.upper()}' if success else 'Error en exportación'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_intention_via_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Agregar intención vía API"""
        try:
            success = self.map_manager.add_intention_manually(
                nombre=data['nombre'],
                descripcion=data.get('descripcion', ''),
                estado_siguiente=data.get('estado_siguiente', ''),
                prioridad=data.get('prioridad', 1),
                ejemplos=data.get('ejemplos', [])
            )
            
            if success:
                self.map_manager.sync_to_database()
            
            return {
                'success': success,
                'message': f'Intención {data["nombre"]} agregada' if success else 'Error agregando intención'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de entrenamiento"""
        try:
            # Estadísticas de la BD
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_ejemplos,
                    COUNT(DISTINCT intencion_real) as total_intenciones,
                    AVG(CAST(confianza_etiqueta as FLOAT)) as confianza_promedio,
                    COUNT(CASE WHEN validado = 1 THEN 1 END) as ejemplos_validados,
                    COUNT(CASE WHEN fecha_registro > DATEADD(day, -7, GETDATE()) THEN 1 END) as ejemplos_ultima_semana
                FROM datos_entrenamiento
                WHERE intencion_real IS NOT NULL
            """)
            
            row = self.db.execute(stats_query).fetchone()
            
            return {
                'total_ejemplos': row[0] or 0,
                'total_intenciones': row[1] or 0,
                'confianza_promedio': round(row[2] or 0, 3),
                'ejemplos_validados': row[3] or 0,
                'ejemplos_ultima_semana': row[4] or 0,
                'intenciones_en_mapa': len(self.map_manager.intention_map),
                'estados_en_mapa': len(self.map_manager.state_transitions)
            }
            
        except Exception as e:
            return {
                'error': str(e)
            }

# ==========================================
# FACTORY
# ==========================================

def create_training_admin(db: Session) -> TrainingAdminInterface:
    """Factory para crear interfaz administrativa"""
    return TrainingAdminInterface(db)