"""Cross-sectional momentum classifier (LightGBM + Optuna TPE): features, label, folds, feature selection,
portfolio weights, the signal factor through the repositories, and one synthetic run through the /csm dashboard."""

import numpy as np
import pandas as pd
import pytest

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
    CSMFeatureConfig,
    CSMLabelConfig,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
    CSMDataset,
    build_dataset,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_model import (
    optimize,
    train,
    walk_forward_folds,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
    long_short_weights,
)

pytestmark = pytest.mark.filterwarnings("ignore")


def _closes(n_days=160, n_assets=8, seed=3):
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        synthetic_closes,
    )
    return synthetic_closes([f"A{i}" for i in range(n_assets)], "2025-01-02", n_days, seed)


def test_features_only_use_past_closes_and_the_label_needs_the_future():
    closes = _closes()
    cfg_f, cfg_l = CSMFeatureConfig(), CSMLabelConfig(horizon=1)
    d = closes.index[120]
    base = build_dataset(closes, cfg_f, cfg_l).rows_on(d)
    changed = closes.copy()
    changed.loc[changed.index > d] *= 1.5                                    # rewrite the future
    after = build_dataset(changed, cfg_f, cfg_l).rows_on(d)
    names = cfg_f.feature_names()
    pd.testing.assert_frame_equal(base[names], after[names])                 # features at d are unchanged
    assert not base["label"].equals(after["label"]) or base["fwd_return"].ne(after["fwd_return"]).any()
    last = build_dataset(closes, cfg_f, cfg_l).rows_on(closes.index[-1])
    assert last["label"].isna().all()                                        # tomorrow is not known
    warm = build_dataset(closes, cfg_f, cfg_l).rows_on(closes.index[100])
    assert warm["return_5m"].isna().all()                                    # 106-close lookback not reached yet
    assert names == [n for _, n in __import__(
        "src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition",
        fromlist=["x"]).LGBMMomentumFeatureDefinition.FEATURE_MAP]               # the 24 momentum factors


def test_features_are_the_domain_factors_own_values():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
        momentum_factor_classes,
    )
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        synthetic_closes,
    )
    closes = synthetic_closes(["A0", "A1", "A2"], "2024-10-01", 150, 3)     # crosses a year end (ytd)
    ds = build_dataset(closes, CSMFeatureConfig(), CSMLabelConfig())
    i, asset = 140, "A1"
    window = closes[asset].iloc[:i + 1]
    classes = momentum_factor_classes()
    row = ds.rows_on(closes.index[i]).loc[asset]
    for name, n in (("return_20d", 21), ("price_vs_ma_50", 50), ("sharpe_20d", 21), ("days_since_5m_high", 105)):
        expected = classes[name]().calculate({"CompanyShareFactor": window.iloc[-n:].tolist()})
        assert row[name] == pytest.approx(expected), name
    assert closes.index[i].year == 2025
    ytd = window[window.index.year == closes.index[i].year]
    prev = window[window.index.year < closes.index[i].year].iloc[-1:]
    expected = classes["return_ytd"]().calculate({"CompanyShareFactor": pd.concat([prev, ytd]).tolist()})
    assert row["return_ytd"] == pytest.approx(expected)


def test_label_is_next_return_above_the_cross_sectional_median():
    closes = _closes(n_days=120)
    ds = build_dataset(closes, CSMFeatureConfig(), CSMLabelConfig(horizon=1))
    d = closes.index[110]
    rows = ds.rows_on(d)
    fwd = closes.iloc[111] / closes.iloc[110] - 1.0
    assert ((fwd > fwd.median()).astype(float) == rows["label"].reindex(fwd.index)).all()
    assert rows["label"].sum() == len(fwd) // 2


def test_walk_forward_folds_are_consecutive_and_purged():
    dates = list(pd.bdate_range("2025-01-01", periods=40))
    folds = walk_forward_folds(dates, n_folds=3, purge=2)
    assert len(folds) == 3
    for train_d, valid_d in folds:
        assert max(train_d) < min(valid_d)
        gap = dates.index(min(valid_d)) - dates.index(max(train_d))
        assert gap == 3                                                      # 2 purged dates in between
    assert folds[0][1][-1] < folds[1][1][0]


def _planted_dataset(n_dates=150, n_assets=20, seed=0):
    """Label = sign of one informative feature (plus noise); the other features are pure noise."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-01", periods=n_dates)
    idx = pd.MultiIndex.from_product([dates, [f"A{i}" for i in range(n_assets)]], names=["date", "asset"])
    signal = rng.normal(size=len(idx))
    frame = pd.DataFrame({"signal": signal, **{f"noise{k}": rng.normal(size=len(idx)) for k in range(6)}}, index=idx)
    frame["label"] = ((signal + 0.5 * rng.normal(size=len(idx))) > 0).astype(float)
    frame["fwd_return"] = 0.01 * (frame["label"] - 0.5) + 0.002 * rng.normal(size=len(idx))
    frame["daily_vol"] = 0.02
    return CSMDataset(frame=frame, feature_names=["signal"] + [f"noise{k}" for k in range(6)]), list(dates)


def test_optuna_tpe_selects_the_informative_feature():
    ds, dates = _planted_dataset()
    cfg = CSMConfiguration()
    cfg.optimization.n_trials = 25
    cfg.optimization.n_startup_trials = 8
    cfg.optimization.min_features = 1
    study = optimize(ds, dates, cfg)
    assert "signal" in study.features
    assert study.best_value > 0.75
    assert study.selection_frequency["signal"] == 1.0                        # every top trial kept it
    assert len(study.trial_values) == 25 and set(study.params) >= {"num_leaves", "learning_rate", "n_estimators"}
    model = train(ds, dates, cfg)
    gain = model.gain_importance()
    assert max(gain, key=gain.get) == "signal"
    assert model.contributions(ds.frame.iloc[:10]).shape == (10, len(model.features))


def test_trials_with_too_few_features_are_pruned():
    ds, dates = _planted_dataset(n_dates=80, n_assets=10)
    cfg = CSMConfiguration()
    cfg.optimization.n_trials = 12
    cfg.optimization.n_startup_trials = 12
    cfg.optimization.min_features = 6                                        # most random subsets are smaller
    study = optimize(ds, dates, cfg)
    assert study.n_pruned > 0 and len(study.features) >= 6


def test_long_short_weights_are_dollar_neutral_inverse_vol_and_capped():
    scores = {f"A{i}": i / 10 for i in range(10)}
    vol = {a: 0.01 if a in ("A9", "A0") else 0.02 for a in scores}
    w = long_short_weights(scores, vol, quantile=0.2, gross=1.0)
    assert set(w) == {"A0", "A1", "A8", "A9"}
    assert w["A9"] > w["A8"] > 0 > w["A1"] > w["A0"]
    assert sum(w.values()) == pytest.approx(0.0) and sum(abs(v) for v in w.values()) == pytest.approx(1.0)
    assert w["A9"] == pytest.approx(2 * w["A8"])                             # half the vol, twice the weight
    assert long_short_weights({"A": 0.5}, {"A": 0.01}, 0.2, 1.0) == {}


def test_signal_factor_round_trip_through_the_repositories():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_signal_store import (
        CSMSignalStore,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import (
        CompanyShareCrossSectionalMomentumFactor,
    )
    from src.infrastructure.repositories.mappers.factor.factor_mapper import DISCRIMINATOR_CLASS_MAP
    from tests.spatio_temporal_momentum.helpers import make_factory
    factory, session, engine = make_factory()
    try:
        assert DISCRIMINATOR_CLASS_MAP["company_share_cross_sectional_momentum_factor"] is \
            CompanyShareCrossSectionalMomentumFactor
        store = CSMSignalStore(factory, CSMConfiguration(signal_factor_name="csm_test_signal"))
        assert store.write("2026-06-02", {7: 0.61, 8: 0.42, 9: float("nan")}) == 2
        assert store.write("2026-06-02", {7: 0.99}) == 0                     # a stored decision is never rewritten
        assert store.read("2026-06-02", 7) == pytest.approx(0.61)
        repo = factory.get_local_repository("CompanyShareCrossSectionalMomentumFactor")
        factor = repo.get_by_name("csm_test_signal")
        assert isinstance(factor, CompanyShareCrossSectionalMomentumFactor)
        entity = type("E", (), {"id": 8})()
        assert factor.calculate({"entity": entity, "target_date": pd.Timestamp("2026-06-02")}) == pytest.approx(0.42)
    finally:
        session.close()
        engine.dispose()


def test_project_config_and_former_entry_point():
    from src.application.managers.project_managers.cross_sectionnal_project import config as c
    from src.application.managers.project_managers.cross_sectionnal_project.cross_sectionnal_project_manager import (
        CrossSectionnal,
    )
    from src.application.managers.project_managers.cross_sectionnal_project.project_manager import (
        CrossSectionalMomentumProjectManager,
    )
    assert CrossSectionnal is CrossSectionalMomentumProjectManager
    cfg = c.build_csm_configuration(c.get_config())
    assert len(cfg.universe.tickers) == 48 and cfg.optimization.n_trials >= 20
    assert cfg.training.training_window_rows == c.TRAINING_WINDOW
    assert CSMConfiguration.from_dict(cfg.to_dict()).model_hash() == cfg.model_hash()
    sessions = len(pd.bdate_range(c.get_config()["price_history_start"], c.get_config()["backtest_start"]))
    assert sessions >= cfg.required_history_rows() - 10                       # history covers window + warm-up
    assert c.get_config()["factors"][0]["name"] == c.CSM_SIGNAL_FACTOR_NAME


def test_synthetic_run_report_dashboard_and_pdf(tmp_path):
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report_renderer import build_pdf
    from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
        STMProgressTracker,
    )
    from src.interfaces.flask.app import FlaskApp

    tracker = STMProgressTracker(persist_path=stm_report_store.progress_path(str(tmp_path)),
                                 last_step_prefixes=("[CSM] Optuna",))
    tracker.start("demo")
    report, results, cycle = run_synthetic_demo(tracker, backtest_sessions=25, n_trials=6,
                                                tickers=[f"T{i}" for i in range(10)], keep_cycle=True)
    # the factor path (dependencies -> CSMModelProvider -> model valid at the date) gives the cycle's probability
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_model_provider import (
        CSMModelProvider,
    )
    from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
        LGBMMomentumFeatureDefinition,
    )
    decision = [r for r in results if r.scores][-1]
    provider = CSMModelProvider(factory=cycle.factory, factor_id=None, config=cycle.config)
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import build_dataset as bd
    closes_known = cycle.reader.load_close_panel({eid: t for t, eid in cycle.ticker_to_entity.items()},
                                                 start=cycle.history_start).loc[:decision.session]
    row = bd(closes_known, cycle.config.features, cycle.config.label, cycle.feature_engine).rows_on(
        decision.session).loc["T3"]
    deps = {cls: [row[name]] for cls, name in LGBMMomentumFeatureDefinition.FEATURE_MAP}
    entity = type("E", (), {"id": cycle.ticker_to_entity["T3"]})()
    assert provider.predict(deps, entity, decision.session) == pytest.approx(decision.scores["T3"])
    cycle.factory.session.close()
    assert report is not None
    retrained = [r for r in results if r.retrained]
    assert len(retrained) >= 2
    assert all(set(r.weights) <= set(r.scores) for r in results)
    assert all(abs(sum(r.weights.values())) < 1e-9 for r in results if r.weights)
    # every model was trained on labels known at its session only
    assert report.table_retrainings["Training window"].map(lambda w: w.split(" .. ")[1]).tolist() == \
        [str((r.session - pd.offsets.BDay(1)).date()) for r in retrained]
    assert set(report.table_importance.columns) == {"Gain share %", "Mean |SHAP| (log-odds)",
                                                    "Selected by best trial %", "Top-trial selection %"}
    assert report.table_importance["Gain share %"].sum() == pytest.approx(100.0)
    assert report.coverage_summary is not None and report.coverage_assets is not None
    assert len(report.selection_matrix) == len(retrained)
    stm_report_store.save_report(report, str(tmp_path), pdf_builder=build_pdf)
    tracker.complete(report)

    app = FlaskApp().get_app()
    app.config["CSM_RESULTS_DIR"] = str(tmp_path)
    client = app.test_client()
    assert "Cross-Sectional Momentum" in client.get("/csm/").get_data(as_text=True)
    snap = client.get("/csm/api/progress").get_json()
    assert snap["status"] == "completed" and snap["has_report"] and snap["last_epoch"].startswith("[CSM] Optuna")
    html = client.get("/csm/results").get_data(as_text=True)
    for title in ("Performance", "Prediction Quality", "Feature Importance", "Optuna TPE Feature Selection",
                  "Retrainings", "Data Coverage – Summary", "Data Coverage by Asset", "Data Coverage by Session"):
        assert title in html, title
    assert html.count("data:image/png;base64,") == 5
    pdf = client.get("/csm/report.pdf")
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")
