"""
Alembic migrations of the application database (alembic.ini, src/infrastructure/database/migrations/).

SQLite: temporary database files (pytest tmp_path). SQL Server: a scratch database `base_infra_alembic_test`
(created and dropped here, marker sql_server) — never the application database.
"""

import importlib
import os
import pkgutil
import re

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.script import ScriptDirectory
from src.infrastructure.database.migration_status import alembic_config, head_revision, status
from src.infrastructure.models import ModelBase

# model modules deliberately left out of the registry (legacy, never created in the application database, used
# only by legacy mappers) — every other module under src/infrastructure/models must be registered
UNMANAGED_MODEL_MODULES = {
    "src.infrastructure.models.finance.back_testing.back_testing_data_types",
    "src.infrastructure.models.finance.back_testing.enums",
    "src.infrastructure.models.finance.back_testing.financial_assets.symbol",
}


def _sqlite(tmp_path, name="app.db"):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    return url, create_engine(url)


def _tables(engine):
    return set(inspect(engine).get_table_names())


# ── one metadata registry ────────────────────────────────────────────────────────────────────────────────────────

def test_one_metadata_registry_with_each_table_once():
    import src.infrastructure.models as models
    names = [t.name for t in ModelBase.metadata.sorted_tables]
    assert len(names) == len(set(names)) == len(ModelBase.metadata.tables)
    assert "strategy_positions" in names                          # registered with the other models
    # the backtest-tracking Base is a separate SQLite file of its own: no table shared with the application schema
    from src.infrastructure.backtest.models import Base as TrackingBase
    assert TrackingBase.metadata is not ModelBase.metadata
    assert not set(TrackingBase.metadata.tables) & set(ModelBase.metadata.tables)
    assert models.ModelBase is ModelBase


def test_importing_every_model_module_leaves_the_application_metadata_unchanged():
    """Every application model is registered by src/infrastructure/models/__init__.py; importing any other model
    module (e.g. the legacy back-testing ones, on LegacyBackTestingBase) adds nothing to ModelBase.metadata — so the
    schema Alembic sees never depends on which modules a process happened to import."""
    import src.infrastructure.models as models
    from src.infrastructure.models.finance.back_testing.legacy_base import LegacyBackTestingBase
    registered = set(ModelBase.metadata.tables)
    for info in pkgutil.walk_packages(models.__path__, models.__name__ + "."):
        module = importlib.import_module(info.name)
        if info.name in UNMANAGED_MODEL_MODULES:
            assert any(getattr(o, "metadata", None) is LegacyBackTestingBase.metadata for o in vars(module).values())
    added = set(ModelBase.metadata.tables) - registered
    assert not added, f"tables registered only when their module is imported: {sorted(added)}"
    assert not set(LegacyBackTestingBase.metadata.tables) & registered


# ── fresh database ───────────────────────────────────────────────────────────────────────────────────────────────

def test_upgrade_head_creates_the_model_schema_on_an_empty_database(tmp_path):
    url, engine = _sqlite(tmp_path)
    command.upgrade(alembic_config(url), "head")
    assert _tables(engine) == set(ModelBase.metadata.tables) | {"alembic_version"}
    s = status(engine, compare=True)
    assert s.current == s.head == head_revision() and s.up_to_date
    assert s.differences == []                                    # the migrations and the models agree


def test_downgrade_to_base_and_upgrade_again(tmp_path):
    url, engine = _sqlite(tmp_path)
    cfg = alembic_config(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert _tables(engine) == {"alembic_version"}
    assert status(engine).current is None
    command.upgrade(cfg, "head")
    assert status(engine).up_to_date


def test_every_revision_upgrades_and_downgrades_one_step(tmp_path):
    url, engine = _sqlite(tmp_path)
    cfg = alembic_config(url)
    revisions = list(reversed(list(ScriptDirectory.from_config(cfg).walk_revisions())))   # oldest first
    for rev in revisions:
        command.upgrade(cfg, rev.revision)
        assert status(engine).current == rev.revision
        command.downgrade(cfg, "-1")
        assert status(engine).current == rev.down_revision
        command.upgrade(cfg, rev.revision)
    assert status(engine).current == head_revision()


def test_offline_sql_script_renders_for_sql_server(tmp_path, capsys):
    cfg = alembic_config("mssql+pyodbc://")
    command.upgrade(cfg, "head", sql=True)
    sql = capsys.readouterr().out
    assert "CREATE TABLE factor_values" in sql and "IDENTITY" in sql
    assert "ALTER TABLE holdings ADD CONSTRAINT fk_holdings_position_id" in sql      # the cycle, after both tables
    assert "CREATE TABLE alembic_version" in sql


# ── existing databases ───────────────────────────────────────────────────────────────────────────────────────────

def test_autogenerate_never_proposes_dropping_a_table_the_models_do_not_define(tmp_path):
    url, engine = _sqlite(tmp_path)
    command.upgrade(alembic_config(url), "head")
    with engine.begin() as conn:                                  # e.g. strategy_configurations, kept on purpose
        conn.execute(text("CREATE TABLE strategy_configurations (id INTEGER PRIMARY KEY, name VARCHAR(50))"))
        conn.execute(text("CREATE INDEX ix_strategy_configurations_name ON strategy_configurations (name)"))
    assert status(engine, compare=True).differences == []
    cfg = alembic_config(url)                                    # the draft goes to tmp_path, not to versions/
    versions = ScriptDirectory.from_config(cfg).versions
    cfg.set_main_option("version_locations", os.pathsep.join([versions, str(tmp_path)]))
    command.revision(cfg, message="nothing", autogenerate=True, version_path=str(tmp_path), rev_id="9999")
    script = next(tmp_path.glob("*9999*.py")).read_text(encoding="utf-8")
    assert "op.drop_table(" not in script and "drop_index(" not in script


def test_an_existing_database_is_reconciled_then_stamped_without_recreating_tables(tmp_path):
    from src.infrastructure.database.legacy_schema import reconcile
    url, engine = _sqlite(tmp_path)
    ModelBase.metadata.create_all(engine)                         # a database created by create_all before Alembic
    with engine.begin() as conn:                                  # ... whose start-up ALTER added no index (base_infra)
        conn.execute(text("DROP INDEX ix_broker_orders_decision_id"))
        conn.execute(text("INSERT INTO strategy_positions (position_id, data_json, is_active, created_at, updated_at) "
                          "VALUES ('kept', '{}', 1, '2026-01-01', '2026-01-01')"))
    before = status(engine, compare=True)
    assert not before.under_control and before.differences == ["add_index broker_orders.ix_broker_orders_decision_id"]
    reconcile(engine, log=lambda m: None)
    assert status(engine, compare=True).differences == []
    command.stamp(alembic_config(url), "head")                    # adopt: no table created or dropped
    after = status(engine, compare=True)
    assert after.up_to_date and after.differences == []
    with engine.connect() as conn:
        assert conn.execute(text("SELECT position_id FROM strategy_positions")).scalar() == "kept"


# ── application start-up ─────────────────────────────────────────────────────────────────────────────────────────

def test_start_up_reports_the_status_and_never_alters_the_schema(tmp_path, monkeypatch, capsys):
    from src.infrastructure.database import base_factory
    url, engine = _sqlite(tmp_path)
    with engine.begin() as conn:                                  # an old broker_orders table
        conn.execute(text("CREATE TABLE broker_orders (id INTEGER PRIMARY KEY, order_id INTEGER)"))
    monkeypatch.setattr(base_factory, "get_database_url", lambda db_type: url)
    factory = base_factory.BaseFactory("sqlite")
    assert _tables(engine) == {"broker_orders"}                   # no create_all
    assert {c["name"] for c in inspect(engine).get_columns("broker_orders")} == {"id", "order_id"}   # no ALTER
    assert not factory.schema_status.under_control
    assert "not under migration control" in capsys.readouterr().out
    command.upgrade(alembic_config(f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"), "head")
    monkeypatch.setattr(base_factory, "get_database_url",
                        lambda db_type: f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}")
    assert base_factory.BaseFactory("sqlite").schema_status.up_to_date


def test_the_models_still_create_their_schema_for_tests_and_bootstrap():
    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)                         # the in-memory test databases
    assert _tables(engine) == set(ModelBase.metadata.tables)


# ── SQL Server ───────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.sql_server
@pytest.mark.integration
def test_upgrade_and_downgrade_on_sql_server():
    pyodbc = pytest.importorskip("pyodbc")
    from urllib.parse import unquote_plus
    from sqlalchemy.engine import URL
    from src.infrastructure.database.settings import _sql_server_connection_string
    name = "base_infra_alembic_test"
    base = _sql_server_connection_string()
    plain = re.sub(r"(?i)driver=([^;]+)", lambda m: "driver={" + unquote_plus(m.group(1)).strip("{}") + "}", base)
    master = re.sub(r"(?i)database=[^;]*", "Database=master", plain)
    try:
        admin = pyodbc.connect(master, autocommit=True, timeout=10)
    except pyodbc.Error as e:
        pytest.skip(f"SQL Server not reachable: {e}")
    admin.execute(f"IF DB_ID(N'{name}') IS NOT NULL DROP DATABASE [{name}]")
    admin.execute(f"CREATE DATABASE [{name}]")
    try:
        url = URL.create("mssql+pyodbc", query={"odbc_connect": re.sub(r"(?i)database=[^;]*", f"Database={name}", base)})
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT DB_NAME()")).scalar() == name
        with engine.connect() as conn:
            cfg = alembic_config(connection=conn)
            command.upgrade(cfg, "head")
            conn.commit()
        assert _tables(engine) == set(ModelBase.metadata.tables) | {"alembic_version"}
        s = status(engine, compare=True)
        assert s.up_to_date and s.differences == [], s.differences
        with engine.connect() as conn:
            command.downgrade(alembic_config(connection=conn), "base")
            conn.commit()
        assert _tables(engine) == {"alembic_version"}
        engine.dispose()
    finally:
        admin.execute(f"ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")
        admin.execute(f"DROP DATABASE [{name}]")
        admin.close()
