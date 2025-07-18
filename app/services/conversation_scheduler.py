from datetime import datetime, timedelta
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Dict, Any
import logging

# Import del timeout manager (debe estar en el mismo directorio)
from app.services.conversation_timeout import ConversationTimeoutManager

logger = logging.getLogger(__name__)


class ConversationScheduler:
    """Scheduler para ejecutar auto-cierre periódicamente"""
    
    def __init__(self, session_factory: Callable[[], Session]):
        """
        Inicializar scheduler con factory de sesiones
        
        Args:
            session_factory: Función que retorna una nueva sesión de BD
        """
        self.scheduler = BackgroundScheduler()
        self.session_factory = session_factory
        self._running = False
        
        # Configurar logging para el scheduler
        logging.getLogger('apscheduler').setLevel(logging.WARNING)
        
    def start_scheduler(self):
        """Iniciar scheduler con tareas programadas"""
        if self._running:
            logger.warning("Scheduler ya está ejecutándose")
            return
            
        try:
            # 🕐 Cada hora: proceso de auto-cierre
            self.scheduler.add_job(
                func=self.run_auto_close_process,
                trigger=CronTrigger(minute=0),  # Cada hora en punto
                id='auto_close_conversations',
                name='Auto-close expired conversations',
                replace_existing=True,
                max_instances=1  # Evitar ejecuciones concurrentes
            )
            
            # 🕒 Cada 4 horas: limpieza de logs antiguos  
            self.scheduler.add_job(
                func=self.cleanup_old_data,
                trigger=CronTrigger(hour='*/4', minute=5),  # 5 min después de la hora
                id='cleanup_old_data',
                name='Cleanup old conversation data',
                replace_existing=True,
                max_instances=1
            )
            
            # 🌅 Cada día a las 6 AM: archivado de conversaciones
            self.scheduler.add_job(
                func=self.archive_old_conversations,
                trigger=CronTrigger(hour=6, minute=0),
                id='archive_conversations',
                name='Archive old conversations',
                replace_existing=True,
                max_instances=1
            )
            
            # 📊 Cada día a las 7 AM: generar métricas diarias
            self.scheduler.add_job(
                func=self.generate_daily_metrics,
                trigger=CronTrigger(hour=7, minute=0),
                id='daily_metrics',
                name='Generate daily conversation metrics',
                replace_existing=True,
                max_instances=1
            )
            
            self.scheduler.start()
            self._running = True
            logger.info("✅ Scheduler de conversaciones iniciado exitosamente")
            print("✅ Scheduler de conversaciones iniciado")
            
            # Mostrar próximas ejecuciones
            self._log_next_executions()
            
        except Exception as e:
            logger.error(f"❌ Error iniciando scheduler: {e}")
            print(f"❌ Error iniciando scheduler: {e}")
    
    def run_auto_close_process(self):
        """Ejecutar proceso de auto-cierre"""
        logger.info("🔄 Iniciando proceso de auto-cierre...")
        
        db = None
        try:
            db = self.session_factory()
            timeout_manager = ConversationTimeoutManager(db)
            stats = timeout_manager.process_all_conversations()
            
            logger.info(f"✅ Auto-cierre completado: {stats}")
            print(f"📊 Auto-cierre ejecutado: {stats}")
            
            # Log estadísticas importantes
            if stats.get('closed', 0) > 0:
                logger.warning(f"🔒 Se cerraron {stats['closed']} conversaciones automáticamente")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error en auto-cierre: {e}")
            print(f"❌ Error en auto-cierre: {e}")
            return {"error": str(e)}
            
        finally:
            if db:
                db.close()
    
    def cleanup_old_data(self):
        """Limpiar datos antiguos"""
        logger.info("🗑️ Iniciando limpieza de datos antiguos...")
        
        db = None
        try:
            db = self.session_factory()
            
            # Fecha de corte: 90 días atrás
            cutoff_date = datetime.now() - timedelta(days=90)
            
            # 1. Limpiar logs de timeout muy antiguos
            cleanup_timeout_logs_query = text("""
                DELETE FROM conversation_timeout_events 
                WHERE created_at < :cutoff_date
            """)
            
            result1 = db.execute(cleanup_timeout_logs_query, {"cutoff_date": cutoff_date})
            
            # 2. Limpiar métricas muy antiguas (mantener solo resumen)
            cleanup_metrics_query = text("""
                DELETE FROM conversation_metrics 
                WHERE metric_date < :cutoff_date
                    AND metric_date NOT IN (
                        SELECT DISTINCT DATEADD(month, DATEDIFF(month, 0, metric_date), 0)
                        FROM conversation_metrics
                        WHERE metric_date < :cutoff_date
                    )
            """)
            
            result2 = db.execute(cleanup_metrics_query, {"cutoff_date": cutoff_date})
            
            # 3. Comprimir mensajes antiguos (opcional)
            # Solo mantener primer y último mensaje de conversaciones muy antiguas
            
            db.commit()
            
            cleaned_records = (result1.rowcount if result1.rowcount else 0) + \
                            (result2.rowcount if result2.rowcount else 0)
            
            logger.info(f"✅ Limpieza completada: {cleaned_records} registros eliminados")
            print(f"🗑️ Limpieza completada: {cleaned_records} registros eliminados")
            
            return {"cleaned_records": cleaned_records, "cutoff_date": cutoff_date.isoformat()}
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza: {e}")
            print(f"❌ Error en limpieza: {e}")
            if db:
                db.rollback()
            return {"error": str(e)}
            
        finally:
            if db:
                db.close()
    
    def archive_old_conversations(self):
        """Archivar conversaciones cerradas hace más de 30 días"""
        logger.info("📦 Iniciando archivado de conversaciones...")
        
        db = None
        try:
            db = self.session_factory()
            
            # Fecha de corte: 30 días después del cierre
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Buscar conversaciones para archivar
            conversations_to_archive = db.execute(text("""
                SELECT id FROM conversations 
                WHERE is_active = 0 
                    AND ended_at IS NOT NULL
                    AND ended_at < :cutoff_date
                    AND id NOT IN (SELECT original_conversation_id FROM conversation_archive)
                    AND current_state != 'archived'
            """), {"cutoff_date": cutoff_date}).fetchall()
            
            archived_count = 0
            
            for conv_row in conversations_to_archive:
                try:
                    # Usar procedimiento almacenado para archivar
                    result = db.execute(text("""
                        EXEC sp_archive_conversation 
                        @conversation_id = :conv_id,
                        @closure_reason = 'auto_archive_30_days'
                    """), {"conv_id": conv_row[0]})
                    
                    result_row = result.fetchone()
                    if result_row and result_row[0] == 'SUCCESS':
                        archived_count += 1
                    else:
                        logger.warning(f"⚠️ No se pudo archivar conversación {conv_row[0]}")
                        
                except Exception as e:
                    logger.error(f"❌ Error archivando conversación {conv_row[0]}: {e}")
                    continue
            
            db.commit()
            
            logger.info(f"✅ Archivado completado: {archived_count} conversaciones")
            print(f"📦 Archivado completado: {archived_count} conversaciones")
            
            return {"archived_conversations": archived_count}
            
        except Exception as e:
            logger.error(f"❌ Error en archivado: {e}")
            print(f"❌ Error en archivado: {e}")
            if db:
                db.rollback()
            return {"error": str(e)}
            
        finally:
            if db:
                db.close()
    
    def generate_daily_metrics(self):
        """Generar métricas diarias de conversaciones"""
        logger.info("📊 Generando métricas diarias...")
        
        db = None
        try:
            db = self.session_factory()
            
            yesterday = (datetime.now() - timedelta(days=1)).date()
            
            # Verificar si ya existen métricas para ayer
            existing_metrics = db.execute(text("""
                SELECT COUNT(*) FROM conversation_metrics 
                WHERE metric_date = :date
            """), {"date": yesterday}).scalar()
            
            if existing_metrics > 0:
                logger.info("📊 Métricas ya existen para esta fecha")
                return {"message": "Metrics already exist for this date"}
            
            # Generar métricas por conversación del día anterior
            metrics_query = text("""
                INSERT INTO conversation_metrics (
                    conversation_id, metric_date, total_messages, user_messages, 
                    system_messages, duration_hours, completion_status,
                    negotiation_result, client_type, debt_amount
                )
                SELECT 
                    c.id,
                    :metric_date,
                    COALESCE(msg_stats.total_messages, 0),
                    COALESCE(msg_stats.user_messages, 0),
                    COALESCE(msg_stats.system_messages, 0),
                    CASE 
                        WHEN c.ended_at IS NOT NULL 
                        THEN DATEDIFF(HOUR, c.created_at, c.ended_at)
                        ELSE DATEDIFF(HOUR, c.created_at, GETDATE())
                    END,
                    CASE 
                        WHEN c.current_state IN ('acuerdo_generado', 'conversacion_exitosa') THEN 'completed'
                        WHEN c.current_state = 'conversacion_cerrada' THEN 'timeout'
                        WHEN c.is_active = 0 THEN 'abandoned'
                        ELSE 'active'
                    END,
                    CASE 
                        WHEN c.current_state IN ('acuerdo_generado', 'conversacion_exitosa') THEN 'accepted'
                        WHEN c.current_state IN ('gestionar_objecion', 'cliente_no_encontrado') THEN 'rejected'
                        ELSE 'pending'
                    END,
                    'regular', -- Por ahora tipo fijo, se puede mejorar
                    CASE 
                        WHEN c.context_data IS NOT NULL 
                        THEN TRY_CAST(JSON_VALUE(c.context_data, '$.saldo_total') AS DECIMAL(18,2))
                        ELSE NULL
                    END
                FROM conversations c
                LEFT JOIN (
                    SELECT 
                        conversation_id,
                        COUNT(*) as total_messages,
                        SUM(CASE WHEN sender_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                        SUM(CASE WHEN sender_type = 'system' THEN 1 ELSE 0 END) as system_messages
                    FROM messages 
                    GROUP BY conversation_id
                ) msg_stats ON c.id = msg_stats.conversation_id
                WHERE CAST(c.created_at AS DATE) = :metric_date
            """)
            
            result = db.execute(metrics_query, {"metric_date": yesterday})
            db.commit()
            
            metrics_created = result.rowcount or 0
            
            logger.info(f"✅ Métricas generadas: {metrics_created} registros para {yesterday}")
            print(f"📊 Métricas diarias generadas: {metrics_created} conversaciones")
            
            return {"metrics_created": metrics_created, "date": yesterday.isoformat()}
            
        except Exception as e:
            logger.error(f"❌ Error generando métricas: {e}")
            print(f"❌ Error generando métricas: {e}")
            if db:
                db.rollback()
            return {"error": str(e)}
            
        finally:
            if db:
                db.close()
    
    def run_manual_process(self, process_name: str) -> Dict[str, Any]:
        """Ejecutar proceso manualmente para testing"""
        logger.info(f"🔧 Ejecutando proceso manual: {process_name}")
        
        if process_name == "auto_close":
            return self.run_auto_close_process()
        elif process_name == "cleanup":
            return self.cleanup_old_data()
        elif process_name == "archive":
            return self.archive_old_conversations()
        elif process_name == "metrics":
            return self.generate_daily_metrics()
        else:
            return {"error": f"Proceso desconocido: {process_name}"}
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Obtener estado del scheduler"""
        if not self._running:
            return {"status": "stopped", "jobs": []}
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs_info,
            "scheduler_state": str(self.scheduler.state)
        }
    
    def _log_next_executions(self):
        """Mostrar próximas ejecuciones programadas"""
        try:
            jobs = self.scheduler.get_jobs()
            logger.info("📅 Próximas ejecuciones programadas:")
            print("📅 Próximas ejecuciones:")
            
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    logger.info(f"  • {job.name}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  • {job.name}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Error mostrando próximas ejecuciones: {e}")
    
    def stop_scheduler(self):
        """Detener scheduler"""
        if not self._running:
            logger.warning("Scheduler ya está detenido")
            return
            
        try:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("✅ Scheduler detenido exitosamente")
            print("🛑 Scheduler detenido")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo scheduler: {e}")
            print(f"❌ Error deteniendo scheduler: {e}")
    
    def restart_scheduler(self):
        """Reiniciar scheduler"""
        logger.info("🔄 Reiniciando scheduler...")
        self.stop_scheduler()
        # Pequeña pausa para asegurar que se detiene completamente
        import time
        time.sleep(1)
        self.start_scheduler()
    
    def __del__(self):
        """Destructor - asegurar que el scheduler se detenga"""
        if hasattr(self, '_running') and self._running:
            try:
                self.stop_scheduler()
            except:
                pass  # Ignorar errores en destructor


# ==========================================
# FACTORY FUNCTIONS
# ==========================================

def create_conversation_scheduler(session_factory: Callable[[], Session]) -> ConversationScheduler:
    """Factory function para crear el scheduler"""
    return ConversationScheduler(session_factory)


# ==========================================
# SINGLETON PARA USO GLOBAL (OPCIONAL)
# ==========================================

_global_scheduler: ConversationScheduler = None

def get_global_scheduler() -> ConversationScheduler:
    """Obtener instancia global del scheduler"""
    global _global_scheduler
    if _global_scheduler is None:
        raise RuntimeError("Scheduler global no ha sido inicializado. Llamar set_global_scheduler() primero.")
    return _global_scheduler

def set_global_scheduler(scheduler: ConversationScheduler):
    """Establecer scheduler global"""
    global _global_scheduler
    _global_scheduler = scheduler

def stop_global_scheduler():
    """Detener scheduler global"""
    global _global_scheduler
    if _global_scheduler:
        _global_scheduler.stop_scheduler()
        _global_scheduler = None