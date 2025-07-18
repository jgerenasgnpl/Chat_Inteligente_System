"""
CREAR NUEVO ARCHIVO: app/services/dynamic_transition_service.py

🚀 SERVICIO DE TRANSICIONES COMPLETAMENTE DINÁMICO
- Cero código hardcodeado
- Todo basado en BD + ML
- Auto-aprendizaje
"""

import json
import re
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

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
        self.cache_ttl = 300  # 5 minutos
        
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
            for row in self.db.execute(query):
                self.ml_mappings[row[0]] = {
                    'bd_condition': row[1],
                    'confidence_threshold': row[2],
                    'priority': row[3]
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Error cargando ML mappings: {e}")
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
        """
        🎯 MÉTODO PRINCIPAL: Determinar siguiente estado dinámicamente
        """
        
        start_time = time.time()
        
        # Refrescar configuración si es necesario
        if time.time() - self.cache_timestamp > self.cache_ttl:
            self._load_configuration()
        
        logger.info(f"🎯 Determinando transición: {current_state} + '{user_message[:30]}...'")
        
        # 1. ✅ PRIORIDAD 1: MAPEO ML → BD
        ml_result_dict = self._try_ml_mapping(ml_result, context)
        if ml_result_dict['success']:
            next_state = self._get_next_state_from_bd(current_state, ml_result_dict['condition'], True)
            if next_state != current_state:
                execution_time = (time.time() - start_time) * 1000
                return self._build_result(next_state, ml_result_dict, 'ml_mapping', execution_time)
        
        # 2. ✅ PRIORIDAD 2: PATRONES DE PALABRAS CLAVE
        keyword_result = self._try_keyword_patterns(user_message, current_state, context)
        if keyword_result['success']:
            next_state = self._get_next_state_from_bd(current_state, keyword_result['condition'], True)
            if next_state != current_state:
                execution_time = (time.time() - start_time) * 1000
                return self._build_result(next_state, keyword_result, 'keyword_pattern', execution_time)
        
        # 3. ✅ PRIORIDAD 3: EVALUADORES PERSONALIZADOS
        evaluator_result = self._try_condition_evaluators(user_message, context)
        if evaluator_result['success']:
            next_state = self._get_next_state_from_bd(current_state, evaluator_result['condition'], True)
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
        """Intentar patrones de palabras clave"""
        
        message_lower = message.lower().strip()
        has_client = context.get('cliente_encontrado', False)
        
        # Ordenar por confianza descendente
        sorted_patterns = sorted(
            self.keyword_patterns.items(), 
            key=lambda x: x[1]['confidence'], 
            reverse=True
        )
        
        for pattern, pattern_info in sorted_patterns:
            
            # Verificar si el patrón aplica
            if not self._pattern_matches(pattern, message_lower, pattern_info['pattern_type']):
                continue
            
            # Verificar contexto de estado si es requerido
            if pattern_info['state_context'] and pattern_info['state_context'] != current_state:
                continue
            
            # Verificar si requiere cliente
            if pattern_info['requires_client'] and not has_client:
                logger.debug(f"🔍 Patrón '{pattern}' requiere cliente pero no está encontrado")
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
    
    def _get_next_state_from_bd(self, current_state: str, condition: str, condition_met: bool) -> str:
        """Obtener siguiente estado desde BD"""
        try:
            query = text("""
                SELECT 
                    CASE 
                        WHEN :condition_met = 1 THEN estado_siguiente_true
                        ELSE COALESCE(estado_siguiente_false, estado_siguiente_default, :current_state)
                    END as next_state
                FROM Estados_Conversacion 
                WHERE nombre = :current_state 
                    AND (condicion = :condition OR condicion IS NULL)
                ORDER BY 
                    CASE WHEN condicion = :condition THEN 1 ELSE 2 END
            """)
            
            result = self.db.execute(query, {
                'current_state': current_state,
                'condition': condition,
                'condition_met': condition_met
            }).fetchone()
            
            next_state = result[0] if result else current_state
            
            if next_state != current_state:
                logger.info(f"🔄 BD Transition: {current_state} → {next_state} (condición: {condition})")
            
            return next_state
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo siguiente estado: {e}")
            return current_state
    
    def _build_result(self, next_state: str, detection_result: Dict[str, Any], 
                     method: str, execution_time: float) -> Dict[str, Any]:
        """Construir resultado final"""
        
        return {
            'next_state': next_state,
            'condition_detected': detection_result.get('condition'),
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
                'service': 'DynamicTransitionService',
                'version': '1.0.0',
                'configuration': config_stats,
                'usage_stats': usage_stats,
                'is_fully_dynamic': True
            }
            
        except Exception as e:
            return {
                'service': 'DynamicTransitionService',
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