from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool

from alembic import context
import os
import sys

# Añadir la ruta del proyecto al path para poder importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message

# Configuración Alembic
config = context.config

# Interpretar el archivo de configuración para logging de Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Establecer el objetivo de la migración (metadatos de las tablas)
target_metadata = Base.metadata

# Otros valores de configuración, definidos por la necesidad de env.py,
# se pueden adquirir:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    return settings.DATABASE_URI

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()