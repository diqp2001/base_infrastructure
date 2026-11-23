"""Monthly cross-sectional deciles of the STM model (stm_monthly_decile_project): decile assignment, holding period,
turnover, cumulative / long-short returns, monthly retraining, the A / B ablation on identical dates and members,
no look-ahead (prices and point-in-time fundamentals) and the Misbuffet path. In memory: no IBKR, no Eulerpool."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.application.managers.project_managers.stm_monthly_decile_project import config as c
from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.synthetic_demo import (
    run_synthetic_demo,
    synthetic_world,
)
from src.application.services.portfolio_research.stm_decile_cycle import month_end_panel
from src.application.services.portfolio_research.decile_portfolios import (
    DecileConfig,
    DecileResearch,
    assign_deciles,
    cumulative,
    monotonicity,
    statistics,
    turnover,
)


# ---------------------------------------------------------------- deciles
def test_lowest_score_is_d1_highest_d10_and_sizes_differ_by_at_most_one():
    scores = {f"S{i:02d}": float(i) for i in range(23)}
    a = assign_deciles(scores, 10)
    assert a.loc[a.score.idxmin(), "decile"] == 1 and a.loc[a.score.idxmax(), "decile"] == 10
    sizes = a.groupby("decile").size()
    assert list(sizes.index) == list(range(1, 11)) and sizes.max() - sizes.min() <= 1 and sizes.sum() == 23
    assert a["decile"].is_monotonic_increasing and list(a["rank"]) == list(range(1, 24))


def test_ties_are_broken_deterministically_by_symbol():
    a = assign_deciles({"B": 1.0, "A": 1.0, "C": 1.0, "D": 2.0}, 2)
    assert list(a["symbol"]) == ["A", "B", "C", "D"] and list(a["decile"]) == [1, 1, 2, 2]
    assert assign_deciles({"C": 1.0, "A": 1.0, "B": 1.0, "D": 2.0}, 2).equals(a)


def test_only_equal_weight_is_implemented_and_sector_neutral_is_reserved():
    with pytest.raises(NotImplementedError):
        DecileConfig(weighting="market_cap_weight")
    with pytest.raises(NotImplementedError):
        DecileConfig(sector_neutral=True)
    with pytest.raises(ValueError):
        DecileConfig(weighting="nonsense")


# ---------------------------------------------------------------- returns, turnover, costs
def test_turnover_between_consecutive_portfolios():
    assert turnover({}, {"A": 0.5, "B": 0.5}) == pytest.approx(0.5)             # first formation
    assert turnover({"A": 0.5, "B": 0.5}, {"A": 0.5, "B": 0.5}) == 0.0
    assert turnover({"A": 0.5, "B": 0.5}, {"A": 0.5, "C": 0.5}) == pytest.approx(0.5)
    assert turnover({"A": 0.5, "B": 0.5}, {"C": 0.5, "D": 0.5}) == pytest.approx(1.0)


def test_equal_weight_returns_costs_cumulative_and_long_short():
    research = DecileResearch(DecileConfig(n_deciles=2, transaction_cost_bps=10.0))
    p1 = research.form("2020-01-31", {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0})
    assert p1.weights == {1: {"A": 0.5, "B": 0.5}, 2: {"C": 0.5, "D": 0.5}}
    research.settle(p1, "2020-02-28", {"A": 0.10, "B": -0.10, "C": 0.04, "D": 0.06})
    p2 = research.form("2020-02-28", {"A": 4.0, "B": 2.0, "C": 3.0, "D": 1.0})   # D1 = {B, D}, D2 = {A, C}
    research.settle(p2, "2020-03-31", {"A": 0.02, "B": 0.0, "C": 0.02, "D": 0.0})
    g = research.returns_frame("gross")
    assert list(g["D1"]) == pytest.approx([0.0, 0.0]) and list(g["D2"]) == pytest.approx([0.05, 0.02])
    assert list(g["LS"]) == pytest.approx(list(g["D2"] - g["D1"]))
    net = research.returns_frame("net")
    # formation: one-way 0.5 -> traded 1.0 x 10 bps; second month D2 replaced one of two names: 0.5 -> 1.0 x 10 bps
    assert net.loc[pd.Timestamp("2020-02-28"), "D2"] == pytest.approx(0.05 - 0.001)
    assert net.loc[pd.Timestamp("2020-03-31"), "D2"] == pytest.approx(0.02 - 2 * 0.5 * 0.001)
    cum = cumulative(g)
    assert cum["D2"].iloc[-1] == pytest.approx(1.05 * 1.02 - 1)
    s = statistics(g["D2"], 12)
    assert s["cumulative_return"] == pytest.approx(1.05 * 1.02 - 1) and s["win_rate"] == 1.0
    assert s["average_return"] == pytest.approx(0.035) and s["best_period"] == pytest.approx(0.05)


def test_a_member_without_a_return_is_left_out_and_reported():
    research = DecileResearch(DecileConfig(n_deciles=2))
    p = research.form("2020-01-31", {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0})
    research.settle(p, "2020-02-28", {"A": 0.1, "B": None, "C": 0.0, "D": 0.0})
    assert p.gross[1] == pytest.approx(0.1) and p.missing[1] == ["B"]


def test_monotonicity_of_a_perfectly_ordered_score():
    rows = {pd.Timestamp(f"2020-{m:02d}-28"): {f"D{d}": 0.001 * d + 0.0001 * m for d in range(1, 11)}
            for m in range(1, 7)}
    frame = pd.DataFrame.from_dict(rows, orient="index")
    frame["LS"] = frame["D10"] - frame["D1"]
    m = monotonicity(frame, 10)
    assert m["spearman_decile_vs_average_return"] == pytest.approx(1.0)
    assert m["average_period_rank_ic"] == pytest.approx(1.0) and m["average_spread"] == pytest.approx(0.009)


# ---------------------------------------------------------------- the cycle (synthetic engine run)
@pytest.fixture(scope="module")
def run():
    logs = []
    results, cycle = run_synthetic_demo(start=date(2020, 1, 1), end=date(2020, 4, 30), log=logs.append)
    return results, cycle, logs


def test_the_model_is_retrained_every_month(run):
    results, cycle, logs = run
    rebalances = [r.rebalance for r in results if r.rebalance is not None]
    assert [d.month for d in rebalances] == [1, 2, 3, 4]
    assert all(r == r + pd.offsets.BMonthEnd(0) for r in rebalances)          # the last trading day of the month
    for name in ("A", "B"):
        assert sum(f"{name}: 20 scored, retrained" in m for m in logs) == len(rebalances)


def test_prediction_at_t_is_scored_on_the_next_months_return(run):
    _, cycle, _ = run
    closes, _ = synthetic_world()
    preds = pd.DataFrame([vars(p) for p in cycle.predictions])
    settled = preds[preds.next_return.notna()]
    assert len(settled) > 0
    dates = sorted(preds.rebalance.unique())
    for rec in settled.itertuples():
        nxt = dates[dates.index(rec.rebalance) + 1]
        expected = closes.loc[nxt, rec.symbol] / closes.loc[rec.rebalance, rec.symbol] - 1
        assert rec.next_return == pytest.approx(expected)


def test_both_models_use_the_same_dates_and_members(run):
    _, cycle, _ = run
    preds = pd.DataFrame([vars(p) for p in cycle.predictions])
    a, b = preds[preds.variant == "A"], preds[preds.variant == "B"]
    assert sorted(a.rebalance.unique()) == sorted(b.rebalance.unique())
    for t in a.rebalance.unique():
        assert set(a[a.rebalance == t].symbol) == set(b[b.rebalance == t].symbol)
    # after the 2020-06-01 change NEW replaces S19; before it S19 is a member
    assert "S19" in set(a.symbol) and "NEW" not in set(a.symbol)


def test_the_engine_book_is_long_d10_short_d1(run):
    results, cycle, _ = run
    for r in results:
        if not r.weights:
            continue
        period = r.formed["A"]
        assert {s for s, w in r.weights.items() if w > 0} == set(period.weights[10])
        assert {s for s, w in r.weights.items() if w < 0} == set(period.weights[1])
        assert sum(w for w in r.weights.values() if w > 0) == pytest.approx(0.5)
        assert sum(w for w in r.weights.values() if w < 0) == pytest.approx(-0.5)


def test_scores_never_use_closes_after_the_rebalance():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import (
        STMConstituentScorer,
    )
    from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.synthetic_demo import (
        MEMBERS,
        tiny_monthly_stm,
    )
    closes, _ = synthetic_world()
    T = pd.Timestamp("2020-03-31")
    panel = month_end_panel(closes[MEMBERS], closes.index[-1])
    a = STMConstituentScorer(tiny_monthly_stm()).score(panel, MEMBERS, T)
    shocked = panel.copy()
    shocked.loc[shocked.index > T] *= 0.3
    b = STMConstituentScorer(tiny_monthly_stm()).score(shocked, MEMBERS, T)
    assert a.scores and a.scores == pytest.approx(b.scores)
    assert month_end_panel(closes, T).index[-1] == T                 # the panel stops at the rebalance


def test_the_report_has_every_decile_and_the_comparison(run, tmp_path):
    from src.application.services.portfolio_research.decile_report import write_report
    _, cycle, _ = run
    s = write_report(cycle, str(tmp_path), {"test": True})
    assert set(s["variants"]) == {"A", "B"} and set(s["long_short_comparison"]) == {"A", "B"}
    stats = s["variants"]["A"]["gross"]["statistics"]
    assert set(stats) == {f"D{d}" for d in range(1, 11)} | {"LS"}
    assert {"annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown", "win_rate",
            "average_turnover"} <= set(stats["D10"])
    cum = pd.read_csv(tmp_path / "cumulative_gross.csv")
    assert {f"D{d}" for d in range(1, 11)} | {"LS", "variant"} <= set(cum.columns)
    assert (tmp_path / "deciles_cumulative.png").exists() and (tmp_path / "predictions.csv").exists()


# ---------------------------------------------------------------- point-in-time fundamentals (model B)
def test_fundamentals_are_known_only_from_their_publication():
    from tests.cross_sectional_momentum.test_csm_fundamentals import KNOWN, NI, income
    from src.application.managers.project_managers.stm_monthly_decile_project.models.model_trainer import (
        fundamental_features,
    )
    provider = SimpleNamespace(statements=income({"A": {"netIncome": NI}}), errors=())
    extra = fundamental_features(provider, ["fund_net_income_growth_yoy_1q"])
    dates = pd.DatetimeIndex([pd.Timestamp(KNOWN[4]) - pd.Timedelta(days=1), pd.Timestamp(KNOWN[4]),
                              pd.Timestamp(KNOWN[5]) - pd.Timedelta(days=1)])
    panel = extra(dates, ["A", "B"])["fund_net_income_growth_yoy_1q"]
    assert np.isnan(panel.iloc[0]["A"])                                  # before publication: nothing
    assert panel.iloc[1]["A"] == pytest.approx(15 / 10 - 1)              # published: the value
    assert panel.iloc[2]["A"] == pytest.approx(15 / 10 - 1)              # carried until the next filing
    assert panel["B"].isna().all()                                       # no statements: missing, never invented


def test_missing_fundamentals_are_the_cross_sectional_mean_not_a_future_value():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
        build_feature_panel,
    )
    from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.synthetic_demo import (
        MEMBERS,
        tiny_monthly_stm,
    )
    closes, _ = synthetic_world()
    panel = month_end_panel(closes[MEMBERS[:4]], closes.index[-1])
    extra = pd.DataFrame(np.nan, index=panel.index, columns=panel.columns)
    extra.iloc[-1] = [1.0, 2.0, 3.0, np.nan]                             # known only at the last date, D missing
    fp = build_feature_panel(panel, tiny_monthly_stm().features, 1, extra_features={"fund_x": extra})
    col = fp.feature_names.index("fund_x")
    assert np.all(fp.features[:-1, :, col] == 0.0)                       # before it is known: neutral 0, not the value
    last = fp.features[-1, :, col]
    assert last[3] == 0.0 and last[0] < 0 < last[2]                      # z-scored across the members that have it


# ---------------------------------------------------------------- configuration and Misbuffet path
def test_the_project_configuration():
    cfg = c.build_stm_configuration()
    assert cfg.prediction_horizon == 1 and cfg.features.annualisation == 12 and not cfg.persist_features
    assert c.variants() == ["A", "B"] and c.get_config()["deciles"]["traded_variant"] == "A"
    assert c.build_decile_config().n_deciles == 10
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_fundamentals import (
        available_candidates,
    )
    assert set(c.FUNDAMENTAL_FEATURES) <= set(available_candidates())
    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    assert set(c.get_config()["universe"][CompanyShare]) >= {"AAPL", "WBA", "NVDA", "GOOGL"}


def test_the_algorithm_sends_the_long_short_book_to_misbuffet_set_holdings():
    from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.base_project_algorithm import (
        Algorithm,
    )
    from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio
    algo = Algorithm()
    algo.initialized = True
    algo.config = {"results_dir": "."}
    algo.cycle = MagicMock(long_short_gross=1.0)
    book = {"AAA": 0.25, "BBB": 0.25, "CCC": -0.5}
    target = TargetPortfolio.from_weights(book, asset_type="CompanyShare")
    algo.cycle.step.return_value = SimpleNamespace(weights=book, target_portfolio=target, rebalance=None)
    upm = MagicMock()
    algo._unified_portfolio_manager = upm
    algo._update_portfolio_value = lambda data: None
    algo._update_performance_tracking = lambda data: None
    algo.on_data(SimpleNamespace(time=pd.Timestamp("2021-02-01 16:00")))
    (targets,), kwargs = upm.set_holdings.call_args
    assert targets is target                                 # the cycle's TargetPortfolio -> rebalancing
    assert kwargs["max_gross_weight"] == 1.0


# ---------------------------------------------------------------- sector-neutral fundamentals (2026-11-18)
def _tiny_closes():
    rng = np.random.default_rng(3)
    idx = pd.date_range("2010-01-31", periods=60, freq="ME")
    return pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.05, (60, 6)), axis=0)), index=idx,
                        columns=[f"S{i}" for i in range(6)])


def test_sector_neutral_zscore_removes_the_sector_level():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
        cross_sectional_zscore,
    )
    day = pd.DatetimeIndex(["2024-03-28"])
    # banks lever 8-12x, software 0.2-0.6x: across all names leverage only says "bank"; within the sector it ranks
    frame = pd.DataFrame([[8.0, 12.0, 0.2, 0.6, 5.0]], index=day, columns=["JPM", "GS", "MSFT", "CRM", "CVX"])
    groups = {"JPM": "Financials", "GS": "Financials", "MSFT": "IT", "CRM": "IT", "CVX": "Energy"}
    plain = cross_sectional_zscore(frame)
    neutral = cross_sectional_zscore(frame, groups=groups)
    assert plain.loc[day[0], "JPM"] > 0 > plain.loc[day[0], "CRM"]                  # the sector level dominates
    row = neutral.loc[day[0]]
    assert row["JPM"] == pytest.approx(-row["GS"]) and row["MSFT"] == pytest.approx(-row["CRM"])
    assert row["GS"] > 0 and row["CRM"] > 0 and row["JPM"] < 0 and row["MSFT"] < 0   # ranked within the sector
    # the residuals -2, 2, -0.2, 0.2 share ONE scale: GS sits further from its sector mean than CRM
    assert row["GS"] == pytest.approx(2.0 / np.sqrt((4 + 4 + 0.04 + 0.04) / 4))
    assert row["CVX"] == pytest.approx(plain.loc[day[0], "CVX"])                      # alone in its sector
    assert cross_sectional_zscore(frame, groups=None).equals(plain)


def test_sector_neutral_zscore_handles_missing_values_and_unknown_sectors():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
        cross_sectional_zscore,
    )
    day = pd.DatetimeIndex(["2024-03-28"])
    frame = pd.DataFrame([[1.0, np.nan, 3.0, 4.0, 2.0]], index=day, columns=["A", "B", "C", "D", "X"])
    out = cross_sectional_zscore(frame, groups={"A": "s1", "B": "s1", "C": "s2", "D": "s2"}).loc[day[0]]
    assert np.isnan(out["B"])                                      # missing stays missing (0 in the panel)
    plain = cross_sectional_zscore(frame).loc[day[0]]
    assert out["A"] == pytest.approx(plain["A"]) and out["X"] == pytest.approx(plain["X"])  # s1: one value; X: none
    assert out["C"] == pytest.approx(-1.0) and out["D"] == pytest.approx(1.0)


def test_every_member_has_a_sector_and_model_b_uses_them():
    from src.application.managers.project_managers.stm_monthly_decile_project.models.model_trainer import (
        DecileModelTrainer,
    )
    from src.application.services.universe.djia_membership import SECTORS, build_membership
    assert set(build_membership().all_constituents()) <= set(SECTORS)
    config = c.get_config()
    assert config["deciles"]["fundamental_scaling"] == "sector_neutral"
    factory = SimpleNamespace(enable_provider_family=lambda family: MagicMock())
    trainer = SimpleNamespace(config=config, stm_config=c.build_stm_configuration(config))
    scorers = DecileModelTrainer.scorers(trainer, factory, log=lambda m: None)
    assert scorers["A"].extra_feature_groups is None and scorers["B"].extra_feature_groups == SECTORS
    config["deciles"]["fundamental_scaling"] = "cross_sectional"
    assert DecileModelTrainer.scorers(trainer, factory, log=lambda m: None)["B"].extra_feature_groups is None
    config["deciles"]["fundamental_scaling"] = "by_country"
    with pytest.raises(ValueError):
        DecileModelTrainer.scorers(trainer, factory, log=lambda m: None)


def test_sector_groups_reach_the_feature_panel():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
        build_feature_panel,
        cross_sectional_zscore,
    )
    closes = _tiny_closes()
    fund = pd.DataFrame(np.arange(closes.size, dtype=float).reshape(closes.shape) % 7, index=closes.index,
                        columns=closes.columns)
    groups = {a: ("g1" if i % 2 else "g2") for i, a in enumerate(closes.columns)}
    cfg = c.build_stm_configuration().features
    panel = build_feature_panel(closes, cfg, 1, extra_features={"f": fund}, extra_feature_groups=groups)
    expected = cross_sectional_zscore(fund, groups=groups).fillna(0.0).to_numpy()
    assert np.allclose(panel.features[:, :, panel.feature_names.index("f")], expected)


# ---------------------------------------------------------------- dividend-adjusted research closes (2026-11-18)
def test_research_reads_adjusted_last_and_the_engine_keeps_trades():
    from src.application.managers.project_managers.stm_monthly_decile_project.models.model_trainer import (
        DecileModelTrainer,
    )
    config = c.get_config()
    assert config["deciles"]["research_price_series"] == "ADJUSTED_LAST"
    assert DecileModelTrainer.price_series(SimpleNamespace(config=config)) == ["TRADES", "ADJUSTED_LAST"]
    config["deciles"]["research_price_series"] = "TRADES"
    assert DecileModelTrainer.price_series(SimpleNamespace(config=config)) == ["TRADES"]


def test_adjusted_last_is_never_read_as_a_traded_price():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
        STMFrontierPriceReader,
        STMPriceHistoryReader,
    )
    from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
    from src.domain.entities.factor.source_policy import EXPLICIT_ONLY_WHAT_TO_SHOW
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from tests.spatio_temporal_momentum.helpers import make_factory
    assert "ADJUSTED_LAST" in EXPLICIT_ONLY_WHAT_TO_SHOW
    factory, session, engine = make_factory()
    try:
        series = {}
        for subgroup in ("TRADES", "ADJUSTED_LAST"):
            f = CompanyShareFactorModel(name="close", group="price", subgroup=subgroup, frequency="1d",
                                        data_type="numeric", source="ibkr", definition=subgroup,
                                        factor_type="company_share_factor")
            session.add(f)
            session.commit()
            series[subgroup] = f.id
        days = pd.bdate_range("2026-06-01", periods=3)
        for d in days:
            for subgroup, value in (("TRADES", "100.0"), ("ADJUSTED_LAST", "97.5")):
                session.add(FactorValueModel(factor_id=series[subgroup], entity_id=1, entity_type="CompanyShare",
                                             date=d.to_pydatetime(), value=value))
        session.commit()
        assert STMPriceHistoryReader(factory).load_close_panel({1: "AAA"})["AAA"].tolist() == [100.0] * 3
        history = MarketDataHistoryService(SimpleNamespace(entity_service=SimpleNamespace(repository_factory=factory)))
        history.set_frontier(pd.Timestamp("2026-06-30").to_pydatetime())
        assert STMFrontierPriceReader(history).load_close_panel({1: "AAA"})["AAA"].tolist() == [100.0] * 3
        assert STMFrontierPriceReader(history, subgroup="ADJUSTED_LAST").load_close_panel(
            {1: "AAA"})["AAA"].tolist() == [97.5] * 3
    finally:
        session.close()
        engine.dispose()


def test_adjusted_last_requests_end_now():
    from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
    broker = InteractiveBrokersBroker.__new__(InteractiveBrokersBroker)
    broker.logger = MagicMock()
    broker.max_import_ibkr = False
    broker._historical_data_cache = {}
    broker.ib_connection = MagicMock(is_connected=lambda: True)
    broker.validate_end_date_within_6_months = lambda end: None
    broker.format_ib_datetime = lambda date_time=None, tz="US/Eastern", duration=None: "20261117-21:00:00"
    sent = []

    def request_history(contract, end, *args, **kwargs):
        sent.append(end)
        return MagicMock(retryable=False, status="complete", bars=[])
    broker.request_history = request_history
    contract = SimpleNamespace(symbol="KO", secType="STK")
    for what in ("ADJUSTED_LAST", "TRADES"):
        try:
            broker.get_historical_data(contract, end_date_time="2026-11-17 16:00:00", duration_str="20 Y",
                                       bar_size_setting="1 day", what_to_show=what)
        except Exception:
            pass                                              # only the request's end time matters here
    assert sent[:2] == ["", "20261117-21:00:00"]


# ---------------------------------------------------------------- the run registry (2026-11-18)
def test_the_decile_research_is_published_to_the_run_registry(run):
    from src.application.services.backtest_registry.backtest_run_service import BacktestRunService
    from src.application.services.backtest_registry.research_query_service import ResearchQueryService
    from src.application.services.backtest_registry.research_result_service import ResearchResultService
    from src.application.services.misbuffet.run_manifest import GitState
    from src.application.services.portfolio_research.decile_report import publish_research
    from tests.spatio_temporal_momentum.helpers import make_factory
    _, cycle, _ = run
    factory, session, engine = make_factory()
    try:
        runs = BacktestRunService(factory, git=lambda: GitState(commit="x", dirty=False), branch=lambda: None)
        r = runs.start(runs.register("stm_monthly_deciles", {"project_name": "stm_monthly_deciles"}))
        results = ResearchResultService(factory)
        n = publish_research(cycle, results, r.id)
        assert n > 0 and publish_research(cycle, results, r.id) == n          # republishing replaces
        query = ResearchQueryService(factory)
        names = {s["name"] for s in query.series(r.id)["series"]}
        assert {"A/gross/D1", "A/gross/D10", "A/gross/D10-D1", "B/net/D10-D1"} <= names
        assert any(name.startswith("A/turnover/") for name in names)
        metrics = query.metrics(r.id)
        assert {"A/gross", "A/net", "B/gross", "B/net"} <= set(metrics)
        assert "D10-D1.sharpe_ratio" in metrics["A/gross"] and "monotonicity.average_spread" in metrics["A/gross"]
    finally:
        session.close()
        engine.dispose()
