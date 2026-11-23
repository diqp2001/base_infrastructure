"""
CSM on the strategy architecture: CSMTradingCycle.step -> CrossSectionalMomentumTradingStrategy -> portfolio
construction (quantile_long_short_inverse_volatility) -> result.target_portfolio -> set_holdings.

Regression: the pre-refactor ``long_short_weights`` is frozen below; the new path must give the same weights (and so
the same orders) on the inputs the cycle produces (scores in symbol order: the CSM dataset is sorted by
(date, asset)).
"""

import ast
import random
from pathlib import Path
import numpy as np
import pytest

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
    long_short_weights,
)
from src.application.services.misbuffet.algorithm.portfolio_rebalancer import CurrentPortfolio, PortfolioRebalancer
from src.application.services.portfolio_construction.portfolio_construction_service import (
    PortfolioConstructionService,
)
from src.domain.entities.factor.trading_strategy.cross_sectional_momentum_strategy import (
    CrossSectionalMomentumTradingStrategy,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy

pytestmark = pytest.mark.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
REL, ABS = 1e-12, 1e-15


def OLD_long_short_weights(scores, daily_vol, quantile, gross):
    """csm_trading_cycle.long_short_weights before the refactor (commit 6809ce4a), frozen."""
    usable = {a: s for a, s in scores.items()
              if np.isfinite(s) and np.isfinite(daily_vol.get(a, np.nan)) and daily_vol.get(a, 0) > 0}
    n = len(usable)
    k = int(np.floor(n * quantile))
    if n < 2 or k < 1:
        return {}
    ranked = sorted(usable, key=lambda a: usable[a])
    shorts, longs = ranked[:k], ranked[-k:]
    weights = {}
    for side, names in ((1.0, longs), (-1.0, shorts)):
        inv = {a: 1.0 / daily_vol[a] for a in names}
        total = sum(inv.values())
        for a, v in inv.items():
            weights[a] = side * (gross / 2.0) * v / total
    return weights


def _new_target(scores, vol, quantile, gross, ids=None):
    strategy = CrossSectionalMomentumTradingStrategy(quantile=quantile, gross=gross)
    return PortfolioConstructionService().construct(strategy.signals(scores, vol), strategy.construction_method(),
                                                    asset_ids=ids, strategy_name=strategy.name)


def _case(rng):
    n = rng.randint(0, 40)
    symbols = sorted(f"S{i:02d}" for i in rng.sample(range(100), n))     # symbol order, as the CSM dataset gives
    tie_grid = rng.random() < 0.4                                        # tree models give tied probabilities
    scores = {s: (round(rng.random(), 1) if tie_grid else rng.random()) for s in symbols}
    vol = {}
    for s in symbols:
        u = rng.random()
        vol[s] = float("nan") if u < 0.05 else 0.0 if u < 0.08 else -0.01 if u < 0.1 else rng.uniform(0.005, 0.05)
    if symbols and rng.random() < 0.1:
        vol.pop(rng.choice(symbols))                                     # a scored asset with no volatility at all
    return scores, vol, rng.choice([0.05, 0.1, 0.2, 0.25, 0.3, 0.5]), rng.choice([0.5, 1.0, 2.0])


def _assert_same(got, expected, ctx):
    assert set(got) == set(expected), ctx
    for a, w in expected.items():
        assert got[a] == pytest.approx(w, rel=REL, abs=ABS), (ctx, a)


def test_the_csm_strategy_is_a_trading_strategy_on_the_csm_signal():
    strategy = CrossSectionalMomentumTradingStrategy(quantile=0.2, gross=1.0)
    assert isinstance(strategy, TradingStrategy)
    (spec,) = strategy.calculate_dependencies
    assert spec.per_entity and spec.key == "score"
    assert spec.factor_type.__name__ == "CompanyShareCrossSectionalMomentumFactor"
    s = strategy.signals({"A": 0.7, "B": float("nan")}, {"A": 0.01})
    assert dict(s.values) == {"A": 0.7} and s.context["volatility"] == {"A": 0.01}    # a NaN score is never ranked
    with pytest.raises(ValueError):
        strategy.evaluate({"score": {"A": [0.7]}})                                   # no volatility input
    with pytest.raises(ValueError):
        CrossSectionalMomentumTradingStrategy(quantile=0.6)


def test_the_new_path_gives_the_pre_refactor_weights():
    rng = random.Random(20261123)
    for i in range(500):
        scores, vol, q, gross = _case(rng)
        expected = OLD_long_short_weights(scores, vol, q, gross)
        target = _new_target(scores, vol, q, gross)
        _assert_same(target.weights(), expected, (i, q, gross))
        _assert_same(long_short_weights(scores, vol, q, gross), expected, ("wrapper", i))


def test_the_new_path_gives_the_pre_refactor_order_quantities():
    rng = random.Random(7)
    rebalancer = PortfolioRebalancer()
    for i in range(200):
        scores, vol, q, gross = _case(rng)
        old = OLD_long_short_weights(scores, vol, q, gross)
        target = _new_target(scores, vol, q, gross)
        prices = {s: rng.uniform(5, 500) for s in scores}
        held = {s: rng.choice([0, 0, 10, -10, 37]) for s in scores}
        current = CurrentPortfolio.from_mappings(rng.uniform(1e5, 5e6), prices, held)
        a = {x.ticker: x.order_qty for x in rebalancer.plan(current, target_weights=old).instructions}
        b = {x.ticker: x.order_qty for x in rebalancer.plan_target(target, current).instructions}
        assert a == b, i


def test_the_target_portfolio_carries_the_assets_and_the_strategy():
    target = _new_target({"A": 0.9, "B": 0.1, "C": 0.5, "D": 0.2, "E": 0.8},
                         {"A": 0.01, "B": 0.02, "C": 0.01, "D": 0.01, "E": 0.02}, 0.2, 1.0,
                         ids={"A": 1, "B": 2, "C": 3, "D": 4, "E": 5})
    assert {p.symbol: (p.side, p.financial_asset_id, p.asset_type) for p in target} == {
        "A": (1, 1, "CompanyShare"), "B": (-1, 2, "CompanyShare")}
    assert target.strategy_name == "cross_sectional_momentum"
    assert target.gross_exposure == pytest.approx(1.0) and target.net_exposure == pytest.approx(0.0)


def test_the_cycle_produces_the_target_portfolio_with_the_pre_refactor_weights():
    from src.application.managers.project_managers.cross_sectionnal_project.backtesting.synthetic_demo import (
        run_synthetic_demo,
    )
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
        STMProgressTracker,
    )
    tracker = STMProgressTracker()
    tracker.start("csm target portfolio")
    _report, results, cycle = run_synthetic_demo(tracker, backtest_sessions=8, n_trials=3,
                                                 tickers=[f"T{i}" for i in range(10)], keep_cycle=True)
    try:
        training = cycle.config.training
        decided = [r for r in results if r.scores]
        assert decided
        for r in decided:
            expected = OLD_long_short_weights(r.scores, r.daily_vol, training.long_short_quantile,
                                              training.gross_exposure)
            assert r.target_portfolio is not None
            _assert_same(r.target_portfolio.weights(), expected, r.session)
            assert r.weights == r.target_portfolio.weights()
            assert all(p.financial_asset_id == cycle.ticker_to_entity[p.symbol] for p in r.target_portfolio)
    finally:
        cycle.factory.session.close()


@pytest.mark.parametrize("project", ["cross_sectionnal_project", "cross_sectionnal_project_10m",
                                     "spatio_temporal_momentum_project", "spatio_temporal_momentum_project_10m",
                                     "spatio_temporal_momentum_project_10m_hourly",
                                     "spatio_temporal_momentum_project_full"])
def test_the_algorithms_send_the_target_portfolio_to_set_holdings(project):
    path = ROOT / "src/application/managers/project_managers" / project / "backtesting/base_project_algorithm.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "set_holdings"]
    assert len(calls) == 1
    (arg,) = calls[0].args
    assert ast.unparse(arg) == "result.target_portfolio"
