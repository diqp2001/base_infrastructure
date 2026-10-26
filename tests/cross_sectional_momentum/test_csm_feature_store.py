"""Option C: every cross-sectional decision's candidate feature values are stored, on the factors the factor-
resolution path uses; intraday signals are dated per bar (in-memory SQLite, temp dirs; no IBKR, no SQL Server)."""

import numpy as np
import pandas as pd
import pytest

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import STMProgressTracker


def _tracker():
    t = STMProgressTracker(persist_path=None)
    t.start("test")
    return t


@pytest.fixture(scope="module")
def daily_run():
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    report, results, cycle = run_synthetic_demo(_tracker(), backtest_sessions=4, n_trials=3, training_window=60,
                                                tickers=[f"T{i}" for i in range(6)], keep_cycle=True)
    yield results, cycle
    cycle.factory.session.close()


def _stored(cycle, factor_id, entity_id, when):
    v = cycle.factory.factor_value_local_repo.get_by_factor_entity_date(
        int(factor_id), int(entity_id), pd.Timestamp(when).strftime("%Y-%m-%d %H:%M:%S"), "CompanyShare")
    return None if v is None else float(v.value)


def test_the_daily_project_stores_every_decisions_features(daily_run):
    results, cycle = daily_run
    assert cycle.config.persist_features and cycle.feature_store is not None
    ids = cycle.feature_store.ensure_feature_factors()
    assert set(ids) == set(cycle.config.features.base_feature_names())        # one factor per candidate
    decision = [r for r in results if r.scores][-1]
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import build_dataset
    closes = cycle.reader.load_close_panel({e: t for t, e in cycle.ticker_to_entity.items()},
                                           start=cycle.history_start).loc[:decision.session]
    row = build_dataset(closes, cycle.config.features, cycle.config.label, cycle.feature_engine).rows_on(
        decision.session)
    checked = 0
    for ticker in decision.scores:
        for name in ("return_20d", "price_vs_ma_20", "avg_turnover_1m", "rel_return_spy_5d", "zakamouline_delta_floor"):
            expected = row.loc[ticker, name] if name in row.columns else np.nan
            got = _stored(cycle, ids[name], cycle.ticker_to_entity[ticker], decision.session)
            if np.isfinite(expected):
                assert got == pytest.approx(expected)                         # what the model scored
                checked += 1
    assert checked > 0


def test_the_stored_features_are_the_factors_the_resolution_path_would_use(daily_run):
    """Each candidate's DependencySpec matches exactly one factor: the one holding the stored values."""
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_store import (
        candidate_specs,
    )
    _, cycle = daily_run
    parent = cycle.signal_store.ensure_signal_factor()
    ids = cycle.feature_store.ensure_feature_factors()
    for name, spec in candidate_specs().items():
        repo = cycle.factory.get_local_repository(spec.dep_name)
        matching = [f.id for f in repo.get_all() if spec.matches_factor(parent, f)]
        assert matching == [ids[name]], name
        assert repo.get_by_id(ids[name]).source == "calculated"


def test_a_second_write_of_the_same_decision_adds_nothing(daily_run):
    results, cycle = daily_run
    decision = [r for r in results if r.scores][-1]
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import build_dataset
    closes = cycle.reader.load_close_panel({e: t for t, e in cycle.ticker_to_entity.items()},
                                           start=cycle.history_start).loc[:decision.session]
    row = build_dataset(closes, cycle.config.features, cycle.config.label, cycle.feature_engine).rows_on(
        decision.session)
    assert cycle.feature_store.write(decision.session, row, cycle.ticker_to_entity) == 0


def test_intraday_signals_are_stored_per_bar_not_once_a_day():
    from src.application.managers.project_managers.cross_sectionnal_project_10m.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    report, results, cycle = run_synthetic_demo(_tracker(), backtest_sessions=1, n_trials=3, training_sessions=3,
                                                tickers=[f"T{i}" for i in range(6)], keep_cycle=True)
    try:
        assert cycle.feature_store is None                                    # off for 10-minute bars (volume)
        factor = cycle.signal_store.ensure_signal_factor()
        decisions = [r for r in results if r.scores]
        assert len({r.session for r in decisions}) > 1
        for r in decisions[:3] + decisions[-2:]:
            ticker, p = next(iter(r.scores.items()))
            assert _stored(cycle, factor.id, cycle.ticker_to_entity[ticker], r.session) == pytest.approx(p)
    finally:
        cycle.factory.session.close()
