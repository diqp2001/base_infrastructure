"""
STM monthly deciles on the strategy architecture: STMDecileTradingCycle.step -> STMDecileLongShortTradingStrategy ->
portfolio construction (quantile_long_short) -> result.target_portfolio -> set_holdings.

Regression: the pre-refactor ``STMDecileTradingCycle.long_short_weights`` is frozen below; the new path must give the
same book (and so the same orders) for the same decile period.
"""

import ast
import random
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.application.services.misbuffet.algorithm.portfolio_rebalancer import CurrentPortfolio, PortfolioRebalancer
from src.application.services.portfolio_research.decile_portfolios import DecileConfig, DecileResearch
from src.application.services.portfolio_research.stm_decile_cycle import STMDecileTradingCycle
from src.domain.entities.factor.trading_strategy.stm_decile_long_short_strategy import (
    STMDecileLongShortTradingStrategy,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy

ROOT = Path(__file__).resolve().parents[2]
REL, ABS = 1e-12, 1e-15
T = pd.Timestamp("2024-01-31")


def OLD_long_short_weights(period, n_deciles, gross):
    """STMDecileTradingCycle.long_short_weights before the refactor (commit 6809ce4a), frozen."""
    half = gross / 2.0
    top, bottom = period.weights.get(n_deciles, {}), period.weights.get(1, {})
    out = {s: half * w for s, w in top.items()}
    for s, w in bottom.items():
        out[s] = out.get(s, 0.0) - half * w
    return out


def _cycle(n_deciles=10, gross=1.0):
    return STMDecileTradingCycle(SimpleNamespace(members_at=lambda d: []), None, {"A": object()},
                                 DecileConfig(n_deciles=n_deciles), date(2024, 1, 1), date(2024, 12, 31),
                                 traded="A", long_short_gross=gross)


def _case(rng):
    n = rng.choice([2, 5, 10])
    N = rng.randint(n, 80)
    symbols = [f"S{i:03d}" for i in rng.sample(range(500), N)]
    rng.shuffle(symbols)                                                   # any input order
    ties = rng.random() < 0.4
    scores = {s: (round(rng.uniform(-1, 1), 1) if ties else rng.uniform(-1, 1)) for s in symbols}
    return scores, n, rng.choice([0.5, 1.0, 2.0])


def _assert_same(got, expected, ctx):
    assert set(got) == set(expected), ctx
    for a, w in expected.items():
        assert got[a] == pytest.approx(w, rel=REL, abs=ABS), (ctx, a)


def test_the_decile_strategy_is_a_trading_strategy_on_the_stm_score():
    strategy = STMDecileLongShortTradingStrategy(n_deciles=10, gross=1.0)
    assert isinstance(strategy, TradingStrategy)
    (spec,) = strategy.calculate_dependencies
    assert spec.per_entity and spec.key == "score"
    assert spec.factor_type.__name__ == "CompanyShareSpatioTemporalMomentumFactor"
    assert dict(strategy.signals({"A": 0.3, "B": float("nan")}).values) == {"A": 0.3}
    with pytest.raises(ValueError):
        STMDecileLongShortTradingStrategy(n_deciles=1)


def test_the_new_path_gives_the_pre_refactor_book():
    rng = random.Random(20261123)
    for i in range(400):
        scores, n, gross = _case(rng)
        period = DecileResearch(DecileConfig(n_deciles=n)).form(T, scores)
        cycle = _cycle(n, gross)
        expected = OLD_long_short_weights(period, n, gross)
        target = cycle.target_portfolio(period)
        _assert_same(target.weights(), expected, (i, n, gross))
        _assert_same(cycle.long_short_weights(period), expected, ("wrapper", i))
        assert target.strategy_name == "stm_decile_long_short"
        assert all(p.asset_type == "CompanyShare" for p in target)


def test_the_new_path_gives_the_pre_refactor_order_quantities():
    rng = random.Random(11)
    rebalancer = PortfolioRebalancer()
    for i in range(200):
        scores, n, gross = _case(rng)
        period = DecileResearch(DecileConfig(n_deciles=n)).form(T, scores)
        old = OLD_long_short_weights(period, n, gross)
        target = _cycle(n, gross).target_portfolio(period)
        prices = {s: rng.uniform(5, 500) for s in scores}
        held = {s: rng.choice([0, 0, 10, -10, 37]) for s in scores}
        current = CurrentPortfolio.from_mappings(rng.uniform(1e5, 5e6), prices, held)
        a = {x.ticker: x.order_qty for x in rebalancer.plan(current, target_weights=old).instructions}
        b = {x.ticker: x.order_qty for x in rebalancer.plan_target(target, current).instructions}
        assert a == b, i


def test_the_cycle_step_returns_the_target_portfolio():
    members = [f"S{i:02d}" for i in range(20)]
    days = pd.bdate_range("2024-01-01", "2024-03-31")
    rng = np.random.default_rng(3)
    frame = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (len(days), len(members))), axis=0)),
                         index=days, columns=members)
    reader = SimpleNamespace(closes=lambda now: frame.loc[: pd.Timestamp(now).normalize() - pd.Timedelta(days=1)])
    scorer = SimpleNamespace(score=lambda panel, m, t: SimpleNamespace(
        scores={s: float((i * 7) % 20) for i, s in enumerate(m)}, unscored=[], trained_at=t, retrained=True,
        model_assets=m))
    cycle = STMDecileTradingCycle(SimpleNamespace(members_at=lambda d: members), reader, {"A": scorer},
                                  DecileConfig(n_deciles=10), date(2024, 1, 1), date(2024, 12, 31), traded="A",
                                  long_short_gross=1.0)
    results = [r for r in (cycle.step(d + pd.Timedelta(hours=16)) for d in days) if r.rebalance is not None]
    assert len(results) == 2
    for r in results:
        expected = OLD_long_short_weights(r.formed["A"], 10, 1.0)
        _assert_same(r.target_portfolio.weights(), expected, r.rebalance)
        assert r.weights == r.target_portfolio.weights()
        assert len(r.target_portfolio.longs()) == 2 and len(r.target_portfolio.shorts()) == 2


def test_the_algorithm_sends_the_target_portfolio_to_set_holdings():
    path = (ROOT / "src/application/managers/project_managers/stm_monthly_decile_project/backtesting"
            / "base_project_algorithm.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "set_holdings"]
    assert len(calls) == 1
    (arg,) = calls[0].args
    assert ast.unparse(arg) == "result.target_portfolio"
