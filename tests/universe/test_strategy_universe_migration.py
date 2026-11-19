"""
The Strategy / Universe schema migration on a SQLite database built in the OLD shape (former backtest universes,
investment_universes with its own name, strategy_configurations, strategy_experiments with configuration_id):
every id and link survives, the ORM then reads it, and the start-up hook only reports it.
"""

import json

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.domain.entities.strategy.strategy import content_hash
from src.infrastructure.database.strategy_universe_migration import migrate, plan

OLD_SCHEMA = [
    "CREATE TABLE universes (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE, creation_date DATE NOT NULL, "
    "description TEXT)",
    "CREATE TABLE investment_universes (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE, description TEXT, "
    "entity_type VARCHAR(100), currency_id INTEGER, created_at DATETIME, updated_at DATETIME)",
    "CREATE TABLE universe_constituents (id INTEGER PRIMARY KEY, universe_id INTEGER NOT NULL "
    "REFERENCES investment_universes(id), entity_id INTEGER NOT NULL, entity_type VARCHAR(100) NOT NULL, "
    "start_date DATE NOT NULL, end_date DATE, weight FLOAT, created_at DATETIME, updated_at DATETIME)",
    "CREATE TABLE strategy_configurations (id INTEGER PRIMARY KEY, name VARCHAR(200) NOT NULL, version INTEGER NOT NULL, "
    "parent_id INTEGER REFERENCES strategy_configurations(id), project_key VARCHAR(100) NOT NULL, description TEXT, "
    "status VARCHAR(20) NOT NULL, content_hash VARCHAR(64) NOT NULL, sections TEXT NOT NULL, created_at DATETIME, "
    "validated_at DATETIME, locked_at DATETIME)",
    "CREATE TABLE strategy_experiments (id INTEGER PRIMARY KEY, configuration_id INTEGER NOT NULL "
    "REFERENCES strategy_configurations(id), configuration_hash VARCHAR(64) NOT NULL, project_key VARCHAR(100) NOT NULL, "
    "kind VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL, results_dir VARCHAR(500), log_path VARCHAR(500), "
    "pid INTEGER, host VARCHAR(200), created_at DATETIME, started_at DATETIME, finished_at DATETIME, "
    "heartbeat_at DATETIME, error TEXT, provenance TEXT, summary TEXT)",
    "CREATE INDEX ix_strategy_experiments_status ON strategy_experiments (status)",
]
SECTIONS = {"model": {"n_trials": 20}}
HASH = content_hash("cross_sectional", SECTIONS)


@pytest.fixture
def old_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        for ddl in OLD_SCHEMA:
            conn.execute(text(ddl))
        conn.execute(text("INSERT INTO investment_universes VALUES (5, 'DIA holdings', 'DIA', 'CompanyShare', 1, "
                          "'2026-11-10 00:00:00', '2026-11-10 00:00:00'), (9, 'stm_us_banks_10m', NULL, "
                          "'CompanyShare', NULL, NULL, NULL)"))
        conn.execute(text("INSERT INTO universe_constituents (id, universe_id, entity_id, entity_type, start_date, "
                          "weight) VALUES (1, 5, 101, 'CompanyShare', '2025-01-01', 0.25)"))
        conn.execute(text("INSERT INTO strategy_configurations VALUES (3, 'csm', 1, NULL, 'cross_sectional', 'd', "
                          f"'locked', '{HASH}', :s, NULL, NULL, NULL), (4, 'csm', 2, 3, 'cross_sectional', 'd', "
                          f"'draft', '{HASH}', :s, NULL, NULL, NULL)"), {"s": json.dumps(SECTIONS)})
        conn.execute(text(f"INSERT INTO strategy_experiments (id, configuration_id, configuration_hash, project_key, "
                          f"kind, status) VALUES (7, 3, '{HASH}', 'cross_sectional', 'backtest', 'succeeded')"))
    from src.infrastructure.models import ModelBase
    ModelBase.metadata.create_all(engine)              # what BaseFactory does first: new tables appear, old untouched
    yield engine
    engine.dispose()


def test_the_old_shape_is_detected_and_only_reported(old_db):
    report = plan(old_db)
    assert len(report.steps) == 4 and report.pending
    dry = migrate(old_db)                                                         # dry run by default
    assert not dry.applied and plan(old_db).steps == report.steps


def test_the_migration_keeps_every_id_and_link(old_db):
    report = migrate(old_db, apply=True, backup=False)
    assert report.applied and not plan(old_db).pending
    columns = {t: {c["name"] for c in inspect(old_db).get_columns(t)}
               for t in ("universes", "investment_universes", "strategy_experiments")}
    assert "creation_date" not in columns["universes"] and "universe_type" in columns["universes"]
    assert "name" not in columns["investment_universes"]
    assert "strategy_id" in columns["strategy_experiments"] and "configuration_id" not in columns["strategy_experiments"]

    from src.domain.entities.universe.investment_universe import InvestmentUniverse
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    f = RepositoryFactory(sessionmaker(bind=old_db)())
    dia = f.investment_universe_local_repo.get_by_name("DIA holdings")
    assert isinstance(dia, InvestmentUniverse) and (dia.id, dia.entity_type, dia.currency_id) == (5, "CompanyShare", 1)
    assert f.universe_local_repo.get_by_id(9).name == "stm_us_banks_10m"
    constituents = f.universe_constituent_local_repo
    assert [(c.universe_id, c.weight) for c in constituents.get_by_universe(5)] == [(5, 0.25)]

    v1, v2 = f.strategy_local_repo.get_by_id(3), f.strategy_local_repo.get_by_id(4)
    assert (v1.strategy_type, v1.status, v1.sections, v2.parent_id) == ("cross_sectional", "locked", SECTIONS, 3)
    assert v1.content_hash == HASH                                                 # the experiment still matches
    (experiment,) = f.strategy_experiment_local_repo.get_by_strategy(3)
    assert (experiment.id, experiment.strategy_hash, experiment.status) == (7, HASH, "succeeded")

    # new rows get fresh ids after the copied ones
    from src.domain.entities.universe.universe import Universe
    assert f.universe_local_repo.add(Universe("new")).id > 9
    assert migrate(old_db, apply=True, backup=False).steps == []                   # idempotent
