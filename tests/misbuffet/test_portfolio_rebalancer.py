"""
P4 — PortfolioRebalancer: target portfolio + current portfolio = required trades, separate from execution.

Pure tests (no DB, no broker) for the order arithmetic, liquidation, multipliers, the no-trade band and the order of
the trades; a golden test against the order computation set_holdings used before the split; and set_holdings fed
a TargetPortfolio through the real repositories (in-memory SQLite, orders to a Mock — no IBKR).
"""

import ast
import logging
import random
from pathlib import Path

import pytest

from src.application.services.misbuffet.algorithm.portfolio_rebalancer import (
    BUY,
    LIQUIDATE,
    REBALANCE,
    SELL,
    CurrentPortfolio,
    PortfolioRebalancer,
)
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio, TargetPortfolioPosition

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)
ROOT = Path(__file__).resolve().parents[2]
rebalancer = PortfolioRebalancer()


def current(quantities, prices=None, pv=100_000.0, multipliers=None):
    prices = prices or {t: 100.0 for t in quantities}
    return CurrentPortfolio.from_mappings(pv, prices, quantities, multipliers)


# -- the four cases of the plan ------------------------------------------------------------------------------------

def test_current_50_target_100_buys_50():
    plan = rebalancer.plan(current({"AAPL": 50}), target_quantities={"AAPL": 100})
    (buy,) = plan.buys
    assert (buy.ticker, buy.order_qty, buy.side, buy.reason) == ("AAPL", 50, BUY, REBALANCE) and not plan.sells


def test_current_100_target_40_sells_60():
    plan = rebalancer.plan(current({"AAPL": 100}), target_quantities={"AAPL": 40})
    (sell,) = plan.sells
    assert (sell.order_qty, sell.side, sell.current_qty, sell.target_qty) == (-60, SELL, 100, 40) and not plan.buys


def test_current_100_target_100_gives_no_order():
    plan = rebalancer.plan(current({"AAPL": 100}), target_quantities={"AAPL": 100})
    assert plan.instructions == () and plan.unchanged == ("AAPL",)


def test_a_held_position_absent_from_the_target_is_liquidated():
    plan = rebalancer.plan(current({"AAPL": 100, "MSFT": 30}), target_quantities={"AAPL": 100}, liquidate={"MSFT"})
    (sell,) = plan.sells
    assert (sell.ticker, sell.order_qty, sell.target_qty, sell.reason) == ("MSFT", -30, 0, LIQUIDATE)
    # a short absent from the target is bought back
    plan = rebalancer.plan(current({"XOM": -20}), liquidate={"XOM"})
    assert [(b.ticker, b.order_qty, b.reason) for b in plan.buys] == [("XOM", 20, LIQUIDATE)]


# -- sizing --------------------------------------------------------------------------------------------------------

def test_weights_are_sized_on_portfolio_value_price_and_multiplier_then_truncated():
    cur = current({"AAPL": 0, "SPY_C500": 0, "MSFT": 10}, prices={"AAPL": 150.0, "SPY_C500": 2.5, "MSFT": 400.0},
                  multipliers={"SPY_C500": 100})
    plan = rebalancer.plan(cur, target_weights={"AAPL": 0.1, "SPY_C500": 0.01, "MSFT": -0.05})
    orders = {i.ticker: i.order_qty for i in plan.instructions}
    assert orders == {"AAPL": 66,          # int(100 000 x 0.1 / 150)
                      "SPY_C500": 4,       # int(100 000 x 0.01 / (2.5 x 100))
                      "MSFT": -22}         # int(-5 000 / 400) = -12, minus the 10 held


def test_no_trade_band_skips_weights_only():
    cur = current({"AAPL": 66, "MSFT": 5}, prices={"AAPL": 150.0, "MSFT": 400.0})
    plan = rebalancer.plan(cur, target_weights={"AAPL": 0.102}, target_quantities={"MSFT": 6}, liquidate=(),
                           min_weight_change=0.005)
    assert plan.within_band == ("AAPL",) and [i.ticker for i in plan.instructions] == ["MSFT"]
    plan = rebalancer.plan(cur, target_weights={"AAPL": 0.102}, liquidate={"MSFT"}, min_weight_change=0.5)
    assert [i.ticker for i in plan.instructions] == ["MSFT"]            # a liquidation is never in the band


def test_unpriced_assets_are_not_traded_and_sells_come_first_in_symbol_order():
    cur = current({"A": 10, "B": 0, "C": 10, "D": 0}, prices={"A": 10.0, "B": 10.0, "C": 10.0, "D": None})
    plan = rebalancer.plan(cur, target_quantities={"D": 5, "B": 3, "C": 1, "A": 0})
    assert plan.unpriced == ("D",)
    assert [i.ticker for i in plan.instructions] == ["A", "C", "B"]      # sells A, C then buy B
    with pytest.raises(ValueError):
        rebalancer.plan(current({"A": 1}, pv=0.0), target_weights={"A": 0.1})


def test_the_rebalancer_works_with_any_target_portfolio():
    target = TargetPortfolio(as_of=None, positions=(
        TargetPortfolioPosition("AAPL", 0.1),
        TargetPortfolioPosition("SPY_C500", 0.0, target_quantity=3),      # sized in units
        TargetPortfolioPosition("MSFT", 0.0)))                             # flat target: sell what is held
    cur = current({"AAPL": 0, "SPY_C500": 1, "MSFT": 7, "XOM": 4},
                  prices={"AAPL": 150.0, "SPY_C500": 2.5, "MSFT": 400.0, "XOM": 100.0})
    plan = rebalancer.plan_target(target, cur, liquidate={"XOM"})
    assert {i.ticker: (i.order_qty, i.reason) for i in plan.instructions} == {
        "AAPL": (66, REBALANCE), "SPY_C500": (2, REBALANCE), "MSFT": (-7, REBALANCE), "XOM": (-4, LIQUIDATE)}


def _old_set_holdings_orders(pv, weights, quantities, to_liquidate, prices, held, mult, band):
    """The order computation of set_holdings before the split (copied from the pre-P4 loop)."""
    out = {}
    for ticker in set(weights) | set(quantities) | to_liquidate:
        price = prices.get(ticker)
        if not price:
            continue
        current_qty = held.get(ticker, 0)
        if ticker in quantities:
            target_qty = quantities[ticker]
        else:
            target_pct = weights.get(ticker, 0.0)
            m = mult.get(ticker, 1)
            target_qty = int(pv * target_pct / (price * m))
            current_pct = current_qty * price * m / pv
            if band and ticker not in to_liquidate and abs(target_pct - current_pct) < band:
                continue
        if target_qty - current_qty:
            out[ticker] = target_qty - current_qty
    return out


def test_same_orders_as_set_holdings_before_the_split():
    rng = random.Random(7)
    for _ in range(300):
        tickers = [f"T{i}" for i in range(rng.randint(1, 12))]
        prices = {t: (rng.choice([None, 0.0]) if rng.random() < 0.1 else round(rng.uniform(1, 500), 2))
                  for t in tickers}
        held = {t: rng.randint(-50, 200) for t in tickers if rng.random() < 0.6}
        mult = {t: 100 for t in tickers if rng.random() < 0.2}
        weights = {t: rng.uniform(-0.2, 0.2) for t in tickers if rng.random() < 0.5}
        quantities = {t: rng.randint(-30, 30) for t in tickers if t not in weights and rng.random() < 0.3}
        to_liquidate = {t for t in held if t not in weights and t not in quantities}
        band = rng.choice([None, 0.0, 0.005, 0.05])
        pv = rng.uniform(10_000, 1_000_000)
        expected = _old_set_holdings_orders(pv, weights, quantities, to_liquidate, prices, held, mult, band)
        plan = rebalancer.plan(CurrentPortfolio.from_mappings(pv, prices, held, mult), weights, quantities,
                               to_liquidate, band)
        assert {i.ticker: i.order_qty for i in plan.instructions} == expected
        assert all(i.order_qty < 0 for i in plan.sells) and all(i.order_qty > 0 for i in plan.buys)


def test_the_rebalancer_knows_nothing_about_strategies_factors_or_brokers():
    path = ROOT / "src/application/services/misbuffet/algorithm/portfolio_rebalancer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    forbidden = ("factor", "strategy", "momentum", "lgbm", "quintile", "dispersion", "rank", "spatio", "broker",
                 "ibkr", "ibapi", "trade_manager", "sqlalchemy", "infrastructure")
    assert not [m for m in imported if any(k in m.lower() for k in forbidden)], imported


# -- set_holdings fed a TargetPortfolio (real repositories, in-memory SQLite, orders to a Mock) -------------------

def test_set_holdings_executes_a_target_portfolio_through_the_existing_path():
    from datetime import datetime

    from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio, slice_at
    p = SqlitePortfolio(cash=100_000.0, shares=("AAPL", "MSFT"))
    try:
        p.upm._algorithm.bar_size_setting = "1 day"
        p.upm._algorithm.time = T0
        for ticker, price in (("AAPL", 150.0), ("MSFT", 400.0)):
            p.seed_close(ticker, datetime(2026, 1, 2), price)
        p.upm.set_holdings({CompanyShare: {"name": "AAPL", "quantity": 10}}, slice_at(T0, AAPL=150.0))
        target = TargetPortfolio(as_of=T0, positions=(
            TargetPortfolioPosition("MSFT", 0.1, asset_type="CompanyShare"),))
        result = p.upm.set_holdings(target, slice_at(T0, AAPL=150.0, MSFT=400.0))
        assert result == {"AAPL": True, "MSFT": True}
        assert (p.qty("AAPL"), p.qty("MSFT")) == (0, 25)           # AAPL liquidated; 100 000 x 0.1 / 400
        # a target without asset types liquidates nothing it cannot scope
        untyped = TargetPortfolio(as_of=T0, positions=(TargetPortfolioPosition("AAPL", 0.0),))
        p.upm.set_holdings(untyped, slice_at(T0, AAPL=150.0, MSFT=400.0))
        assert p.qty("MSFT") == 25
    finally:
        p.close()
