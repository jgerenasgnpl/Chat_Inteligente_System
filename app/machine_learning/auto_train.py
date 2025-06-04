import schedule
import time
from datetime import datetime
import os
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from train.train_intention_classifier import EntrenadorML

class AutoTrainer:
    """
    Sistema de entrenamiento automático
    
    LÓGICA:
    1. Se ejecuta en segundo plano como servicio
    2. Revisa periódicamente si hay nuevos datos
    3. Ejecuta reentrenamiento automático
    4. Mantiene historial de modelos
    """
    
    def __init__(self):
        self.carpeta_datos = "data/training/"
        self.carpeta_modelos = "models/"
        self.log_file = "logs/auto_train.log"
        
        # Crear carpetas si no existen
        os.makedirs(self.carpeta_datos, exist_ok=True)
        os.makedirs(self.carpeta_modelos, exist_ok=True)
        os.makedirs("logs", exist_ok=True)
    
    def log_mensaje(self, mensaje):
        """Registrar mensaje en log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {mensaje}\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def verificar_nuevos_datos(self):
        """
        Verificar si hay archivos Excel nuevos para entrenar
        
        LÓGICA:
        - Busca archivos .xlsx en carpeta data/training/
        - Compara fecha de modificación con último entrenamiento
        - Retorna True si hay datos nuevos
        """
        try:
            archivos_excel = []
            for archivo in os.listdir(self.carpeta_datos):
                if archivo.endswith('.xlsx') and 'datos_entrenamiento' in archivo:
                    ruta_completa = os.path.join(self.carpeta_datos, archivo)
                    fecha_mod = os.path.getmtime(ruta_completa)
                    archivos_excel.append((archivo, fecha_mod))
            
            if not archivos_excel:
                self.log_mensaje("No se encontraron archivos de entrenamiento")
                return False, None
            
            # Obtener archivo más reciente
            archivo_reciente = max(archivos_excel, key=lambda x: x[1])
            ruta_archivo = os.path.join(self.carpeta_datos, archivo_reciente[0])
            
            # Verificar si es más reciente que el último modelo
            modelos_existentes = [f for f in os.listdir(self.carpeta_modelos) if f.endswith('.joblib')]
            
            if not modelos_existentes:
                self.log_mensaje(f"No hay modelos previos, entrenar con: {archivo_reciente[0]}")
                return True, ruta_archivo
            
            # Comparar fechas
            modelo_reciente = max(modelos_existentes, key=lambda x: os.path.getmtime(os.path.join(self.carpeta_modelos, x)))
            fecha_ultimo_modelo = os.path.getmtime(os.path.join(self.carpeta_modelos, modelo_reciente))
            
            if archivo_reciente[1] > fecha_ultimo_modelo:
                self.log_mensaje(f"Datos nuevos detectados: {archivo_reciente[0]}")
                return True, ruta_archivo
            else:
                self.log_mensaje("No hay datos nuevos para entrenar")
                return False, None
                
        except Exception as e:
            self.log_mensaje(f"Error verificando datos: {e}")
            return False, None
    
    def ejecutar_entrenamiento_auto(self):
        """
        Ejecutar entrenamiento automático
        
        PROCESO:
        1. Verificar nuevos datos
        2. Ejecutar entrenamiento si hay datos nuevos
        3. Validar modelo generado
        4. Limpiar modelos antiguos (mantener últimos 5)
        """
        self.log_mensaje("🔄 Iniciando verificación automática...")
        
        try:
            # Verificar datos nuevos
            hay_nuevos, ruta_datos = self.verificar_nuevos_datos()
            
            if not hay_nuevos:
                return
            
            # Buscar archivo de estados
            ruta_estados = None
            for archivo in os.listdir(self.carpeta_datos):
                if 'estados_conversacion' in archivo and archivo.endswith('.xlsx'):
                    ruta_estados = os.path.join(self.carpeta_datos, archivo)
                    break
            
            # Ejecutar entrenamiento
            self.log_mensaje("🤖 Iniciando entrenamiento automático...")
            entrenador = EntrenadorML()
            
            exito = entrenador.ejecutar_entrenamiento_completo(
                ruta_datos_excel=ruta_datos,
                ruta_estados_excel=ruta_estados
            )
            
            if exito:
                self.log_mensaje("✅ Entrenamiento automático completado")
                self.limpiar_modelos_antiguos()
            else:
                self.log_mensaje("❌ Entrenamiento automático falló")
                
        except Exception as e:
            self.log_mensaje(f"❌ Error en entrenamiento automático: {e}")
    
    def limpiar_modelos_antiguos(self, mantener=5):
        """
        Mantener solo los últimos N modelos
        
        LÓGICA:
        - Lista todos los modelos .joblib
        - Ordena por fecha de creación
        - Elimina los más antiguos, mantiene solo los últimos N
        """
        try:
            modelos = []
            for archivo in os.listdir(self.carpeta_modelos):
                if archivo.endswith('.joblib'):
                    ruta_completa = os.path.join(self.carpeta_modelos, archivo)
                    fecha_creacion = os.path.getctime(ruta_completa)
                    modelos.append((archivo, fecha_creacion, ruta_completa))
            
            # Ordenar por fecha (más reciente primero)
            modelos.sort(key=lambda x: x[1], reverse=True)
            
            # Eliminar modelos antiguos
            if len(modelos) > mantener:
                for archivo, _, ruta in modelos[mantener:]:
                    os.remove(ruta)
                    self.log_mensaje(f"🗑️ Modelo antiguo eliminado: {archivo}")
                    
        except Exception as e:
            self.log_mensaje(f"Error limpiando modelos: {e}")
    
    def iniciar_servicio(self):
        """
        Iniciar servicio de entrenamiento automático
        
        PROGRAMACIÓN:
        - Cada día a las 2:00 AM → Verificar y entrenar si hay datos nuevos
        - Cada lunes a las 8:00 AM → Entrenamiento forzado semanal
        - Cada hora → Verificación de archivos nuevos (sin entrenar)
        """
        self.log_mensaje("🚀 Iniciando servicio de Auto-Train...")
        
        # Programar tareas
        schedule.every().day.at("02:00").do(self.ejecutar_entrenamiento_auto)
        schedule.every().monday.at("08:00").do(self.ejecutar_entrenamiento_auto)
        schedule.every().hour.do(self.verificar_nuevos_datos)
        
        self.log_mensaje("📅 Programación configurada:")
        self.log_mensaje("   - Entrenamiento diario: 02:00 AM")
        self.log_mensaje("   - Entrenamiento semanal: Lunes 08:00 AM")
        self.log_mensaje("   - Verificación horaria de archivos")
        
        # Loop principal
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
            except KeyboardInterrupt:
                self.log_mensaje("🛑 Servicio Auto-Train detenido por usuario")
                break
            except Exception as e:
                self.log_mensaje(f"❌ Error en servicio: {e}")
                time.sleep(300)  # Esperar 5 minutos antes de continuar

# === EJECUCIÓN ===
if __name__ == "__main__":
    auto_trainer = AutoTrainer()
    auto_trainer.iniciar_servicio()