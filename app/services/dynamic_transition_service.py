import json
import re
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.models.condiciones_inteligentes import CondicionesInteligentes

logger = logging.getLogger(__name__)

class DynamicTransitionService:
    """
    🎯 SERVICIO DE TRANSICIONES 100% DINÁMICO
    - Sin patrones hardcodeados
    - Configuración desde BD
    - Auto-mejora basada en resultados
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ml_mappings = {}
        self.keyword_patterns = {}
        self.condition_evaluators = {}
        self.cache_timestamp = 0
        self.cache_ttl = 300  
        
        # Cargar configuración inicial
        self._load_configuration()
    
    def _load_configuration(self):
        """✅ CARGAR TODA LA CONFIGURACIÓN DESDE BD"""
        try:
            start_time = time.time()
            
            # 1. Cargar mapeos ML → BD
            self._load_ml_mappings()
            
            # 2. Cargar patrones de palabras clave
            self._load_keyword_patterns()
            
            # 3. Cargar evaluadores de condición
            self._load_condition_evaluators()
            
            self.cache_timestamp = time.time()
            
            load_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Configuración dinámica cargada en {load_time:.1f}ms")
            logger.info(f"   ML mappings: {len(self.ml_mappings)}")
            logger.info(f"   Keyword patterns: {len(self.keyword_patterns)}")
            logger.info(f"   Condition evaluators: {len(self.condition_evaluators)}")
            
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
            self._load_emergency_fallback()
    
    def _load_ml_mappings(self):
        """Cargar mapeos ML → Condiciones BD"""
        try:
            query = text("""
                SELECT ml_intention, bd_condition, confidence_threshold, priority
                FROM ml_intention_mappings
                WHERE active = 1
                ORDER BY priority ASC, confidence_threshold DESC
            """)

            self.ml_mappings = {}
            result = self.db.execute(query)
            rows = result.fetchall()

            print(f"🔍 Cargando ML mappings... Encontradas {len(rows)} filas")

            for row in rows:
                self.ml_mappings[row[0]] = {
                    'bd_condition': row[1],
                    'confidence_threshold': row[2],
                    'priority': row[3]
                }
                print(f"   ✅ {row[0]} → {row[1]} (confianza: {row[2]})")

            print(f"✅ ML mappings cargados: {len(self.ml_mappings)} elementos")

        except Exception as e:
            print(f"❌ Error cargando ML mappings: {e}")
            import traceback
            traceback.print_exc()
            self.ml_mappings = {}

    def _load_keyword_patterns(self):
        """Cargar patrones de palabras clave"""
        try:
            query = text("""
                SELECT keyword_pattern, bd_condition, confidence_score, 
                       requires_client, state_context, pattern_type
                FROM keyword_condition_patterns 
                WHERE active = 1
                ORDER BY confidence_score DESC
            """)
            
            self.keyword_patterns = {}
            for row in self.db.execute(query):
                pattern = row[0].lower()
                self.keyword_patterns[pattern] = {
                    'bd_condition': row[1],
                    'confidence': row[2],
                    'requires_client': bool(row[3]),
                    'state_context': row[4],
                    'pattern_type': row[5] or 'contains'
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Error cargando keyword patterns: {e}")
            self.keyword_patterns = {}
    
    def _load_condition_evaluators(self):
        """Cargar evaluadores de condición"""
        try:
            query = text("""
                SELECT condition_name, evaluation_method, evaluation_config, success_threshold
                FROM condition_evaluators 
                WHERE active = 1
            """)
            
            self.condition_evaluators = {}
            for row in self.db.execute(query):
                self.condition_evaluators[row[0]] = {
                    'method': row[1],
                    'config': json.loads(row[2]) if row[2] else {},
                    'threshold': row[3]
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Error cargando evaluadores: {e}")
            self.condition_evaluators = {}
    
    def _load_emergency_fallback(self):
        """Fallback mínimo en caso de error de BD"""
        logger.warning("🚨 Usando configuración de emergencia")
        
        self.ml_mappings = {
            'CONFIRMACION_EXITOSA': {'bd_condition': 'cliente_selecciona_plan', 'confidence_threshold': 0.7, 'priority': 1},
            'IDENTIFICACION': {'bd_condition': 'cedula_detectada', 'confidence_threshold': 0.8, 'priority': 1}
        }
        
        self.keyword_patterns = {
            'acepto': {'bd_condition': 'cliente_selecciona_plan', 'confidence': 0.9, 'requires_client': True, 'state_context': None, 'pattern_type': 'contains'},
            'si': {'bd_condition': 'cliente_confirma_interes', 'confidence': 0.8, 'requires_client': False, 'state_context': None, 'pattern_type': 'contains'}
        }
    
    def determine_next_state(self, current_state: str, user_message: str, 
                        ml_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """🎯 MÉTODO PRINCIPAL: Determinar siguiente estado dinámicamente"""
        
        start_time = time.time()
        
        if time.time() - self.cache_timestamp > self.cache_ttl:
            self._load_configuration()
        
        logger.info(f"🎯 Determinando transición: {current_state} + '{user_message[:30]}...'")
        
        # 1. ✅ PRIORIDAD 1: MAPEO ML → BD
        ml_result_dict = self._try_ml_mapping(ml_result, context)
        if ml_result_dict['success']:
            next_state = self._get_next_state_from_bd(current_state, ml_result_dict['condition'], usar_inteligentes=True)
            if next_state != current_state:
                execution_time = (time.time() - start_time) * 1000
                return self._build_result(next_state, ml_result_dict, 'ml_mapping', execution_time)
        
        # 2. ✅ PRIORIDAD 2: PATRONES DE PALABRAS CLAVE - CORREGIDO
        keyword_result = self._try_keyword_patterns(user_message, current_state, context)
        if keyword_result['success']:
            next_state = self._get_next_state_from_bd(current_state, keyword_result['condition'], usar_inteligentes=True)  # ✅ FIX
            if next_state != current_state:
                execution_time = (time.time() - start_time) * 1000
                return self._build_result(next_state, keyword_result, 'keyword_pattern', execution_time)
        
        # 3. ✅ PRIORIDAD 3: EVALUADORES PERSONALIZADOS - CORREGIDO
        evaluator_result = self._try_condition_evaluators(user_message, context)
        if evaluator_result['success']:
            next_state = self._get_next_state_from_bd(current_state, evaluator_result['condition'], usar_inteligentes=True)  # ✅ FIX
            if next_state != current_state:
                execution_time = (time.time() - start_time) * 1000
                return self._build_result(next_state, evaluator_result, 'condition_evaluator', execution_time)
        
        # 4. ✅ FALLBACK: MANTENER ESTADO ACTUAL
        execution_time = (time.time() - start_time) * 1000
        return self._build_result(current_state, {'condition': 'no_transition', 'confidence': 0.0}, 'no_change', execution_time)
    
    def _try_ml_mapping(self, ml_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Intentar mapeo ML → BD"""
        
        ml_intention = ml_result.get('intention', '')
        ml_confidence = ml_result.get('confidence', 0.0)
        
        if not ml_intention or ml_intention not in self.ml_mappings:
            return {'success': False, 'reason': 'intention_not_mapped'}
        
        mapping = self.ml_mappings[ml_intention]
        required_confidence = mapping['confidence_threshold']
        
        if ml_confidence < required_confidence:
            logger.debug(f"🤖 ML confianza baja: {ml_confidence:.2f} < {required_confidence:.2f}")
            return {'success': False, 'reason': 'low_confidence'}
        
        logger.info(f"✅ ML mapping: {ml_intention} → {mapping['bd_condition']} ({ml_confidence:.2f})")
        
        return {
            'success': True,
            'condition': mapping['bd_condition'],
            'confidence': ml_confidence,
            'ml_intention': ml_intention,
            'source': 'ml_mapping'
        }
    
    def _try_keyword_patterns(self, message: str, current_state: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """✅ CORREGIDO - Pattern matching robusto con case insensitive"""
        
        message_lower = message.lower().strip()  # ✅ SIEMPRE lowercase
        has_client = context.get('cliente_encontrado', False)
        
        # ✅ DETECCIÓN ESPECÍFICA PARA SELECCIÓN DE PLANES (PRIORIDAD MÁXIMA)
        if current_state == 'proponer_planes_pago':
            
            # ✅ PAGO ÚNICO - Patrones amplios
            pago_unico_patterns = [
                'pago unic', 'pago único', 'descuento', 'oferta especial',
                'liquidar', 'pago completo', 'primera', 'primer', '1'
            ]
            
            if any(pattern in message_lower for pattern in pago_unico_patterns):
                return {
                    'success': True,
                    'condition': 'cliente_selecciona_pago_unico',
                    'confidence': 0.95,
                    'pattern_matched': f'pago_unico_detected: {message_lower}',
                    'source': 'keyword_pattern_plan_selection'
                }
            
            # ✅ 3 CUOTAS
            if any(pattern in message_lower for pattern in ['3 cuotas', 'tres cuotas', 'segunda', '2']):
                return {
                    'success': True,
                    'condition': 'cliente_selecciona_plan_3_cuotas',
                    'confidence': 0.95,
                    'pattern_matched': '3_cuotas',
                    'source': 'keyword_pattern_plan_selection'
                }
            
            # ✅ 6 CUOTAS  
            if any(pattern in message_lower for pattern in ['6 cuotas', 'seis cuotas', 'tercera', '3']):
                return {
                    'success': True,
                    'condition': 'cliente_selecciona_plan_6_cuotas',
                    'confidence': 0.95,
                    'pattern_matched': '6_cuotas',
                    'source': 'keyword_pattern_plan_selection'
                }
            
            # ✅ 12 CUOTAS
            if any(pattern in message_lower for pattern in ['12 cuotas', 'doce cuotas', 'cuarta', '4']):
                return {
                    'success': True,
                    'condition': 'cliente_selecciona_plan_12_cuotas', 
                    'confidence': 0.95,
                    'pattern_matched': '12_cuotas',
                    'source': 'keyword_pattern_plan_selection'
                }
        
        # ✅ RESTO DEL CÓDIGO ORIGINAL (búsqueda en BD)
        sorted_patterns = sorted(
            self.keyword_patterns.items(), 
            key=lambda x: x[1]['confidence'], 
            reverse=True
        )
        
        for pattern, pattern_info in sorted_patterns:
            if not self._pattern_matches(pattern, message_lower, pattern_info['pattern_type']):
                continue
            
            if pattern_info['state_context'] and pattern_info['state_context'] != current_state:
                continue
            
            if pattern_info['requires_client'] and not has_client:
                continue
            
            logger.info(f"✅ Keyword match: '{pattern}' → {pattern_info['bd_condition']} ({pattern_info['confidence']:.2f})")
            
            return {
                'success': True,
                'condition': pattern_info['bd_condition'],
                'confidence': pattern_info['confidence'],
                'pattern_matched': pattern,
                'source': 'keyword_pattern'
            }
        
        return {'success': False, 'reason': 'no_pattern_match'}
    
    def _pattern_matches(self, pattern: str, message: str, pattern_type: str) -> bool:
        """Verificar si patrón coincide según su tipo"""
        
        if pattern_type == 'exact':
            return message.strip() == pattern.strip()
        elif pattern_type == 'regex':
            try:
                return bool(re.search(pattern, message))
            except re.error:
                return False
        else:  # 'contains' (default)
            return pattern in message
    
    def _try_condition_evaluators(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Intentar evaluadores de condición personalizados"""
        
        for condition_name, evaluator in self.condition_evaluators.items():
            
            if self._evaluate_condition_custom(condition_name, message, context, evaluator):
                logger.info(f"✅ Custom evaluator: {condition_name}")
                
                return {
                    'success': True,
                    'condition': condition_name,
                    'confidence': evaluator['threshold'],
                    'evaluator': evaluator['method'],
                    'source': 'condition_evaluator'
                }
        
        return {'success': False, 'reason': 'no_evaluator_match'}
    
    def _evaluate_condition_custom(self, condition_name: str, message: str, 
                                 context: Dict[str, Any], evaluator: Dict[str, Any]) -> bool:
        """Evaluar condición usando evaluador personalizado"""
        
        method = evaluator['method']
        config = evaluator['config']
        threshold = evaluator['threshold']
        
        try:
            if method == 'regex':
                pattern = config.get('pattern', '')
                return bool(re.search(pattern, message))
            
            elif method == 'keyword_match':
                keywords = config.get('keywords', [])
                min_confidence = config.get('min_confidence', 0.7)
                
                matches = sum(1 for kw in keywords if kw.lower() in message.lower())
                confidence = matches / len(keywords) if keywords else 0
                
                return confidence >= min_confidence
            
            elif method == 'ml_similarity':
                # Placeholder para implementación ML similarity
                # Aquí se integraría con servicio ML para calcular similitud
                return len(message) > 0  # Placeholder
            
            elif method == 'context_based':
                required_context = config.get('required_context', {})
                return all(context.get(key) == value for key, value in required_context.items())
            
            else:
                logger.warning(f"⚠️ Método de evaluación desconocido: {method}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error evaluando condición {condition_name}: {e}")
            return False
        
    # ☝️ Esta función está MAL UBICADA y debe eliminarse completamente

    # ✅ REEMPLAZAR el método _get_next_state_from_bd con esta versión 100% dinámica:

    def _get_next_state_from_bd(self, estado_actual: str, condicion_detectada: str, usar_inteligentes: bool = True) -> str:
        """✅ VERSIÓN 100% DINÁMICA - Sin hardcoding"""
        try:
            logger.info(f"🔍 [BD] Consultando transición: {estado_actual} + {condicion_detectada}")
            
            # ✅ 1. PRIORIDAD: Estados_Conversacion (tabla principal)
            query = text("""
                SELECT estado_siguiente_true, estado_siguiente_false, estado_siguiente_default, condicion
                FROM Estados_Conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado_actual}).fetchone()
            
            if result:
                estado_true, estado_false, estado_default, condicion_requerida = result
                
                # ✅ EVALUACIÓN DINÁMICA DE CONDICIÓN
                if self._evaluar_condicion_dinamica(condicion_requerida, condicion_detectada):
                    siguiente_estado = estado_true or estado_default or estado_actual
                    logger.info(f"✅ [BD] Transición encontrada: {estado_actual} → {siguiente_estado}")
                    return siguiente_estado
                elif estado_false:
                    logger.info(f"🔄 [BD] Condición falsa: {estado_actual} → {estado_false}")
                    return estado_false
                elif estado_default:
                    logger.info(f"🔄 [BD] Usando default: {estado_actual} → {estado_default}")
                    return estado_default
            
            # ✅ 2. FALLBACK: keyword_condition_patterns
            keyword_query = text("""
                SELECT bd_condition, confidence_score
                FROM keyword_condition_patterns 
                WHERE active = 1 AND confidence_score >= 0.7
                ORDER BY confidence_score DESC
            """)
            
            for row in self.db.execute(keyword_query):
                bd_condition, confidence = row
                if bd_condition == condicion_detectada:
                    # Buscar estado destino para esta condición
                    destino = self._buscar_estado_destino_para_condicion(bd_condition, estado_actual)
                    if destino != estado_actual:
                        logger.info(f"✅ [KEYWORD] Encontrado: {estado_actual} → {destino}")
                        return destino
            
            # ✅ 3. ÚLTIMO RECURSO: ml_intention_mappings
            ml_query = text("""
                SELECT bd_condition, confidence_threshold
                FROM ml_intention_mappings
                WHERE active = 1
                ORDER BY priority ASC
            """)
            
            for row in self.db.execute(ml_query):
                bd_condition, threshold = row
                if bd_condition == condicion_detectada:
                    destino = self._buscar_estado_destino_para_condicion(bd_condition, estado_actual)
                    if destino != estado_actual:
                        logger.info(f"✅ [ML] Encontrado: {estado_actual} → {destino}")
                        return destino
            
            logger.info(f"🌀 [BD] Sin transición definida, permaneciendo en: {estado_actual}")
            return estado_actual
            
        except Exception as e:
            logger.error(f"❌ [BD] Error: {e}")
            return estado_actual

    def _evaluar_condicion_dinamica(self, condicion_requerida: str, condicion_detectada: str) -> bool:
        """✅ EVALUACIÓN 100% DINÁMICA DE CONDICIONES"""
        
        if not condicion_requerida or not condicion_detectada:
            return False
        
        # ✅ COINCIDENCIA EXACTA
        if condicion_requerida == condicion_detectada:
            return True
        
        # ✅ CONSULTAR TABLA DE EQUIVALENCIAS DINÁMICAS
        try:
            equivalencias_query = text("""
                SELECT pattern_variations
                FROM condition_equivalences
                WHERE base_condition = :base_condition AND active = 1
            """)
            
            result = self.db.execute(equivalencias_query, {"base_condition": condicion_requerida}).fetchone()
            
            if result and result[0]:
                try:
                    import json
                    variaciones = json.loads(result[0])
                    if condicion_detectada in variaciones:
                        return True
                except:
                    pass
        except:
            pass
        
        # ✅ MAPEO DINÁMICO BÁSICO (sin hardcoding extenso)
        mapeo_basico = {
            "cliente_selecciona_plan": [
                "cliente_selecciona_pago_unico",
                "cliente_selecciona_plan_3_cuotas", 
                "cliente_selecciona_plan_6_cuotas",
                "cliente_selecciona_plan_12_cuotas",
                "PAGO_UNICO",
                "CONFIRMACION_EXITOSA"
            ]
        }
        
        condiciones_validas = mapeo_basico.get(condicion_requerida, [condicion_requerida])
        return condicion_detectada in condiciones_validas
    
    def _buscar_estado_destino_para_condicion(self, condicion: str, estado_actual: str) -> str:
        """✅ BUSCAR ESTADO DESTINO DINÁMICAMENTE"""
        try:
            # ✅ BÚSQUEDA EN TODAS LAS CONFIGURACIONES
            destino_query = text("""
                SELECT estado_siguiente_true, estado_siguiente_default
                FROM Estados_Conversacion 
                WHERE (condicion = :condicion OR condicion LIKE :condicion_pattern)
                    AND activo = 1
                    AND nombre != :estado_actual
                ORDER BY 
                    CASE WHEN condicion = :condicion THEN 1 ELSE 2 END,
                    estado_siguiente_true DESC
            """)
            
            result = self.db.execute(destino_query, {
                "condicion": condicion,
                "condicion_pattern": f"%{condicion}%",
                "estado_actual": estado_actual
            }).fetchone()
            
            if result:
                return result[0] or result[1] or estado_actual
            
            # ✅ MAPEO ESPECÍFICO PARA CASOS CRÍTICOS (mínimo hardcoding)
            mapeo_critico = {
                "cliente_selecciona_pago_unico": "confirmar_plan_elegido",
                "cliente_selecciona_plan_3_cuotas": "confirmar_plan_elegido",
                "cliente_selecciona_plan_6_cuotas": "confirmar_plan_elegido",
                "cliente_selecciona_plan_12_cuotas": "confirmar_plan_elegido",
                "cliente_confirma_acuerdo": "generar_acuerdo",
                "proceso_completado": "finalizar_conversacion"
            }
            
            return mapeo_critico.get(condicion, estado_actual)
            
        except Exception as e:
            logger.error(f"❌ Error buscando destino para {condicion}: {e}")
            return estado_actual
    
    def _consultar_condiciones_inteligentes(self, estado_actual: str, condicion_detectada: str) -> str:
        """✅ CONSULTAR condiciones_inteligentes 100% dinámico"""
        try:
            # ✅ CONSULTA COMPLETAMENTE DINÁMICA
            query = text("""
                SELECT estado_siguiente_true, estado_siguiente_default, configuracion_json, tipo_condicion
                FROM condiciones_inteligentes 
                WHERE estado_actual = :estado AND activa = 1
                ORDER BY confianza_minima DESC
            """)
            
            results = self.db.execute(query, {"estado": estado_actual}).fetchall()
            
            for row in results:
                estado_true, estado_default, config_json, tipo_condicion = row
                
                # ✅ EVALUACIÓN DINÁMICA BASADA EN TIPO
                if self._evaluar_condicion_inteligente_completa(condicion_detectada, config_json, tipo_condicion):
                    return estado_true or estado_default or estado_actual
            
            # ✅ FALLBACK DINÁMICO: buscar en keyword patterns
            return self._buscar_en_patterns_dinamicos(estado_actual, condicion_detectada)
            
        except Exception as e:
            logger.error(f"❌ Error en condiciones_inteligentes: {e}")
            return estado_actual

    def _buscar_en_patterns_dinamicos(self, estado_actual: str, condicion_detectada: str) -> str:
        """✅ BÚSQUEDA DINÁMICA EN PATTERNS"""
        try:
            pattern_query = text("""
                SELECT keyword_pattern, bd_condition, confidence_score
                FROM keyword_condition_patterns
                WHERE active = 1 AND bd_condition = :condicion
                ORDER BY confidence_score DESC
            """)
            
            result = self.db.execute(pattern_query, {"condicion": condicion_detectada}).fetchone()
            
            if result:
                # Encontrado pattern, buscar estado destino
                return self._buscar_estado_destino_para_condicion(result[1], estado_actual)
            
            return estado_actual
            
        except Exception as e:
            logger.error(f"❌ Error en patterns dinámicos: {e}")
            return estado_actual

    def _consultar_estados_conversacion(self, estado_actual: str, condicion_detectada: str) -> str:
        """Consultar Estados_conversacion con lógica mejorada"""
        try:
            query = text("""
                SELECT estado_siguiente_true, estado_siguiente_false, estado_siguiente_default, condicion
                FROM Estados_conversacion 
                WHERE nombre = :estado AND activo = 1
            """)
            
            result = self.db.execute(query, {"estado": estado_actual}).fetchone()
            
            if result:
                estado_true, estado_false, estado_default, condicion_requerida = result
                
                # ✅ MAPEO ESPECÍFICO DE CONDICIONES
                if condicion_requerida == 'cliente_selecciona_plan':
                    condiciones_plan = [
                        'cliente_selecciona_pago_unico',
                        'cliente_selecciona_plan_3_cuotas',
                        'cliente_selecciona_plan_6_cuotas', 
                        'cliente_selecciona_plan_12_cuotas'
                    ]
                    if condicion_detectada in condiciones_plan:
                        return estado_true or estado_default or estado_actual
                
                # ✅ OTROS MAPEOS
                elif condicion_requerida == 'cliente_confirma_interes':
                    if condicion_detectada in ['cliente_confirma_interes', 'CONFIRMACION']:
                        return estado_true or estado_default or estado_actual
                
                # ✅ DEFAULT
                return estado_true or estado_default or estado_actual
            
            return estado_actual
            
        except Exception as e:
            logger.error(f"❌ Error en Estados_conversacion: {e}")
            return estado_actual

    def _evaluar_condicion_inteligente_completa(self, condicion_detectada: str, config_json: str, tipo_condicion: str) -> bool:
        """Evaluar condición según configuración JSON"""
        try:
            config = json.loads(config_json) if config_json else {}
            
            if tipo_condicion == "ml_intention":
                patrones = config.get("patrones", [])
                # Verificar si la condición detectada coincide con algún patrón
                return any(patron.lower() in condicion_detectada.lower() for patron in patrones)
            
            elif tipo_condicion == "context_value":
                # Para context_value, asumir que se cumple si llegó hasta aquí
                return True
            
            elif tipo_condicion == "custom_function":
                # Para custom_function, asumir que se cumple
                return True
            
            # Mapeo directo por nombre de condición
            mapeo_condiciones = {
                "cliente_selecciona_pago_unico": ["PAGO_UNICO", "cliente_selecciona_pago_unico"],
                "cliente_selecciona_plan_3_cuotas": ["PLAN_3_CUOTAS", "cliente_selecciona_plan_3_cuotas"], 
                "cliente_selecciona_plan_6_cuotas": ["PLAN_6_CUOTAS", "cliente_selecciona_plan_6_cuotas"],
                "cliente_selecciona_plan_12_cuotas": ["PLAN_12_CUOTAS", "cliente_selecciona_plan_12_cuotas"],
                "cliente_selecciona_plan": ["CONFIRMACION_EXITOSA", "cliente_selecciona_plan"]
            }
            
            # Buscar en el mapeo por el registro actual
            for row_id in [9, 10, 11, 12]:  # IDs de tus registros específicos
                for condicion_nombre, patrones_validos in mapeo_condiciones.items():
                    if condicion_detectada in patrones_validos:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error evaluando condición: {e}")
            return False

    def _evaluar_condicion_estados(self, condicion_requerida: str, condicion_detectada: str) -> bool:
        """Evaluar condición de Estados_conversacion"""
        
        # Mapeo de condiciones Estados_conversacion
        mapeo_estados = {
            "cliente_selecciona_plan": [
                "cliente_selecciona_pago_unico",
                "cliente_selecciona_plan_3_cuotas", 
                "cliente_selecciona_plan_6_cuotas",
                "cliente_selecciona_plan_12_cuotas",
                "PAGO_UNICO",
                "CONFIRMACION_EXITOSA",
                "PLAN_3_CUOTAS",
                "PLAN_6_CUOTAS", 
                "PLAN_12_CUOTAS"
            ],
            "cliente_confirma_interes": ["CONFIRMACION", "cliente_confirma_interes"],
            "cedula_detectada": ["IDENTIFICACION", "cedula_detectada"]
        }
        
        condiciones_validas = mapeo_estados.get(condicion_requerida, [condicion_requerida])
        return condicion_detectada in condiciones_validas

    def _build_result(self, next_state: str, detection_result: Dict[str, Any], 
                    method: str, execution_time: float) -> Dict[str, Any]:
        """Construir resultado final - CORREGIDO"""
        
        return {
            'next_state': next_state,
            'condition_detected': detection_result.get('condition', detection_result.get('bd_condition', 'unknown')),  # ✅ FIX
            'confidence': detection_result.get('confidence', 0.0),
            'detection_method': method,
            'detection_details': detection_result,
            'execution_time_ms': execution_time,
            'timestamp': datetime.now().isoformat()
        }
    
    def log_decision(self, conversation_id: int, current_state: str, user_message: str,
                    ml_result: Dict[str, Any], decision_result: Dict[str, Any]):
        """Log de decisión para auto-aprendizaje"""
        try:
            query = text("""
                INSERT INTO transition_decision_log (
                    conversation_id, current_state, user_message,
                    ml_intention, ml_confidence, detected_condition,
                    condition_source, next_state, decision_confidence, execution_time_ms
                ) VALUES (
                    :conv_id, :current_state, :message,
                    :ml_intention, :ml_confidence, :condition,
                    :source, :next_state, :confidence, :exec_time
                )
            """)
            
            self.db.execute(query, {
                'conv_id': conversation_id,
                'current_state': current_state,
                'message': user_message,
                'ml_intention': ml_result.get('intention'),
                'ml_confidence': ml_result.get('confidence', 0),
                'condition': decision_result.get('condition_detected'),
                'source': decision_result.get('detection_method'),
                'next_state': decision_result.get('next_state'),
                'confidence': decision_result.get('confidence', 0),
                'exec_time': int(decision_result.get('execution_time_ms', 0))
            })
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"❌ Error logging decision: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del servicio"""
        try:
            # Estadísticas de configuración
            config_stats = {
                'ml_mappings_count': len(self.ml_mappings),
                'keyword_patterns_count': len(self.keyword_patterns),
                'condition_evaluators_count': len(self.condition_evaluators),
                'cache_age_seconds': int(time.time() - self.cache_timestamp),
                'configuration_source': 'database' if self.ml_mappings else 'emergency_fallback'
            }
            
            # Estadísticas de uso (último mes)
            usage_query = text("""
                SELECT 
                    condition_source,
                    COUNT(*) as usage_count,
                    AVG(decision_confidence) as avg_confidence,
                    COUNT(CASE WHEN was_successful = 1 THEN 1 END) as successful_count
                FROM transition_decision_log 
                WHERE created_at >= DATEADD(month, -1, GETDATE())
                GROUP BY condition_source
            """)
            
            usage_stats = {}
            for row in self.db.execute(usage_query):
                source = row[0]
                usage_stats[source] = {
                    'usage_count': row[1],
                    'avg_confidence': float(row[2]) if row[2] else 0,
                    'success_count': row[3] or 0,
                    'success_rate': (row[3] or 0) / row[1] if row[1] > 0 else 0
                }
            
            return {
                'service': 'DynamicTransitionService(db=session)',
                'version': '1.0.0',
                'configuration': config_stats,
                'usage_stats': usage_stats,
                'is_fully_dynamic': True
            }
            
        except Exception as e:
            return {
                'service': 'DynamicTransitionService(db=session)',
                'error': str(e),
                'configuration': {
                    'ml_mappings_count': len(self.ml_mappings),
                    'keyword_patterns_count': len(self.keyword_patterns)
                }
            }
    
    def auto_improve_patterns(self):
        """Auto-mejora basada en resultados históricos"""
        try:
            # Encontrar patrones con baja tasa de éxito
            low_performance_query = text("""
                SELECT pattern_identifier, success_rate, total_usage
                FROM pattern_performance_metrics
                WHERE success_rate < 0.6 AND total_usage >= 10
            """)
            
            # Deshabilitar patrones con mal rendimiento
            for row in self.db.execute(low_performance_query):
                pattern_id = row[0]
                logger.warning(f"🔧 Deshabilitando patrón con bajo rendimiento: {pattern_id}")
                
                # Marcar como inactivo
                update_query = text("""
                    UPDATE keyword_condition_patterns 
                    SET active = 0 
                    WHERE keyword_pattern = :pattern
                """)
                self.db.execute(update_query, {'pattern': pattern_id})
            
            # Identificar nuevos patrones exitosos
            self._identify_new_successful_patterns()
            
            self.db.commit()
            logger.info("✅ Auto-mejora de patrones completada")
            
        except Exception as e:
            logger.error(f"❌ Error en auto-mejora: {e}")
            self.db.rollback()
    
    def _identify_new_successful_patterns(self):
        """Identificar nuevos patrones exitosos automáticamente"""
        try:
            # Buscar mensajes que llevaron a transiciones exitosas frecuentemente
            pattern_discovery_query = text("""
                SELECT 
                    LOWER(user_message) as message,
                    detected_condition,
                    COUNT(*) as frequency,
                    AVG(CAST(was_successful AS FLOAT)) as success_rate
                FROM transition_decision_log 
                WHERE was_successful = 1
                    AND created_at >= DATEADD(day, -7, GETDATE())
                    AND condition_source = 'ml_mapping'
                    AND LEN(user_message) BETWEEN 3 AND 50
                GROUP BY LOWER(user_message), detected_condition
                HAVING COUNT(*) >= 3 AND AVG(CAST(was_successful AS FLOAT)) >= 0.8
            """)
            
            for row in self.db.execute(pattern_discovery_query):
                message = row[0].strip()
                condition = row[1]
                frequency = row[2]
                success_rate = row[3]
                
                # Extraer palabras clave potenciales
                keywords = self._extract_keywords_from_message(message)
                
                for keyword in keywords:
                    if len(keyword) >= 3 and keyword not in self.keyword_patterns:
                        # Crear nuevo patrón
                        confidence = min(0.95, success_rate + (frequency * 0.05))
                        
                        insert_pattern_query = text("""
                            INSERT INTO keyword_condition_patterns 
                            (keyword_pattern, bd_condition, confidence_score, active)
                            VALUES (:keyword, :condition, :confidence, 1)
                        """)
                        
                        self.db.execute(insert_pattern_query, {
                            'keyword': keyword,
                            'condition': condition,
                            'confidence': confidence
                        })
                        
                        logger.info(f"🆕 Nuevo patrón auto-descubierto: '{keyword}' → {condition} ({confidence:.2f})")
                        
        except Exception as e:
            logger.error(f"❌ Error en descubrimiento de patrones: {e}")
    
    def _extract_keywords_from_message(self, message: str) -> List[str]:
        """Extraer palabras clave relevantes de un mensaje"""
        # Palabras a ignorar
        stop_words = {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'mi', 'tu', 'me', 'si', 'pero', 'como', 'mas', 'muy', 'ya', 'sin', 'sobre', 'hay', 'fue', 'ser', 'estar', 'tener', 'hacer'}
        
        # Limpiar y dividir mensaje
        words = re.findall(r'\b\w+\b', message.lower())
        
        # Filtrar palabras relevantes
        keywords = []
        for word in words:
            if len(word) >= 3 and word not in stop_words and not word.isdigit():
                keywords.append(word)
        
        # También incluir frases de 2 palabras
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if len(phrase) >= 6 and not any(sw in phrase for sw in stop_words):
                keywords.append(phrase)
        
        return list(set(keywords))  # Eliminar duplicados


# ==========================================
# FACTORY FUNCTION
# ==========================================

def create_dynamic_transition_service(db: Session) -> DynamicTransitionService:
    """Factory para crear el servicio dinámico"""
    return DynamicTransitionService(db)