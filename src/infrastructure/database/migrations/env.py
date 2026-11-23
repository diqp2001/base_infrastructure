"""
Alembic environment of the application database.

target_metadata = the application's ONE declarative registry: ``src.infrastructure.models.ModelBase.metadata``.
Importing ``src.infrastructure.models`` registers every application model (the package imports them all), so the
metadata is complete before autogenerate compares it. No table is defined here.

Database URL (no URL in alembic.ini), first found:
    1. ``alembic -x url=<SQLAlchemy URL>``                    (e.g. -x url=sqlite:///C:/tmp/scratch.db)
    2. ``config.attributes['connection']`` / ``sqlalchemy.url`` set programmatically (tests)
    3. the DATABASE_URL environment variable                 (a migration-only override)
    4. the application's SQL Server URL: settings.get_database_url('sql_server') — the DB_* variables
       (DB_ODBC_CONNECTION_STRING, DB_HOST / DB_NAME / ...), default the Windows localhost base_infra

Safety: autogenerate never proposes dropping a table the models do not define (or that table's indexes /
constraints) — e.g. strategy_configurations, kept on purpose by the strategy / universe migration. Dropping a table
is written by hand in a reviewed migration.
SQLite: ALTER TABLE is limited, so migrations are rendered / run in batch mode there (render_as_batch).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.infrastructure.database.migration_status import make_include_object
from src.infrastructure.models import ModelBase   # registers every application model on ModelBase.metadata

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = ModelBase.metadata


def database_url():
    url = context.get_x_argument(as_dictionary=True).get("url") or config.get_main_option("sqlalchemy.url")
    if url:
        return url
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    from src.infrastructure.database.settings import get_database_url
    return get_database_url("sql_server")


# autogenerate compares only what the models define: a reflected table absent from the models (and its indexes /
# constraints) is left alone instead of being dropped (the same rule as migration_status)
include_object = make_include_object(target_metadata)


def _configure(**kwargs):
    context.configure(target_metadata=target_metadata, include_object=include_object, compare_type=True,
                      compare_server_default=False, **kwargs)


def run_migrations_offline() -> None:
    """``alembic upgrade head --sql``: the SQL script, without connecting."""
    url = database_url()
    _configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"},
               render_as_batch=str(url).startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:                       # a connection handed over by the caller (tests)
        _configure(connection=connection, render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        _configure(connection=connection, render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
