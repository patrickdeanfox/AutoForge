"""Alembic environment configuration for AutoForge.

Uses a synchronous psycopg2 connection for migrations while the application
itself uses asyncpg at runtime. DATABASE_URL from db.base is rewritten to
use the psycopg2 driver when running Alembic.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import db.models  # noqa: F401 — registers all models against Base.metadata
from alembic import context

# Import Base and all models so Alembic autogenerate can detect them.
from db.base import DATABASE_URL, Base

# ============================================================
# ALEMBIC CONFIG
# ============================================================
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ============================================================
# URL HELPERS
# ============================================================

def _get_sync_url() -> str:
    """Return a psycopg2-compatible URL for Alembic migrations.

    Alembic runs synchronously, so replace the asyncpg driver with psycopg2.
    The DATABASE_URL env var is checked first so CI and staging can override
    the default without touching alembic.ini.
    """
    url = os.environ.get("DATABASE_URL", DATABASE_URL)
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


# ============================================================
# MIGRATION RUNNERS
# ============================================================

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required).

    Generates SQL to stdout rather than executing it directly — useful for
    review and audit workflows.
    """
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection).

    Creates a synchronous engine, opens a connection, and executes all
    pending migrations inside a transaction.
    """
    # Override the URL from alembic.ini with the resolved sync URL so that
    # the DATABASE_URL env var always wins at runtime.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_sync_url()

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
