"""
Schema migration: Strategy / Universe domain (2026-11-19).

Brings a database created before the Strategy / Universe models to the new shape, keeping every id:

1. ``universes``            the former backtest Universe table (name, creation_date, description) becomes the parent
                            universe table (name, description, universe_type, version, created_at, updated_at);
2. ``investment_universes`` becomes a child of ``universes`` (joined inheritance): each row gets its parent row with
                            the SAME id (universe_type 'InvestmentUniverse'), the child keeps entity_type /
                            currency_id; the foreign keys onto it (universe_constituents, model trainings) are kept;
3. ``strategies``           filled from ``strategy_configurations`` (same ids; project_key -> strategy_type, same
                            content hash); the old table is left in place, unused;
4. ``strategy_experiments`` configuration_id / configuration_hash / project_key -> strategy_id / strategy_hash /
                            strategy_type (same ids).
5. strategy parameters      the strategy's parameters leave the strategies row (JSON ``sections`` + typed columns
                            bar_frequency, bar_size, model_type, training_window, retrain_every_days,
                            prediction_horizon): one strategy_parameter_values row per parameter (catalog
                            strategy_parameters), then those columns are dropped.
New tables (universe_financial_assets, universe_factors, strategies) are created by ``create_all``.

It is NOT run automatically (``BaseFactory._migrate_schema`` only warns): it rebuilds tables, so on SQL Server it is
run explicitly, after a COPY_ONLY backup, in ONE transaction (nothing changes when a step fails):

    python -m src.infrastructure.database.strategy_universe_migration                 # dry run: what would change
    python -m src.infrastructure.database.strategy_universe_migration --apply         # backup, then migrate

Database selection: the usual settings (DB_NAME / DB_ODBC_CONNECTION_STRING, default base_infra).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

LEGACY_UNIVERSE_COLUMN = "creation_date"          # only the former backtest universes table has it


@dataclass
class MigrationReport:
    steps: List[str] = field(default_factory=list)
    applied: bool = False
    backup: Optional[str] = None

    @property
    def pending(self) -> bool:
        return bool(self.steps)

    def summary(self) -> str:
        if not self.steps:
            return "strategy / universe schema: up to date"
        head = "applied" if self.applied else "pending"
        return f"strategy / universe schema ({head}):\n  - " + "\n  - ".join(self.steps)


# -- detection ---------------------------------------------------------------------------------------------------------
def _columns(inspector, table: str) -> set:
    return {c["name"] for c in inspector.get_columns(table)}


def plan(engine: Engine) -> MigrationReport:
    """The steps the database still needs (empty when it already has the new shape)."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    report = MigrationReport()
    if "universes" in tables and LEGACY_UNIVERSE_COLUMN in _columns(inspector, "universes"):
        report.steps.append("universes: former backtest table -> parent universe table")
    if "investment_universes" in tables and "name" in _columns(inspector, "investment_universes"):
        report.steps.append("investment_universes: child of universes (same ids, parent rows created)")
    if "strategy_configurations" in tables:
        with engine.connect() as conn:
            old = conn.execute(text("SELECT COUNT(*) FROM strategy_configurations")).scalar() or 0
            new = (conn.execute(text("SELECT COUNT(*) FROM strategies")).scalar() or 0) if "strategies" in tables else 0
        if old and not new:
            report.steps.append(f"strategies: {old} strategy configuration version(s) copied (same ids)")
    if "strategy_experiments" in tables and "configuration_id" in _columns(inspector, "strategy_experiments"):
        report.steps.append("strategy_experiments: configuration_id -> strategy_id (same ids)")
    if "strategies" in tables and "sections" in _columns(inspector, "strategies"):
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM strategies")).scalar() or 0
        report.steps.append(f"strategy parameters: {n} strategy version(s) -> strategy_parameter_values rows "
                            f"(sections / typed columns dropped from strategies)")
    return report


# -- helpers -----------------------------------------------------------------------------------------------------------
def _mssql(conn: Connection) -> bool:
    return conn.dialect.name == "mssql"


def _rows(conn: Connection, sql: str) -> List[Dict]:
    return [dict(r._mapping) for r in conn.execute(text(sql))]


def _insert(conn: Connection, table: str, rows: List[Dict]) -> None:
    if not rows:
        return
    cols = list(rows[0])
    sql = text(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})")
    identity = _mssql(conn) and _has_identity(conn, table)
    if identity:
        conn.execute(text(f"SET IDENTITY_INSERT {table} ON"))
    conn.execute(sql, rows)
    if identity:
        conn.execute(text(f"SET IDENTITY_INSERT {table} OFF"))


def _has_identity(conn: Connection, table: str) -> bool:
    return bool(conn.execute(text("SELECT OBJECTPROPERTY(OBJECT_ID(:t), 'TableHasIdentity')"), {"t": table}).scalar())


def _foreign_keys_onto(conn: Connection, target: str) -> List[Dict]:
    """[{table, name, columns}] of the foreign keys referencing ``target``."""
    inspector = inspect(conn)
    found = []
    for table in inspector.get_table_names():
        for fk in inspector.get_foreign_keys(table):
            if fk.get("referred_table") == target and table != target:
                found.append({"table": table, "name": fk.get("name"), "columns": fk["constrained_columns"]})
    return found


def _drop_references(conn: Connection, target: str) -> List[Dict]:
    """SQL Server: drop the foreign keys onto ``target`` (a table about to be rebuilt); returns them to restore."""
    references = _foreign_keys_onto(conn, target)
    if _mssql(conn):
        for fk in references:
            conn.execute(text(f"ALTER TABLE {fk['table']} DROP CONSTRAINT {fk['name']}"))
    return references


def _restore_references(conn: Connection, target: str, references: List[Dict]) -> None:
    if not _mssql(conn):                    # SQLite keeps the references by table name
        return
    for fk in references:
        name = fk["name"] or f"fk_{fk['table']}_{'_'.join(fk['columns'])}"
        conn.execute(text(f"ALTER TABLE {fk['table']} ADD CONSTRAINT {name} FOREIGN KEY "
                          f"({', '.join(fk['columns'])}) REFERENCES {target} (id)"))


def _count(conn: Connection, table: str) -> int:
    return int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)


def _recreate(conn: Connection, metadata, table: str) -> None:
    metadata.tables[table].create(conn)


def _drop_empty_new_tables(conn: Connection, metadata, names: List[str]) -> List[str]:
    """Empty tables create_all made against the OLD universes table: dropped here, recreated after."""
    existing = set(inspect(conn).get_table_names())
    dropped = []
    for name in names:
        if name in existing:
            if _count(conn, name):
                raise RuntimeError(f"{name} already holds rows: migrate it by hand")
            metadata.tables[name].drop(conn)
            dropped.append(name)
    return dropped


# -- steps -------------------------------------------------------------------------------------------------------------
def _migrate_universes(conn: Connection, metadata) -> None:
    rows = _rows(conn, "SELECT id, name, description, creation_date FROM universes")
    references = _drop_references(conn, "universes")
    conn.execute(text("DROP TABLE universes"))
    _recreate(conn, metadata, "universes")
    _insert(conn, "universes", [
        {"id": r["id"], "name": r["name"], "description": r["description"], "universe_type": "Universe",
         "version": 1, "created_at": r["creation_date"], "updated_at": r["creation_date"]} for r in rows])
    _restore_references(conn, "universes", references)


def _migrate_investment_universes(conn: Connection, metadata) -> None:
    rows = _rows(conn, "SELECT id, name, description, entity_type, currency_id, created_at, updated_at "
                       "FROM investment_universes ORDER BY id")
    clash = conn.execute(text("SELECT COUNT(*) FROM universes WHERE id IN (SELECT id FROM investment_universes)")
                         ).scalar()
    if clash:
        raise RuntimeError("universes already holds ids used by investment_universes: migrate them by hand")
    _insert(conn, "universes", [
        {"id": r["id"], "name": r["name"], "description": r["description"], "universe_type": "InvestmentUniverse",
         "version": 1, "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows])
    references = _drop_references(conn, "investment_universes")
    if _mssql(conn):
        conn.execute(text("EXEC sp_rename 'investment_universes', 'investment_universes_v0'"))
    else:                                               # SQLite: keep the other tables' references by name
        conn.execute(text("PRAGMA legacy_alter_table = ON"))
        conn.execute(text("ALTER TABLE investment_universes RENAME TO investment_universes_v0"))
        conn.execute(text("PRAGMA legacy_alter_table = OFF"))
    _recreate(conn, metadata, "investment_universes")
    _insert(conn, "investment_universes", [
        {"id": r["id"], "entity_type": r["entity_type"], "currency_id": r["currency_id"]} for r in rows])
    conn.execute(text("DROP TABLE investment_universes_v0"))
    _restore_references(conn, "investment_universes", references)


TYPED_COLUMNS = ("bar_frequency", "bar_size", "model_type", "training_window", "retrain_every_days",
                 "prediction_horizon")


def _write_parameter_rows(conn: Connection, metadata, strategy_id: int, sections: Dict, definition: Dict,
                          catalog: Dict) -> None:
    """One strategy_parameter_values row per parameter of the strategy (catalog rows created when missing)."""
    from src.infrastructure.repositories.mappers.strategy import strategy_parameter_codec as codec
    parameters = metadata.tables["strategy_parameters"]
    values = metadata.tables["strategy_parameter_values"]
    for section, name, value in codec.flatten(sections, definition):
        key = (section, name)
        if key not in catalog:
            found = conn.execute(parameters.select().where(parameters.c.section == section,
                                                            parameters.c.name == name)).first()
            catalog[key] = found.id if found else conn.execute(
                parameters.insert().values(section=section, name=name)).inserted_primary_key[0]
        value_type, value_text, numeric = codec.encode(value)
        conn.execute(values.insert().values(strategy_id=strategy_id, parameter_id=catalog[key], value=value_text,
                                            value_type=value_type, value_numeric=numeric))


def _ensure_parameter_tables(conn: Connection, metadata) -> None:
    existing = set(inspect(conn).get_table_names())
    for name in ("strategy_parameters", "strategy_parameter_values"):
        if name not in existing:
            _recreate(conn, metadata, name)


def _migrate_strategy_parameters(conn: Connection, metadata) -> None:
    """strategies.sections (JSON) + typed columns -> parameter rows; then the columns are dropped."""
    import json
    _ensure_parameter_tables(conn, metadata)
    columns = _columns(inspect(conn), "strategies")
    typed = [c for c in TYPED_COLUMNS if c in columns]
    rows = _rows(conn, f"SELECT id, sections{''.join(', ' + c for c in typed)} FROM strategies ORDER BY id")
    catalog: Dict = {}
    for r in rows:
        if conn.execute(text("SELECT COUNT(*) FROM strategy_parameter_values WHERE strategy_id = :i"),
                        {"i": r["id"]}).scalar():
            continue                                    # already has its rows
        try:
            sections = json.loads(r["sections"] or "{}")
        except ValueError:
            sections = {}
        _write_parameter_rows(conn, metadata, r["id"], sections if isinstance(sections, dict) else {},
                              {c: r[c] for c in typed}, catalog)
    for column in ["sections"] + typed:
        conn.execute(text(f"ALTER TABLE strategies DROP COLUMN {column}"))


def _migrate_strategies(conn: Connection, metadata) -> None:
    import json
    rows = _rows(conn, "SELECT id, name, version, parent_id, project_key, description, status, content_hash, "
                       "sections, created_at, validated_at, locked_at FROM strategy_configurations ORDER BY id")
    sections = {}
    has_sections_column = "sections" in _columns(inspect(conn), "strategies")
    for r in rows:
        r["strategy_type"] = r.pop("project_key")
        text_sections = r["sections"] if has_sections_column else r.pop("sections")
        try:
            sections[r["id"]] = json.loads(text_sections or "{}")
        except ValueError:
            sections[r["id"]] = {}
    _insert(conn, "strategies", rows)
    if not has_sections_column:                         # the parameter-row shape: write the rows now
        _ensure_parameter_tables(conn, metadata)
        catalog: Dict = {}
        for r in rows:
            _write_parameter_rows(conn, metadata, r["id"], sections[r["id"]], {}, catalog)


def _migrate_experiments(conn: Connection, metadata) -> None:
    rows = _rows(conn, "SELECT * FROM strategy_experiments ORDER BY id")
    references = _drop_references(conn, "strategy_experiments")         # backtest_runs.strategy_experiment_id
    conn.execute(text("DROP TABLE strategy_experiments"))
    _recreate(conn, metadata, "strategy_experiments")
    for r in rows:
        r["strategy_id"] = r.pop("configuration_id")
        r["strategy_hash"] = r.pop("configuration_hash")
        r["strategy_type"] = r.pop("project_key")
    _insert(conn, "strategy_experiments", rows)
    _restore_references(conn, "strategy_experiments", references)


def database_name(engine: Engine) -> str:
    """The database the engine really connects to (an ODBC connection string hides it from the URL)."""
    if engine.dialect.name != "mssql":
        return engine.url.database or "?"
    with engine.connect() as conn:
        return conn.exec_driver_sql("SELECT DB_NAME()").scalar()


def backup_database(engine: Engine, label: str = "before_strategy_universe") -> str:
    """SQL Server: COPY_ONLY backup with checksums to the instance's default backup folder, then VERIFYONLY."""
    database = database_name(engine)
    raw = engine.raw_connection()
    try:
        raw.driver_connection.autocommit = True        # BACKUP cannot run inside a transaction
        cursor = raw.cursor()
        folder = cursor.execute("SELECT CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS nvarchar(400))"
                                ).fetchone()[0]
        path = f"{folder.rstrip(chr(92))}\\{database}_{label}_{datetime.now():%Y%m%d_%H%M%S}.bak"
        for sql in (f"BACKUP DATABASE [{database}] TO DISK = N'{path}' WITH COPY_ONLY, CHECKSUM, INIT",
                    f"RESTORE VERIFYONLY FROM DISK = N'{path}' WITH CHECKSUM"):
            cursor.execute(sql)
            while cursor.nextset():                    # read every progress message, or the backup is cut short
                pass
        cursor.close()
    finally:
        raw.close()
    return path


def migrate(engine: Engine, apply: bool = False, backup: bool = True) -> MigrationReport:
    """Dry run unless ``apply``. Applying: backup (SQL Server), then every pending step in one transaction."""
    from src.infrastructure.models import ModelBase
    report = plan(engine)
    if not apply or not report.pending:
        return report
    if backup and engine.dialect.name == "mssql":
        report.backup = backup_database(engine)
    metadata = ModelBase.metadata
    inspector = inspect(engine)
    legacy_universes = ("universes" in inspector.get_table_names()
                        and LEGACY_UNIVERSE_COLUMN in _columns(inspector, "universes"))
    with engine.begin() as conn:
        recreate = []
        if legacy_universes:
            recreate = _drop_empty_new_tables(conn, metadata,
                                              ["universe_financial_assets", "universe_factors",
                                               "strategy_parameter_values", "strategies"])
            _migrate_universes(conn, metadata)
        for name in ("universes", "strategies"):
            if name not in inspect(conn).get_table_names():
                _recreate(conn, metadata, name)
        cols = inspect(conn)
        if "investment_universes" in cols.get_table_names() and "name" in _columns(cols, "investment_universes"):
            _migrate_investment_universes(conn, metadata)
        existing = set(inspect(conn).get_table_names())
        if "strategy_configurations" in existing and _count(conn, "strategy_configurations") \
                and not _count(conn, "strategies"):
            _migrate_strategies(conn, metadata)
        if "strategy_experiments" in existing and "configuration_id" in _columns(inspect(conn), "strategy_experiments"):
            _migrate_experiments(conn, metadata)
        if "sections" in _columns(inspect(conn), "strategies"):
            _migrate_strategy_parameters(conn, metadata)
        for name in reversed(recreate):                 # parents first (strategies before its values)
            if name not in inspect(conn).get_table_names():
                _recreate(conn, metadata, name)
    metadata.create_all(engine)
    report.applied = True
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="back up, then migrate (default: dry run)")
    parser.add_argument("--no-backup", action="store_true", help="skip the COPY_ONLY backup (test databases only)")
    parser.add_argument("--db-type", default="sql_server")
    args = parser.parse_args(argv)
    from sqlalchemy import create_engine

    from src.infrastructure.database.settings import get_database_url
    engine = create_engine(get_database_url(args.db_type))
    report = migrate(engine, apply=args.apply, backup=not args.no_backup)
    print(f"database: {database_name(engine)}")
    if report.backup:
        print(f"backup: {report.backup} (verified)")
    print(report.summary())
    if report.pending and not report.applied:
        print("dry run: nothing changed (add --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
