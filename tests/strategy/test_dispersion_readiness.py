"""
P7 — dispersion readiness: an ETF call dispersion TradingStrategy stops at a TargetPortfolio, through the same
layers as the LGBM quintile and STM strategies, with no change to execution.

    constituent ranking (+ ETF weights) -> ETFCallDispersionTradingStrategy -> selection -> option legs (premiums,
    ETF weights, deltas) -> TargetPortfolio (contracts) -> PortfolioRebalancer
"""

import ast
from datetime import date, datetime
from pathlib import Path

import pytest

from src.application.services.dispersion.dispersion_target_portfolio import (
    ORIGINAL,
    construct_dispersion_trade,
    dispersion_target_portfolio,
)
from src.application.services.dispersion.model_selection import ModelFilterConfig
from src.application.services.misbuffet.algorithm.portfolio_rebalancer import CurrentPortfolio, PortfolioRebalancer
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import (  # noqa: E501
    Leg,
)
from src.domain.entities.factor.trading_strategy.etf_call_dispersion_strategy import ETFCallDispersionTradingStrategy
from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio

ROOT = Path(__file__).resolve().parents[2]
AS_OF, OPENED, EXPIRY = datetime(2026, 1, 5, 16), date(2026, 1, 5), date(2026, 2, 20)
WEIGHTS = {"AAPL": 0.4, "MSFT": 0.3, "JPM": 0.2, "XOM": 0.1}
SCORES = {"AAPL": 0.6, "MSFT": 0.2, "JPM": -0.4, "XOM": 0.05}         # JPM: the model expects it to fall
ETF = Leg("DIA", spot=400.0, strike=400.0, multiplier=100.0, bid=6.0, ask=6.2, delta=0.52)
LEGS = [Leg("AAPL", 200.0, 200.0, 100.0, 4.8, 5.0, WEIGHTS["AAPL"], delta=0.55),
        Leg("MSFT", 400.0, 400.0, 100.0, 9.6, 10.0, WEIGHTS["MSFT"], delta=0.50),
        Leg("JPM", 150.0, 150.0, 100.0, 3.4, 3.5, WEIGHTS["JPM"], delta=0.48),
        Leg("XOM", 100.0, 100.0, 100.0, 2.2, 2.3, WEIGHTS["XOM"], delta=0.45)]


def signals():
    strategy = ETFCallDispersionTradingStrategy()
    # the shape the resolution service gives a per_entity strategy on an ETF: values per constituent + 'weights'
    return strategy.evaluate({"score": {s: [v] for s, v in SCORES.items()}, "weights": WEIGHTS}, as_of=AS_OF)


def test_the_dispersion_strategy_is_a_trading_strategy_reading_the_constituent_ranking():
    strategy = ETFCallDispersionTradingStrategy()
    assert isinstance(strategy, TradingStrategy)
    (spec,) = strategy.calculate_dependencies
    assert spec.per_entity and spec.key == "score"
    s = signals()
    assert dict(s.values) == SCORES and s.context["etf_weights"] == WEIGHTS and s.asset_type == "CompanyShare"


def test_names_expected_to_decline_are_excluded_and_the_rest_keep_their_full_basket_size():
    trade = construct_dispersion_trade(signals(), ETF, LEGS, OPENED, EXPIRY, ModelFilterConfig(minimum_model_score=0.0))
    target = dispersion_target_portfolio(trade, as_of=AS_OF)
    assert isinstance(target, TargetPortfolio)
    by_underlying = {p.symbol[:6].strip(): p for p in target}
    assert set(by_underlying) == {"DIA", "AAPL", "MSFT", "XOM"}                 # JPM's call excluded
    assert by_underlying["DIA"].target_quantity == -trade.etf_contracts          # short N ETF calls
    assert by_underlying["DIA"].asset_type == "ETFShareOption"
    for s in ("AAPL", "MSFT", "XOM"):                                            # ETF-weight replication, N fixed
        assert by_underlying[s].target_quantity == trade.original.positions[s] > 0
        assert by_underlying[s].asset_type == "CompanyShareOption"
    full = dispersion_target_portfolio(trade, as_of=AS_OF, strategy=ORIGINAL)
    assert len(full) == 5 and full.context["etf_contracts"] == target.context["etf_contracts"]


def test_premiums_and_deltas_are_accounted_for_in_the_target():
    trade = construct_dispersion_trade(signals(), ETF, LEGS, OPENED, EXPIRY)
    target = dispersion_target_portfolio(trade, as_of=AS_OF)
    assert target.context["short_premium"] == pytest.approx(trade.short_premium)
    assert target.context["long_premium"] == pytest.approx(trade.selected_basket_premium)
    assert target.context["net_initial_premium"] == pytest.approx(trade.net_initial_premium)
    by_underlying = {p.symbol[:6].strip(): p for p in target}
    leg = {c.symbol: c for c in LEGS}
    long_premium = sum(p.target_quantity * leg[u].multiplier * leg[u].ask for u, p in by_underlying.items() if u != "DIA")
    assert long_premium == pytest.approx(trade.selected_basket_premium)
    expected_delta = (-trade.etf_contracts * 100 * 0.52 * 400
                      + sum(p.target_quantity * 100 * leg[u].delta * leg[u].spot
                            for u, p in by_underlying.items() if u != "DIA"))
    assert target.context["net_dollar_delta"] == pytest.approx(expected_delta)


def test_the_rebalancer_turns_any_strategys_target_into_trades():
    from src.domain.entities.factor.trading_strategy.lgbm_quintile_long_short_strategy import (
        LGBMQuintileLongShortStrategy,
    )
    from src.domain.entities.factor.trading_strategy.spatio_temporal_momentum_strategy import (
        SpatioTemporalMomentumTradingStrategy,
    )
    from src.domain.entities.finance.portfolio.construction.steps import ConstructionInputs
    lgbm = LGBMQuintileLongShortStrategy()
    q = lgbm.evaluate({"score": {"AAPL": [5.0], "JPM": [1.0], "KO": [3.0]}})
    stm = SpatioTemporalMomentumTradingStrategy()
    s = stm.signals({"AAPL": 0.5, "JPM": -0.3}, {"AAPL": 0.01, "JPM": 0.02})
    targets = [
        lgbm.construction_method().build(ConstructionInputs(scores=dict(q.values))),
        stm.construction_method().build(ConstructionInputs(scores=dict(s.values), volatility=s.context["volatility"])),
        dispersion_target_portfolio(construct_dispersion_trade(signals(), ETF, LEGS, OPENED, EXPIRY)),
    ]
    rebalancer = PortfolioRebalancer()
    for target in targets:
        prices = {p.symbol: 100.0 for p in target}
        plan = rebalancer.plan_target(target, CurrentPortfolio.from_mappings(1_000_000.0, prices, {}))
        assert plan.instructions and not plan.unpriced
    dispersion_orders = {i.ticker: i.order_qty for i in rebalancer.plan_target(
        targets[2], CurrentPortfolio.from_mappings(1e6, {p.symbol: 1.0 for p in targets[2]}, {})).instructions}
    assert dispersion_orders == {p.symbol: int(p.target_quantity) for p in targets[2]}       # contracts, as targeted


def test_the_dispersion_strategy_and_its_construction_never_reach_execution():
    forbidden = ("order", "transaction", "trade_manager", "broker", "ibkr", "ibapi", "ib_insync", "position",
                 "sqlalchemy", "infrastructure", "misbuffet")
    for rel in ("src/domain/entities/factor/trading_strategy/etf_call_dispersion_strategy.py",
                "src/application/services/dispersion/dispersion_target_portfolio.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not [m for m in imported if any(k in m.lower() for k in forbidden)], (rel, imported)
