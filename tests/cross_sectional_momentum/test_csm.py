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


def _bars(n_days=150, start="2024-10-01", tickers=("A0", "A1", "A2"), seed=3):
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        synthetic_bars,
        synthetic_closes,
    )
    return synthetic_bars(synthetic_closes(list(tickers), start, n_days, seed), seed)


def test_features_only_use_past_bars_and_the_label_needs_the_future():
    bars = _bars(n_days=170, tickers=[f"A{i}" for i in range(6)])
    cfg_f, cfg_l = CSMFeatureConfig(), CSMLabelConfig(horizon=1)
    d = bars["close"].index[150]
    base = build_dataset(bars, cfg_f, cfg_l).rows_on(d)
    changed = {f: p.copy() for f, p in bars.items()}
    for f in changed:
        changed[f].loc[changed[f].index > d] *= 1.5                          # rewrite the future of every series
    after = build_dataset(changed, cfg_f, cfg_l).rows_on(d)
    names = cfg_f.feature_names()
    pd.testing.assert_frame_equal(base[names], after[names])                 # features at d are unchanged
    no_benchmark = [n for n in names if not n.startswith("rel_") and "zakamouline" not in n
                    and "whalley" not in n]                                   # no SPY / IV / IRX given here
    assert base[no_benchmark].notna().all().all()
    last = build_dataset(bars, cfg_f, cfg_l).rows_on(bars["close"].index[-1])
    assert last["label"].isna().all()                                        # tomorrow is not known
    warm = build_dataset(bars, cfg_f, cfg_l).rows_on(bars["close"].index[100])
    assert warm["return_5m"].isna().all() and warm["max_daily_return_6m"].isna().all()


def test_candidates_are_momentum_plus_liquidity_factors_and_match_the_signal_factor():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
        CSMFeatureDefinition,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import max_lookback
    from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
        LGBMMomentumFeatureDefinition,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_cross_sectional_momentum_factor import (
        CompanyShareCrossSectionalMomentumFactor,
    )
    names = CSMFeatureConfig().feature_names()
    assert len(names) == 48 and names[:24] == LGBMMomentumFeatureDefinition.FEATURE_NAMES
    assert {"avg_turnover_1m", "avg_turnover_2m", "avg_turnover_3m", "avg_turnover_4m", "avg_turnover_5m",
            "avg_turnover_6m", "share_turnover", "vpt_16w_20d_lag", "monthly_price_range", "max_daily_return_6m",
            "min_return_120d", "rel_return_spy_1d", "rel_return_spy_5d", "rel_return_spy_20d", "rel_return_spy_3m",
            "rel_return_spy_6m", "zakamouline_delta_ceiling", "zakamouline_delta_floor",
            "whalley_wilmott_delta_ceiling", "whalley_wilmott_delta_floor", "zakamouline_ceiling_distance",
            "zakamouline_floor_distance", "whalley_wilmott_ceiling_distance",
            "whalley_wilmott_floor_distance"} == set(names[24:])
    deps = [spec.factor_type.__name__ for spec in CompanyShareCrossSectionalMomentumFactor().calculate_dependencies]
    assert sorted(deps) == sorted(cls for cls, _ in CSMFeatureDefinition.FEATURE_MAP)   # same candidates
    assert len(LGBMMomentumFeatureDefinition.FEATURE_MAP) == 24              # quintile-rank factor unchanged
    assert CSMFeatureConfig().warmup_rows() == max_lookback() + 1
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import benchmark_symbols
    assert benchmark_symbols() == ["IRX", "SPY"]


def test_new_liquidity_and_return_extreme_factors():
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_liquidity_factors import (
        CompanyShareAvgTurnover2mFactor, CompanyShareMaxDailyReturn6mFactor, CompanyShareMinReturn120dFactor,
        CompanyShareTurnoverFactor, CompanyShareVpt16w20dLagFactor,
    )
    volumes = [float(v) for v in range(1, 43)]
    assert CompanyShareAvgTurnover2mFactor().calculate({"volumes": volumes}) == pytest.approx(21.5)
    assert CompanyShareAvgTurnover2mFactor().calculate({"volumes": volumes[:-1]}) is None      # 41 < 42 sessions
    assert CompanyShareTurnoverFactor().calculate({"volumes": [5.0, 7.0]}) == 7.0
    closes = [100.0] * 101
    closes[-21] = 110.0                                                       # close 20 sessions ago
    vols = [2000.0] + [1.0] * 20                                              # volume 20 sessions ago first
    assert CompanyShareVpt16w20dLagFactor().calculate({"closes": closes, "volumes": vols}) == pytest.approx(200.0)
    path = [100.0] * 50 + [120.0] * 40 + [60.0] * 37                          # one +20% day, one -50% day
    assert CompanyShareMaxDailyReturn6mFactor().calculate({"closes": path}) == pytest.approx(0.2)
    assert CompanyShareMinReturn120dFactor().calculate({"closes": path[-121:]}) == pytest.approx(-0.5)
    assert CompanyShareMaxDailyReturn6mFactor().calculate({"closes": path[:-1]}) is None


def test_relative_return_versus_spy():
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_relative_performance_factors import (
        CompanyShareRelativeReturnVsSpy5DFactor,
    )
    f = CompanyShareRelativeReturnVsSpy5DFactor()
    share = [100.0, 101, 102, 103, 104, 110.0]                                # +10% over 5 sessions
    spy = [400.0, 401, 399, 402, 405, 408.0]                                  # +2%
    assert f.calculate({"closes": share, "benchmark_closes": spy}) == pytest.approx(0.08)
    assert f.calculate({"closes": share, "benchmark_closes": spy[:-1]}) is None
    specs = f.calculate_dependencies
    assert [s.entity_symbol for s in specs] == [None, "SPY"] and [s.lookback for s in specs] == [6, 6]


def test_the_resolution_service_reads_a_benchmark_dependency_on_the_benchmark_entity():
    from unittest.mock import MagicMock
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_relative_performance_factors import (
        CompanyShareRelativeReturnVsSpy1DFactor,
    )
    share, spy = type("CompanyShare", (), {"id": 7})(), type("CompanyShare", (), {"id": 99})()
    factory = MagicMock()
    factory.get_local_repository.return_value.get_by_symbol.side_effect = lambda s: spy if s == "SPY" else None
    service = FactorValueResolutionService(factory=factory)
    service._get_resolution_entities = lambda *a, **k: [share]
    seen = {}

    def fake_spec(spec, parent, targets, *a, **k):
        seen[spec.result_key] = [t.id for t in targets]
        return [1.0, 2.0]
    service._resolve_dependency_spec = fake_spec
    out = service._resolve_dynamic_dependencies(CompanyShareRelativeReturnVsSpy1DFactor(), share,
                                                pd.Timestamp("2026-06-02").to_pydatetime(), "local")
    assert seen == {"closes": [7], "benchmark_closes": [99]}
    assert set(out) == {"closes", "benchmark_closes"}
    factory.get_local_repository.assert_any_call("CompanyShare")


def test_features_are_the_domain_factors_own_values():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
        candidate_factor_classes,
    )
    bars = _bars()
    closes = bars["close"]
    ds = build_dataset(bars, CSMFeatureConfig(), CSMLabelConfig())
    i, asset = 140, "A1"
    upto = {f: p[asset].iloc[:i + 1] for f, p in bars.items()}
    window = upto["close"]
    classes = candidate_factor_classes()
    row = ds.rows_on(closes.index[i]).loc[asset]
    for name, n in (("return_20d", 21), ("price_vs_ma_50", 50), ("sharpe_20d", 21), ("days_since_5m_high", 105)):
        expected = classes[name]().calculate({"CompanyShareFactor": window.iloc[-n:].tolist()})
        assert row[name] == pytest.approx(expected), name
    expected = {
        "avg_turnover_3m": classes["avg_turnover_3m"]().calculate({"volumes": upto["volume"].iloc[-63:].tolist()}),
        "avg_turnover_6m": classes["avg_turnover_6m"]().calculate({"volumes": upto["volume"].iloc[-126:].tolist()}),
        "share_turnover": float(upto["volume"].iloc[-1]),
        "vpt_16w_20d_lag": classes["vpt_16w_20d_lag"]().calculate(
            {"closes": window.iloc[-101:].tolist(), "volumes": upto["volume"].iloc[-21:].tolist()}),
        "monthly_price_range": float(upto["high"].iloc[-1] - upto["low"].iloc[-21]),
        "min_return_120d": float(window.pct_change().iloc[-120:].min()),
    }
    for name, value in expected.items():
        assert row[name] == pytest.approx(value), name
    spy = bars["close"]["A0"] * 0.5 + 10.0                                   # any benchmark close series
    with_spy = build_dataset(bars, CSMFeatureConfig(), CSMLabelConfig(), benchmarks={"SPY": spy})
    rel = with_spy.rows_on(closes.index[i]).loc[asset, "rel_return_spy_20d"]
    assert rel == pytest.approx(classes["rel_return_spy_20d"]().calculate(
        {"closes": window.iloc[-21:].tolist(), "benchmark_closes": spy.iloc[:i + 1].iloc[-21:].tolist()}))
    assert row["rel_return_spy_20d"] != row["rel_return_spy_20d"]           # NaN without the benchmark
    assert closes.index[i].year == 2025
    ytd = window[window.index.year == closes.index[i].year]
    prev = window[window.index.year < closes.index[i].year].iloc[-1:]
    expected_ytd = classes["return_ytd"]().calculate({"CompanyShareFactor": pd.concat([prev, ytd]).tolist()})
    assert row["return_ytd"] == pytest.approx(expected_ytd)


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
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
        CSMFeatureDefinition,
    )
    decision = [r for r in results if r.scores][-1]
    provider = CSMModelProvider(factory=cycle.factory, factor_id=None, config=cycle.config)
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import build_dataset as bd
    closes_known = cycle.reader.load_close_panel({eid: t for t, eid in cycle.ticker_to_entity.items()},
                                                 start=cycle.history_start).loc[:decision.session]
    row = bd(closes_known, cycle.config.features, cycle.config.label, cycle.feature_engine).rows_on(
        decision.session).loc["T3"]
    deps = {cls: [row[name]] for cls, name in CSMFeatureDefinition.FEATURE_MAP}
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


# ── Delta-hedging bands of the reference call ──────────────────────────────────────────────────────────────────────

def _band_inputs(spot=105.0, iv=0.25, irx=45.05):
    closes = [100.0] * 84
    closes[-1] = spot
    return {"closes": closes, "implied_vols": [iv], "rates": [irx],
            "parameters": {"cost_rate": 0.0001, "risk_aversion": 1.0, "time_to_expiry_days": 30}}


def test_delta_band_factors_follow_whalley_wilmott_and_zakamouline():
    import math
    from statistics import NormalDist
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share import (
        company_share_delta_band_factors as b,
    )
    deps = _band_inputs()
    S, K, sigma, r, tau = 105.0, (83 * 100.0 + 105.0) / 84, 0.25, math.log1p(0.04505), 30 / 365
    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * tau) / (sigma * math.sqrt(tau))
    delta, gamma = NormalDist().cdf(d1), NormalDist().pdf(d1) / (S * sigma * math.sqrt(tau))
    h_ww = (1.5 * (0.0001 * S / 1.0) * math.exp(r * tau) * gamma) ** (1 / 3)
    h_z = math.sqrt(0.0001 * S * math.exp(r * tau) * gamma / (1.0 * sigma ** 2))
    assert b.CompanyShareWhalleyWilmottDeltaCeilingFactor().calculate(deps) == pytest.approx(delta + h_ww)
    assert b.CompanyShareWhalleyWilmottDeltaFloorFactor().calculate(deps) == pytest.approx(delta - h_ww)
    assert b.CompanyShareZakamoulineDeltaCeilingFactor().calculate(deps) == pytest.approx(delta + h_z)
    assert b.CompanyShareZakamoulineDeltaFloorFactor().calculate(deps) == pytest.approx(delta - h_z)
    # the price at which the delta reaches the ceiling / floor really gives that delta
    band = b.delta_band(deps, "zakamouline")
    up, down = S * (1 + band.ceiling_distance), S * (1 - band.floor_distance)
    assert b.black_scholes_call_delta_gamma(up, K, sigma, r, tau)[0] == pytest.approx(band.ceiling)
    assert b.black_scholes_call_delta_gamma(down, K, sigma, r, tau)[0] == pytest.approx(band.floor)
    assert b.CompanyShareZakamoulineCeilingDistanceFactor().calculate(deps) == pytest.approx(up / S - 1)
    assert b.CompanyShareZakamoulineFloorDistanceFactor().calculate(deps) == pytest.approx(1 - down / S)
    assert 0 < band.floor_distance and 0 < band.ceiling_distance
    # higher implied vol -> narrower Zakamouline band (sigma in the denominator)
    wide = b.delta_band(_band_inputs(iv=0.15), "zakamouline").half_width
    assert wide > b.delta_band(_band_inputs(iv=0.45), "zakamouline").half_width


def test_delta_band_factors_never_substitute_missing_inputs():
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_delta_band_factors import (
        CompanyShareWhalleyWilmottDeltaCeilingFactor as F,
    )
    from src.application.services.data.entities.factor.factor_library.factor_definition_config import (
        library_parameters,
    )
    assert F().calculate({**_band_inputs(), "parameters": {}}) is None           # no library parameters
    assert F().calculate({**_band_inputs(), "rates": []}) is None                 # no IRX
    assert F().calculate({**_band_inputs(), "implied_vols": []}) is None          # no implied vol
    assert F().calculate({**_band_inputs(), "closes": [100.0] * 83}) is None      # < 4 months of closes
    assert library_parameters(F()) == {"cost_rate": 0.0001, "risk_aversion": 1.0, "time_to_expiry_days": 30}
    specs = {s.result_key: s for s in F().calculate_dependencies}
    assert specs["implied_vols"].subgroup == "OPTION_IMPLIED_VOLATILITY"
    assert (specs["rates"].entity_symbol, specs["rates"].entity_type) == ("IRX", "Index")
    assert specs["closes"].lookback == 84


def test_engine_band_features_equal_the_factors_on_iv_and_irx_windows():
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        synthetic_implied_vols,
        synthetic_irx,
    )
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_features import (
        candidate_factor_classes,
    )
    bars = _bars()
    closes = bars["close"]
    bars["close|OPTION_IMPLIED_VOLATILITY"] = synthetic_implied_vols(closes)
    irx = synthetic_irx(closes.index)["IRX"]
    ds = build_dataset(bars, CSMFeatureConfig(), CSMLabelConfig(), benchmarks={"close@IRX": irx})
    i, asset = 140, "A2"
    row = ds.rows_on(closes.index[i]).loc[asset]
    deps = {"closes": closes[asset].iloc[i + 1 - 84:i + 1].tolist(),
            "implied_vols": [float(bars["close|OPTION_IMPLIED_VOLATILITY"][asset].iloc[i])],
            "rates": [float(irx.iloc[i])],
            "parameters": {"cost_rate": 0.0001, "risk_aversion": 1.0, "time_to_expiry_days": 30}}
    classes = candidate_factor_classes()
    for name in ("zakamouline_delta_ceiling", "whalley_wilmott_delta_floor", "zakamouline_floor_distance",
                 "whalley_wilmott_ceiling_distance"):
        assert row[name] == pytest.approx(classes[name]().calculate(deps)), name


def test_implied_volatility_is_never_read_as_a_price():
    from types import SimpleNamespace
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
        STMFrontierPriceReader,
        STMPriceHistoryReader,
    )
    from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from tests.spatio_temporal_momentum.helpers import make_factory
    factory, session, engine = make_factory()
    try:
        series = {}
        for subgroup, value in (("TRADES", 100.0), ("OPTION_IMPLIED_VOLATILITY", 0.25)):
            f = CompanyShareFactorModel(name="close", group="price", subgroup=subgroup, frequency="1d",
                                        data_type="numeric", source="ibkr", definition=subgroup,
                                        factor_type="company_share_factor")
            session.add(f)
            session.commit()
            series[subgroup] = f.id
        days = pd.bdate_range("2026-06-01", periods=5)
        for d in days:
            session.add(FactorValueModel(factor_id=series["OPTION_IMPLIED_VOLATILITY"], entity_id=1,
                                         entity_type="CompanyShare", date=d.to_pydatetime(), value="0.25"))
        for d in days[:3]:                                                    # TRADES stops two days early
            session.add(FactorValueModel(factor_id=series["TRADES"], entity_id=1, entity_type="CompanyShare",
                                         date=d.to_pydatetime(), value="100.0"))
        session.commit()
        direct = STMPriceHistoryReader(factory).load_close_panel({1: "AAA"})
        assert direct["AAA"].dropna().tolist() == [100.0, 100.0, 100.0]
        iv = STMPriceHistoryReader(factory, subgroup="OPTION_IMPLIED_VOLATILITY").load_close_panel({1: "AAA"})
        assert iv["AAA"].tolist() == [0.25] * 5
        history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
        history.set_frontier(pd.Timestamp("2026-06-30").to_pydatetime())
        assert STMFrontierPriceReader(history).load_close_panel({1: "AAA"})["AAA"].dropna().tolist() == [100.0] * 3
        assert STMFrontierPriceReader(history, subgroup="OPTION_IMPLIED_VOLATILITY").load_close_panel(
            {1: "AAA"})["AAA"].tolist() == [0.25] * 5
    finally:
        session.close()
        engine.dispose()


def test_the_resolver_keeps_non_price_series_out_of_price_dependencies():
    from unittest.mock import MagicMock
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    from src.domain.entities.factor.dependency_spec import DependencySpec
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import (
        CompanyShareFactor,
    )

    def raw(subgroup):
        return CompanyShareFactor(name="close", group="price", subgroup=subgroup, frequency="1d",
                                  data_type="numeric", source="ibkr")
    trades, iv = raw("TRADES"), raw("OPTION_IMPLIED_VOLATILITY")
    service = FactorValueResolutionService(factory=MagicMock())
    read = []
    service._spec_values = lambda spec, factors, *a, **k: read.append([f.subgroup for f in factors]) or []
    service._missing_series = lambda *a, **k: []
    repo = MagicMock()
    repo.get_all.return_value = [trades, iv]
    service.factory.get_local_repository.return_value = repo
    price = DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=["close"], lookback=5)
    service._resolve_dependency_spec(price, CompanyShareFactor(name="x", group="price"), [], None, "local")
    assert read == [["TRADES"]]                                               # no fallback into the IV series
    read.clear()
    named = DependencySpec(factor_type=CompanyShareFactor, group="price", name_in=["close"], lookback=1,
                           subgroup="OPTION_IMPLIED_VOLATILITY")
    service._resolve_dependency_spec(named, CompanyShareFactor(name="x", group="price"), [], None, "local")
    assert read == [["OPTION_IMPLIED_VOLATILITY"]]


def test_the_import_requests_implied_volatility_without_volume():
    from datetime import datetime
    from types import SimpleNamespace
    from src.application.services.misbuffet.data.market_data_service import MarketDataService
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    calls = []
    client = SimpleNamespace(ib_connection=SimpleNamespace(connected_flag=True))
    entity_service = SimpleNamespace(repository_factory=SimpleNamespace(ibkr_client=client),
                                     create_or_get_batch_ibkr=lambda data, cls, **kw: calls.append((data, kw)) or [])
    service = MarketDataService(entity_service)
    share = CompanyShare.__new__(CompanyShare)
    share._id = 7
    service._get_entity_by_ticker = lambda ticker, cls: share
    service._get_point_in_time_data("JPM", CompanyShare, datetime(2026, 10, 22), "1 day", "1 Y",
                                    what_to_show="OPTION_IMPLIED_VOLATILITY")
    factors, kwargs = calls[0]
    assert kwargs["what_to_show"] == "OPTION_IMPLIED_VOLATILITY"
    assert {f["entity_symbol"] for f in factors} == {"open", "high", "low", "close"}
    assert {f["subgroup"] for f in factors} == {"OPTION_IMPLIED_VOLATILITY"}


# ── Backtest data preload ───────────────────────────────────────────────────────────────────────────────────────────

def test_the_preload_covers_every_series_the_run_reads():
    from collections import Counter
    from src.application.managers.project_managers.cross_sectionnal_project import config as c
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_preload import (
        extra_series,
        preload_series,
    )
    cfg = c.build_csm_configuration(c.get_config())
    series = preload_series(cfg, "1 day")
    kinds = Counter((s.entity_class.__name__, s.what_to_show) for s in series)
    assert kinds == {("CompanyShare", "TRADES"): 49, ("CompanyShare", "OPTION_IMPLIED_VOLATILITY"): 48,
                     ("Index", "TRADES"): 1}
    assert [s.symbol for s in series[:48]] == list(cfg.universe.tickers)       # the universe first
    assert {s.symbol for s in series if s.entity_class.__name__ == "Index"} == {"IRX"}
    assert "SPY" not in cfg.universe.tickers and any(s.symbol == "SPY" for s in series)
    assert {s.bar_size_setting for s in series} == {"1 day"}
    assert len(extra_series(cfg)) == len(series) - 48                         # the updater imports the same list


def test_the_trainer_preloads_before_the_first_bar(tmp_path, monkeypatch):
    from src.application.managers.project_managers.cross_sectionnal_project import config as c
    from src.application.managers.project_managers.cross_sectionnal_project.data.price_ingestion import (
        DailyHistoryUpdater,
    )
    from src.application.managers.project_managers.cross_sectionnal_project.models import model_trainer as mt
    calls = {}

    class FakeService:
        def __init__(self, market_data_service, log=None):
            calls["mds"] = market_data_service

        def preload(self, series, start, end):
            calls.update(series=series, start=start, end=end)
            return []

        @staticmethod
        def to_frame(results):
            return pd.DataFrame({"symbol": ["JPM"], "coverage_pct": [100.0]})

    monkeypatch.setattr(mt, "BacktestDataPreloadService", FakeService)
    trainer = mt.CSMModelTrainer.__new__(mt.CSMModelTrainer)
    import logging
    trainer.logger = logging.getLogger("test")
    trainer.config = {**c.get_config(), "results_dir": str(tmp_path)}
    trainer.csm_config = c.build_csm_configuration(c.get_config())
    updater = DailyHistoryUpdater(object(), ["JPM"], c.get_config()["price_history_start"])
    trainer.preload("mds", updater)
    assert calls["mds"] == "mds" and len(calls["series"]) == 98
    assert (calls["start"], calls["end"]) == (c.get_config()["price_history_start"], c.get_config()["backtest_end"])
    assert (tmp_path / mt.PRELOAD_FILE).exists()
    assert updater._imported_through == pd.Timestamp.now().normalize()        # no second full import at bar 1
    assert updater(pd.Timestamp.now()) is None
