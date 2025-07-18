set -e

echo "🚀 Iniciando Sistema de Chat Inteligente..."

# Verificar variables de entorno requeridas
: ${SQLSERVER_SERVER:?"❌ SQLSERVER_SERVER no configurado"}
: ${SQLSERVER_DB:?"❌ SQLSERVER_DB no configurado"}

echo "✅ Variables de entorno verificadas"

# Esperar a que SQL Server esté disponible
echo "⏳ Esperando conexión a SQL Server..."
while ! nc -z ${SQLSERVER_SERVER%,*} ${SQLSERVER_SERVER#*,} 2>/dev/null; do
    echo "⏳ SQL Server no disponible, esperando..."
    sleep 2
done
echo "✅ SQL Server conectado"

# Verificar conexión a BD
echo "🔍 Verificando conexión a base de datos..."
python -c "
from app.db.session import test_connection
if test_connection():
    print('✅ Conexión a BD exitosa')
else:
    print('❌ Error de conexión a BD')
    exit(1)
" || exit 1

# Crear tablas si no existen
echo "📋 Verificando/creando tablas..."
python -c "
from app.db.session import create_tables
try:
    create_tables()
    print('✅ Tablas verificadas/creadas')
except Exception as e:
    print(f'⚠️ Error con tablas: {e}')
"

# Inicializar modelos ML si existen
echo "🧠 Inicializando modelos ML..."
python -c "
try:
    from app.services.nlp_service import nlp_service
    print('✅ Modelo ML inicializado')
except Exception as e:
    print(f'⚠️ ML no disponible: {e}')
"

echo "🎉 Sistema listo - ejecutando comando principal..."
exec "$@"