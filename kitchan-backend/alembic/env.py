import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. PRIMERO: Inyectamos la ruta raíz al sistema para que Python encuentre 'src'
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

# 2. SEGUNDO: Ahora sí podemos importar nuestros modelos porque Python ya entiende la ruta
from src.kitchan.core.database import Base
from src.kitchan.modules.restaurantes.infrastructure.models import \
    RestauranteModel  # noqa
from src.kitchan.modules.usuarios.infrastructure.models import \
    UsuarioModel  # noqa

# Esto es de Alembic por defecto
config = context.config
target_metadata = Base.metadata
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Importamos tu Base y tus modelos para el --autogenerate
from src.kitchan.core.database import Base
from src.kitchan.modules.usuarios.infrastructure.models import \
    UsuarioModel  # noqa


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transactions():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Inyecta el motor asíncrono correctamente para evitar el error de Greenlet."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Ejecuta las migraciones online llamando al loop asíncrono."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
