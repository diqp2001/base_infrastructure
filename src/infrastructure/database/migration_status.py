"""
Migration status of a database — read only: its Alembic revision, the head revision, and how its schema differs
from the models (Alembic compare_metadata). Nothing is created, altered or stamped here.

    python -m src.infrastructure.database.migration_status            # the application database (settings)
    python -m src.infrastructure.database.migration_status --url sqlite:///C:/tmp/x.db

Used by BaseFactory at start-up (a warning when the database is not at head: migrations are applied explicitly with
``alembic upgrade head``, never by the application) and before adopting an existing database (docs/development/
DATABASE_MIGRATIONS.md: compare, reconcile, then ``alembic stamp head``).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = ROOT / "alembic.ini"


def alembic_config(url: Optional[str] = None, connection=None):
    """The project's Alembic configuration (alembic.ini), optionally bound to a URL or an open connection."""
    from alembic.config import Config
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["configure_logger"] = False
    if url is not None:
        cfg.set_main_option("sqlalchemy.url", str(url).replace("%", "%%"))
    if connection is not None:
        cfg.attributes["connection"] = connection
    return cfg


def head_revision() -> Optional[str]:
    from alembic.script import ScriptDirectory
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def make_include_object(metadata):
    """Compare only what the models define: a reflected table absent from the models (and its indexes /
    constraints) is never proposed for dropping."""
    def include_object(obj, name, type_, reflected, compare_to):
        if type_ == "table":
            return not (reflected and compare_to is None)
        table = getattr(obj, "table", None)
        if reflected and table is not None and table.name not in metadata.tables:
            return False
        return True
    return include_object


@dataclass
class SchemaStatus:
    current: Optional[str]                    # the database's revision (None: not under Alembic control)
    head: Optional[str]
    differences: List[str] = field(default_factory=list)      # schema vs models (empty when compared and equal)
    compared: bool = False

    @property
    def under_control(self) -> bool:
        return self.current is not None

    @property
    def up_to_date(self) -> bool:
        return self.current is not None and self.current == self.head

    def message(self) -> str:
        if self.up_to_date:
            return f"database schema at revision {self.head} (head)"
        if not self.under_control:
            return ("database not under migration control (no alembic_version): compare it with the models "
                    "(python -m src.infrastructure.database.migration_status), reconcile, then 'alembic stamp head' "
                    "- see docs/development/DATABASE_MIGRATIONS.md")
        return f"database schema at revision {self.current}, head is {self.head}: run 'alembic upgrade head'"


def describe(diff) -> str:
    if isinstance(diff, list):
        return "; ".join(describe(d) for d in diff)
    kind = diff[0]
    if kind in ("add_table", "remove_table"):
        return f"{kind} {diff[1].name}"
    if kind in ("add_column", "remove_column"):
        return f"{kind} {diff[2]}.{diff[3].name}"
    if kind.startswith("modify_"):
        return f"{kind} {diff[2]}.{diff[3]}: {diff[-2]!r} -> {diff[-1]!r}"
    obj = diff[1]
    return f"{kind} {getattr(getattr(obj, 'table', None), 'name', '?')}.{getattr(obj, 'name', None)}"


def status(engine, compare: bool = False) -> SchemaStatus:
    """The database's revision vs head; with ``compare`` also its differences from the models (read only)."""
    from alembic.migration import MigrationContext
    from src.infrastructure.models import ModelBase
    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
        out = SchemaStatus(current=current, head=head_revision())
        if compare:
            from alembic.autogenerate import compare_metadata
            ctx = MigrationContext.configure(conn, opts={
                "compare_type": True, "include_object": make_include_object(ModelBase.metadata)})
            out.differences = [describe(d) for d in compare_metadata(ctx, ModelBase.metadata)]
            out.compared = True
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Migration status of a database (read only)")
    p.add_argument("--url", help="SQLAlchemy URL (default: the application's SQL Server settings)")
    a = p.parse_args(argv)
    from sqlalchemy import create_engine
    from src.infrastructure.database.settings import get_database_url
    engine = create_engine(a.url or get_database_url("sql_server"))
    s = status(engine, compare=True)
    print(f"current revision: {s.current or '(none - not under migration control)'}")
    print(f"head revision:    {s.head}")
    print(f"schema vs models: {len(s.differences)} difference(s)")
    for d in s.differences:
        print(f"  - {d}")
    print(s.message())
    return 0 if s.up_to_date and not s.differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
