"""
Persistence backends for contract and integration tests.

    sqlite      in-memory, foreign keys ON (SQLite ignores them by default, SQL Server does not)
    sql_server  the dedicated test database DB_NAME (must end in "_test"), created if missing and
                reset (drop_all / create_all) once per test session — never the application database

Both expose .engine and .session(); repositories are built through RepositoryFactory as in the
application.
"""

import os
import re
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

TEST_DATABASE_SUFFIX = "_test"
_sql_server_engine = None


def _metadata():
    from src.infrastructure.models import ModelBase
    return ModelBase.metadata


def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _metadata().create_all(engine)
    return engine


def test_database_name() -> str:
    name = os.getenv("DB_NAME", "")
    if not name.endswith(TEST_DATABASE_SUFFIX):
        raise RuntimeError(f"refusing to use database {name!r}: SQL Server tests need DB_NAME=*{TEST_DATABASE_SUFFIX}")
    return name


def _ensure_database_exists(name: str) -> None:
    import pyodbc
    from src.infrastructure.database.settings import _sql_server_connection_string
    master = re.sub(r"DATABASE=[^;]*", "DATABASE=master", _sql_server_connection_string())
    with pyodbc.connect(master, autocommit=True, timeout=15) as conn:
        conn.execute(f"IF DB_ID(N'{name}') IS NULL CREATE DATABASE [{name}]")


def sql_server_engine():
    """Engine on the test database; the schema is rebuilt once per process (test session)."""
    global _sql_server_engine
    if _sql_server_engine is None:
        name = test_database_name()
        _ensure_database_exists(name)
        from src.infrastructure.database.settings import get_database_url
        engine = create_engine(get_database_url("sql_server"), pool_pre_ping=True)
        with engine.connect() as conn:
            from sqlalchemy import text
            actual = conn.execute(text("SELECT DB_NAME()")).scalar()
        if actual != name or not actual.endswith(TEST_DATABASE_SUFFIX):
            raise RuntimeError(f"connected to {actual!r}, expected the test database {name!r}")
        _metadata().drop_all(engine)
        _metadata().create_all(engine)
        _sql_server_engine = engine
    return _sql_server_engine


class Backend:
    """One persistence backend; `session()` gives a fresh session on it."""

    def __init__(self, name: str):
        self.name = name
        self.engine = sqlite_engine() if name == "sqlite" else sql_server_engine()
        if name == "sql_server":
            self.reset()

    def reset(self) -> None:
        """Empty every table (children first) so each SQL Server test starts from a clean schema."""
        test_database_name()
        from sqlalchemy import text
        tables = [t.name for t in reversed(_metadata().sorted_tables)]
        with self.engine.begin() as conn:
            # holdings <-> positions reference each other: no delete order satisfies both, so
            # constraints are suspended for the reset and re-validated afterwards
            for name in tables:
                conn.execute(text(f"ALTER TABLE [{name}] NOCHECK CONSTRAINT ALL"))
            for name in tables:
                conn.execute(text(f"DELETE FROM [{name}]"))
            for name in tables:
                conn.execute(text(f"ALTER TABLE [{name}] WITH CHECK CHECK CONSTRAINT ALL"))

    def session(self) -> Session:
        return Session(self.engine)

    @contextmanager
    def factory(self):
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        session = self.session()
        try:
            yield RepositoryFactory(session), session
        finally:
            session.rollback()
            session.close()

    def dispose(self):
        if self.name == "sqlite":
            self.engine.dispose()
