from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import engine_from_config

from alembic import context

# Import your models and Base
from app.db.database import Base
from app.models import *  # Import all models for autogenerate

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata for autogenerate
target_metadata = Base.metadata


def get_url():
    """Get database URL from settings."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get URL from environment or use default
    # Pydantic Settings автоматически читает DATABASE_URL из переменных окружения
    # Но для Alembic нужно получить напрямую из os.getenv
    url = os.getenv("DATABASE_URL")
    
    # Если DATABASE_URL не установлен, попробуем получить из настроек приложения
    if not url:
        try:
            from app.core.config import settings
            url = settings.database_url
        except Exception:
            # Fallback на дефолтное значение
            url = "sqlite+aiosqlite:///./pc_place.db"
    
    # Convert async URL to sync for Alembic
    # Alembic works synchronously, so we need sync drivers
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite+pysqlite")
    elif url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using sync engine."""
    configuration = config.get_section(config.config_ini_section, {})
    url = get_url()
    configuration["sqlalchemy.url"] = url
    
    # Use sync engine for Alembic (Alembic works synchronously)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
