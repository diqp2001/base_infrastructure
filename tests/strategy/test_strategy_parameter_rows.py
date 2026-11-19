"""
Strategy parameters as rows: strategies (identity) / strategy_parameters (one row per parameter) /
strategy_parameter_values (strategy, parameter, value). Codec round trip, repository storage, SQL queries across
strategies, and the migration of strategies stored with JSON sections + typed columns (file SQLite).
"""

import json

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.domain.entities.strategy.strategy import Strategy, content_hash
from src.infrastructure.repositories.mappers.strategy import strategy_parameter_codec as codec

SECTIONS = {
    "model": {"stm.model": {"model_type": "tft", "lookback": 24, "encoder_length": 16,
                            "params": {"hidden_dim": 32, "dropout": 0.1, "device": "cpu"}},
              "flag": True, "nothing": None, "ratio": 1e-05},
    "factors": {"stm.features": {"macd_combinations": [[3, 9], [6, 18]], "return_horizons": [1, 3, 6]}},
    "risk": {},
    "strategy": {"a/b": "slash", "t~ilde": "tilde", "": "empty key", "nested": {"empty": {}}},
}


# ── codec ────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_every_leaf_is_one_row_and_the_sections_rebuild_exactly():
    rows = codec.flatten(SECTIONS, {"model_type": "tft", "training_window": 390, "bar_size": None})
    names = {(s, n) for s, n, _ in rows}
    assert ("model", "stm.model/params/hidden_dim") in names and ("model", "flag") in names
    assert ("factors", "stm.features/macd_combinations") in names            # a list is one value
    assert ("risk", "") in names                                              # an empty section is kept
    assert ("strategy", "a~1b") in names and ("strategy", "t~0ilde") in names and ("strategy", "~e") in names
    assert ("definition", "model_type") in names and ("definition", "bar_size") not in names
    encoded = [(s, n, codec.decode(*codec.encode(v)[:2])) for s, n, v in rows]
    sections, definition = codec.unflatten(encoded)
    assert sections == SECTIONS and definition == {"model_type": "tft", "training_window": 390}


@pytest.mark.parametrize("value,kind", [(None, "null"), (True, "bool"), (7, "int"), (0.1, "float"), (1e-05, "float"),
                                        ("x", "str"), ([1, [2, 3]], "json"), ({}, "json")])
def test_values_keep_their_type(value, kind):
    value_type, value_text, numeric = codec.encode(value)
    assert value_type == kind and codec.decode(value_type, value_text) == value
    assert (numeric is not None) == (kind in ("int", "float"))


# ── repository ───────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def repo(tmp_path):
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.local_repo.strategy.strategy_repositories import StrategyRepository
    engine = create_engine(f"sqlite:///{tmp_path / 'params.db'}")
    ModelBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield StrategyRepository(session)
    session.close()
    engine.dispose()


def test_the_strategies_table_holds_identity_only():
    from src.infrastructure.models import ModelBase
    columns = set(ModelBase.metadata.tables["strategies"].columns.keys())
    assert not columns & {"sections", "bar_frequency", "bar_size", "model_type", "training_window",
                          "retrain_every_days", "prediction_horizon"}
    assert set(ModelBase.metadata.tables["strategy_parameter_values"].columns.keys()) >= {
        "strategy_id", "parameter_id", "value"}


def test_a_strategy_is_stored_as_parameter_rows_and_rebuilt(repo):
    s = repo.add(Strategy("stm", "spatio_temporal_momentum_project_10m", SECTIONS, model_type="tft",
                          training_window=390, retrain_every_days=1, bar_frequency="10m"))
    again = repo.get_by_id(s.id)
    assert again.sections == SECTIONS and again.content_hash == s.content_hash
    assert (again.model_type, again.training_window, again.bar_frequency, again.bar_size) == ("tft", 390, "10m",
                                                                                              None)
    n_rows = repo.session.execute(text("SELECT COUNT(*) FROM strategy_parameter_values WHERE strategy_id = :i"),
                                  {"i": s.id}).scalar()
    assert n_rows == len(codec.flatten(SECTIONS, {"model_type": "tft", "training_window": 390,
                                                  "retrain_every_days": 1, "bar_frequency": "10m"}))
    # an update replaces the rows (no leftovers)
    again.update(sections={"risk": {"split_guard": {"tolerance": 0.05}}}, training_window=200)
    repo.update(again)
    third = repo.get_by_id(s.id)
    assert third.risk == {"split_guard": {"tolerance": 0.05}} and third.training_window == 200
    assert repo.session.execute(text(
        "SELECT COUNT(*) FROM strategy_parameter_values v JOIN strategy_parameters p ON p.id = v.parameter_id "
        "WHERE v.strategy_id = :i AND p.section = 'risk' AND p.name = ''"), {"i": s.id}).scalar() == 0


def test_parameters_are_shared_and_queryable_across_strategies(repo):
    a = repo.add(Strategy("a", "p", {"model": {"lookback": 24}}, training_window=390))
    b = repo.add(Strategy("b", "p", {"model": {"lookback": 60}}, training_window=120))
    assert repo.session.execute(text("SELECT COUNT(*) FROM strategy_parameters WHERE section = 'model' "
                                     "AND name = 'lookback'")).scalar() == 1          # one catalog row
    assert repo.parameter_values("model", "lookback") == {a.id: 24, b.id: 60}
    wide = repo.session.execute(text(
        "SELECT s.name FROM strategies s JOIN strategy_parameter_values v ON v.strategy_id = s.id "
        "JOIN strategy_parameters p ON p.id = v.parameter_id "
        "WHERE p.section = 'definition' AND p.name = 'training_window' AND v.value_numeric > 200")).scalars().all()
    assert wide == ["a"]
    with pytest.raises(IntegrityError):                                      # one value per strategy / parameter
        param = repo.session.execute(text("SELECT id FROM strategy_parameters WHERE name = 'lookback'")).scalar()
        repo.session.execute(text("INSERT INTO strategy_parameter_values (strategy_id, parameter_id, value, "
                                  "value_type) VALUES (:s, :p, '1', 'int')"), {"s": a.id, "p": param})
    repo.session.rollback()


def test_listing_strategies_reads_every_parameter_in_one_pass(repo):
    for i in range(5):
        repo.add(Strategy(f"s{i}", "p", {"model": {"lookback": i}}, model_type="tft"))
    assert [s.section("model")["lookback"] for s in repo.get_all()] == [0, 1, 2, 3, 4]
    assert all(s.model_type == "tft" for s in repo.get_versions("s3"))


# ── migration of strategies stored with JSON sections + typed columns ────────────────────────────────────────────

def test_strategies_with_json_sections_are_migrated_to_rows(tmp_path):
    from src.infrastructure.database.strategy_universe_migration import migrate, plan
    from src.infrastructure.models import ModelBase
    engine = create_engine(f"sqlite:///{tmp_path / 'json.db'}")
    ModelBase.metadata.create_all(engine)
    with engine.begin() as conn:                         # the previous shape of strategies
        conn.execute(text("DROP TABLE strategy_parameter_values"))
        conn.execute(text("DROP TABLE strategy_parameters"))
        for column, kind in (("sections", "TEXT"), ("bar_frequency", "VARCHAR(20)"), ("bar_size", "VARCHAR(30)"),
                             ("model_type", "VARCHAR(50)"), ("training_window", "INTEGER"),
                             ("retrain_every_days", "INTEGER"), ("prediction_horizon", "INTEGER")):
            conn.execute(text(f"ALTER TABLE strategies ADD COLUMN {column} {kind}"))
        h = content_hash("p", SECTIONS, {"model_type": "tft", "training_window": 390})
        conn.execute(text("INSERT INTO strategies (id, name, version, strategy_type, description, status, "
                          "content_hash, sections, model_type, training_window) VALUES (4, 'old', 1, 'p', '', "
                          "'locked', :h, :s, 'tft', 390)"), {"h": h, "s": json.dumps(SECTIONS)})
    assert any("strategy parameters" in step for step in plan(engine).steps)
    migrate(engine, apply=True, backup=False)
    assert not plan(engine).pending
    assert "sections" not in {c["name"] for c in inspect(engine).get_columns("strategies")}
    from src.infrastructure.repositories.local_repo.strategy.strategy_repositories import StrategyRepository
    s = StrategyRepository(sessionmaker(bind=engine)()).get_by_id(4)
    assert s.sections == SECTIONS and (s.model_type, s.training_window) == ("tft", 390)
    assert s.content_hash == h                                               # same definition, same hash
    engine.dispose()
