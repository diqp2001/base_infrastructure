"""
BaseFactory — the application's engine and session on the configured database (settings.get_database_url).

Schema management (2026-11-23): the schema is managed by Alembic migrations (alembic.ini,
src/infrastructure/database/migrations/), applied explicitly with ``alembic upgrade head`` — never by the application.
Start-up only REPORTS the migration status (a warning when the database is not at the head revision); it no longer
runs create_all or ALTER TABLE. See docs/development/DATABASE_MIGRATIONS.md.

``initialize_database_and_create_all_tables`` stays an explicit, opt-in bootstrap (create_all: creates missing tables,
never alters one) for scratch / test databases; the pre-Alembic upgrades of an old database are
``legacy_schema.reconcile`` (run before ``alembic stamp head``).
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.database.settings import get_database_url
from src.infrastructure.models import ModelBase as Base

logger = logging.getLogger(__name__)


class BaseFactory:
    """
    The engine, session and model Base of one database.
    """
    def __init__(self, db_type: str):
        database_url = get_database_url(db_type)
        self.engine = create_engine(database_url)
        self.Base = Base

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.SessionLocal = SessionLocal()
        self.schema_status = self._report_schema_status()

    def _report_schema_status(self):
        """The database's migration status (read only); a warning when it is not at the head revision."""
        try:
            from src.infrastructure.database.migration_status import status
            s = status(self.engine)
        except Exception as e:                                   # never block start-up on the check itself
            logger.warning(f"Schema status unavailable: {e}")
            return None
        if not s.up_to_date:
            logger.warning(s.message())
            print(f"Schema warning: {s.message()}")
        return s

    def _migrate_schema(self):
        """The pre-Alembic additive upgrades (legacy_schema.reconcile) — explicit only, never run at start-up."""
        from src.infrastructure.database.legacy_schema import reconcile
        reconcile(self.engine)

    def initialize_database_and_create_all_tables(self):
        """Explicit bootstrap of a scratch / test database (create_all: creates missing tables, never alters one).
        Application databases are created and changed by Alembic migrations."""
        self.Base.metadata.create_all(bind=self.engine)

    def drop_all_tables(self):
        self.Base.metadata.drop_all(self.engine)
        self.SessionLocal.commit()
