"""Intraday Spatio-Temporal Momentum (spatio_temporal_momentum_project_10m): bar keys, the 10-minute frontier,
annualisation, the bar updater, the project configuration and one synthetic 10-minute trading cycle."""

from types import SimpleNamespace

import pandas as pd
import pytest

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMFrontierPriceReader,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
    strategy_metrics,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import (
    bar_key,
    bars_per_session,
    frequency,
    next_key,
    periods_per_year,
)
from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
from tests.spatio_temporal_momentum.helpers import make_factory


def test_daily_keys_are_unchanged_and_intraday_keys_are_bars():
    ts = pd.Timestamp("2026-10-05 10:17:30")
    assert bar_key(ts, None) == pd.Timestamp("2026-10-05") and next_key(ts, None) == pd.Timestamp("2026-10-06")
    assert bar_key(ts, 10) == pd.Timestamp("2026-10-05 10:10") and next_key(ts, 10) == pd.Timestamp("2026-10-05 10:20")
    assert bar_key(pd.Timestamp("2026-10-05 10:10", tz="UTC"), 10) == pd.Timestamp("2026-10-05 10:10")
    assert (bars_per_session(None), bars_per_session(10)) == (1, 39)
    assert (periods_per_year(None), periods_per_year(10)) == (252, 252 * 39)
    assert (frequency(None), frequency(10)) == ("1d", "10m")


def test_annualisation_follows_the_periods_per_year():
    r = pd.Series([0.001, -0.0005, 0.002, 0.0, -0.001, 0.0015])
    daily, intraday = strategy_metrics(r), strategy_metrics(r, periods_per_year(10))
    assert intraday["E[Return]"] == pytest.approx(daily["E[Return]"] * 39)
    assert intraday["Vol."] == pytest.approx(daily["Vol."] * 39 ** 0.5)
    assert intraday["Sharpe"] == pytest.approx(daily["Sharpe"] * 39 ** 0.5)


def test_the_frontier_only_returns_closed_10_minute_bars():
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    factory, session, engine = make_factory()
    try:
        f = CompanyShareFactorModel(name="close", group="price", subgroup="TRADES", frequency="10m",
                                    data_type="numeric", source="ibkr", definition="close",
                                    factor_type="company_share_factor")
        session.add(f)
        session.commit()
        starts = pd.date_range("2026-10-05 09:30", periods=6, freq="10min")       # 09:30 .. 10:20
        for i, d in enumerate(starts):
            session.add(FactorValueModel(factor_id=f.id, entity_id=1, entity_type="CompanyShare",
                                         date=d.to_pydatetime(), value=repr(100.0 + i)))
        session.commit()
        history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
        reader = STMFrontierPriceReader(history, frequency="10m", bar_minutes=10)

        history.set_frontier(pd.Timestamp("2026-10-05 10:05").to_pydatetime())   # 09:50 bar closed, 10:00 not
        panel = reader.load_close_panel({1: "AAA"})
        assert list(panel.index) == list(starts[:3]) and panel["AAA"].iloc[-1] == 102.0

        history.set_frontier(pd.Timestamp("2026-10-05 10:10").to_pydatetime())   # the 10:00 bar has just closed
        assert reader.load_close_panel({1: "AAA"}).index[-1] == pd.Timestamp("2026-10-05 10:00")
        # 'end' narrows to the end of its bar, never past the frontier
        assert reader.load_close_panel({1: "AAA"}, end="2026-10-05 09:45").index[-1] == pd.Timestamp("2026-10-05 09:40")
    finally:
        session.close()
        engine.dispose()


def test_the_10m_project_is_intraday_and_separate_from_the_daily_projects():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m import config as m10
    from src.application.managers.project_managers.spatio_temporal_momentum_project_full import config as full
    cfg, daily = m10.build_stm_configuration(m10.get_config()), full.build_stm_configuration(full.get_config())
    assert cfg.bar_minutes == 10 and daily.bar_minutes is None
    assert cfg.features.annualisation == 252 * 39
    assert cfg.features.required_history_days(cfg.model.lookback) <= m10.TRAINING_WINDOW
    assert cfg.model_hash() != daily.model_hash()
    for attr in ("ml_model_name_prefix", "signal_factor_name", "feature_factor_prefix", "artifact_dir"):
        assert getattr(cfg, attr) != getattr(daily, attr), attr
    assert cfg.universe.name != daily.universe.name
    c10, cfull = m10.get_config(), full.get_config()
    for key in ("project_name", "results_dir"):
        assert c10[key] != cfull[key], key
    assert c10["Portfolio"]["name"] != cfull["Portfolio"]["name"]
    assert c10["bar_size_setting"] == "10 mins"
    assert c10["config_interval"]["custom_interval_minutes"] == 10
    feature_rows = [f for f in c10["factors"] if f["name"].startswith(m10.STM_FEATURE_FACTOR_PREFIX)]
    assert feature_rows and all(f["frequency"] == "10m" and f["subgroup"] == "minutes" for f in feature_rows)


def test_the_bar_updater_imports_the_history_once_then_after_each_new_bar(monkeypatch):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.data.price_ingestion import (
        BarHistoryUpdater,
    )
    calls = []
    service = SimpleNamespace(_get_point_in_time_data=lambda **kw: calls.append(kw) or object())
    up = BarHistoryUpdater(service, ["JPM", "BAC"], history_start="2026-09-15")
    assert BarHistoryUpdater.duration_for("2026-09-15", "2026-10-21") == "6 W"
    assert BarHistoryUpdater.duration_for("2026-10-20", "2026-10-21") == "1 W"

    status = up(pd.Timestamp("2026-10-05 09:40"))
    assert status == {"JPM": True, "BAC": True}
    assert {c["bar_size_setting"] for c in calls} == {"10 mins"} and calls[0]["duration_str"].endswith(" W")
    n = len(calls)
    imported = up._imported_through
    assert up(imported + pd.Timedelta(minutes=5)) is None and len(calls) == n           # same bar: no request
    assert up(imported + pd.Timedelta(minutes=10)) is not None                           # a new bar closed
    assert {c["duration_str"] for c in calls[n:]} == {"1 D"}


def test_session_clock_skips_the_night():
    from src.application.services.misbuffet.engine.misbuffet_engine import MisbuffetEngine
    from datetime import datetime
    engine = MisbuffetEngine.__new__(MisbuffetEngine)
    interval = engine._get_time_interval({'custom_interval': {'custom_interval_minutes': 10,
                                                              'session_start': '09:40', 'session_end': '16:00'}})
    step = lambda t: engine._add_time_interval(t, interval)
    assert step(datetime(2026, 10, 5, 15, 50)) == datetime(2026, 10, 5, 16, 0)
    assert step(datetime(2026, 10, 5, 16, 0)) == datetime(2026, 10, 6, 9, 40)
    assert step(datetime(2026, 10, 5, 9, 0)) == datetime(2026, 10, 5, 9, 40)
    plain = engine._get_time_interval({'custom_interval': {'custom_interval_minutes': 10}})
    assert engine._add_time_interval(datetime(2026, 10, 5, 16, 0), plain) == datetime(2026, 10, 5, 16, 10)


def test_synthetic_10_minute_cycle_trains_scores_and_reports_per_bar():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
        STMProgressTracker,
    )
    report, results = run_synthetic_demo(STMProgressTracker(), backtest_bars=45, n_epochs=1,
                                         tickers=["JPM", "BAC", "WFC", "C", "GS", "MS"], return_results=True)
    # a decision at bar close uses that bar: decided at 09:40 -> keyed on the 09:30 bar
    assert all(r.session.minute % 10 == 0 for r in results)
    assert len({r.session for r in results}) == len(results)
    retrained = [r.session for r in results if r.retrained]
    assert len(retrained) >= 2 and len({d.normalize() for d in retrained}) == len(retrained)   # once per day
    assert sum(1 for r in results if r.weights) > len(results) // 2
    assert report is not None and report.n_sessions > 10
    assert any("10-minute bar" in n for n in report.notes)
