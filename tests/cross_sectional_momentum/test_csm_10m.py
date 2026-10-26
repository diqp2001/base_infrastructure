"""10-minute cross-sectional momentum project: configuration, bar-sized services and a synthetic run (in-memory
SQLite, temp directories; no IBKR, no SQL Server)."""

import hashlib
import json

import pandas as pd
import pytest

from src.application.managers.project_managers.cross_sectionnal_project import config as daily
from src.application.managers.project_managers.cross_sectionnal_project_10m import config as c
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)


def test_the_project_trains_on_10_minute_bars_and_retrains_every_day():
    cfg = c.build_csm_configuration(c.get_config())
    assert cfg.bar_minutes == 10 and c.get_config()["bar_size_setting"] == "10 mins"
    assert c.get_config()["retrain_every_days"] == 1
    assert c.get_config()["config_interval"] == {"custom_interval_minutes": 10, "session_start": "09:40",
                                                 "session_end": "16:00"}
    assert cfg.training.training_window_rows == 390 and cfg.label.horizon == 1
    assert CSMConfiguration.from_dict(cfg.to_dict()).model_hash() == cfg.model_hash()
    # history start .. backtest start covers the training window + warm-up + label, counted in 10-minute bars
    sessions = len(pd.bdate_range(c.get_config()["price_history_start"], c.get_config()["backtest_start"])) - 1
    assert sessions * c.BARS_PER_SESSION >= cfg.required_history_rows()


def test_the_10_minute_project_keeps_its_own_names_apart_from_the_daily_one():
    d, m = daily.get_config(), c.get_config()
    for key in ("results_dir", "project_name"):
        assert d[key] != m[key]
    assert d["Portfolio"]["name"] != m["Portfolio"]["name"]
    assert d["csm"]["artifact_dir"] != m["csm"]["artifact_dir"]
    dc, mc = daily.build_csm_configuration(d), c.build_csm_configuration(m)
    assert (dc.universe.name, dc.signal_factor_name, dc.ml_model_name_prefix) != \
        (mc.universe.name, mc.signal_factor_name, mc.ml_model_name_prefix)
    assert dc.model_hash() != mc.model_hash()


def test_a_daily_configuration_hash_is_unchanged_by_the_bar_size_field():
    """Daily models trained before bar_minutes existed keep their hash (artifacts stay selectable)."""
    cfg = daily.build_csm_configuration(daily.get_config())
    d = cfg.to_dict()
    for k in ("artifact_dir", "persist_signals", "persist_features", "bar_minutes"):
        d.pop(k)
    assert cfg.bar_minutes is None
    assert cfg.model_hash() == hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


def test_the_preload_reads_every_series_at_10_minutes():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_preload import preload_series
    series = preload_series(c.build_csm_configuration(), c.get_config()["bar_size_setting"])
    assert series and {s.bar_size_setting for s in series} == {"10 mins"}
    assert {"SPY", "IRX"} <= {s.symbol for s in series}


def test_synthetic_10_minute_run_decides_every_bar_retrains_daily_and_reports(tmp_path):
    from src.application.managers.project_managers.cross_sectionnal_project_10m.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report_renderer import build_pdf
    from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
        STMProgressTracker,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
        strategy_metrics,
    )
    from src.interfaces.flask.app import FlaskApp

    tracker = STMProgressTracker(persist_path=stm_report_store.progress_path(str(tmp_path)),
                                 last_step_prefixes=("[CSM] Optuna",))
    tracker.start("demo")
    report, results, cycle = run_synthetic_demo(tracker, backtest_sessions=2, n_trials=4, training_sessions=3,
                                                tickers=[f"T{i}" for i in range(8)], keep_cycle=True)
    try:
        assert {r.frequency for r in cycle.readers.values()} == {"10m"}
        assert len(results) == 2 * c.BARS_PER_SESSION
        assert all(r.weights for r in results)                               # a decision at every 10-minute bar
        retrained = [r.session for r in results if r.retrained]
        assert len(retrained) == 2 and [t.time() for t in retrained] == [pd.Timestamp("09:30").time()] * 2
        assert len({t.date() for t in retrained}) == 2                       # once per session, at its first bar
        assert all(abs(sum(r.weights.values())) < 1e-9 for r in results)
        # bar-to-bar returns annualised with 252 x 39 bars
        model = report.returns.columns[0]
        assert report.table_performance.loc[model, "Sharpe"] == pytest.approx(
            strategy_metrics(report.returns[model], 252 * 39)["Sharpe"])
        # every decision is evaluated on the next bar, except the last one (its next bar is not known yet)
        assert len(report.quintile_returns) == report.n_sessions == len(results) - 1
        assert any("10-minute bars stored" in n for n in report.notes)
        signal = cycle.signal_store.ensure_signal_factor()
        assert (signal.name, signal.frequency) == (c.CSM_SIGNAL_FACTOR_NAME, "10m")
    finally:
        cycle.factory.session.close()

    stm_report_store.save_report(report, str(tmp_path), pdf_builder=build_pdf)
    tracker.complete(report)
    app = FlaskApp().get_app()
    app.config["CSM_RESULTS_DIR"] = str(tmp_path)
    client = app.test_client()
    assert "10-minute bars, retrained daily" in client.get("/csm/?project=csm_10m").get_data(as_text=True)
    html = client.get("/csm/results?project=csm_10m").get_data(as_text=True)
    assert "Performance per Score Quintile" in html and "Retrainings" in html
    assert client.get("/csm/report.pdf?project=csm_10m").data.startswith(b"%PDF")
