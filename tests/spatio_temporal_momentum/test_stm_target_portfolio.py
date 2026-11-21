"""
P6 — STM on the strategy -> construction -> TargetPortfolio -> rebalancer path, with unchanged behaviour.

OLD = the pre-P6 ``signals_to_weights`` (frozen copy below). For representative inputs the NEW TargetPortfolio
weights match it within TOLERANCE, and so do the target and order quantities the rebalancer derives from them.
The real STMTradingCycle (tiny model, in-memory DB) returns a TargetPortfolio whose weights are the OLD weights of
its own scores; the full and the live algorithms pass that TargetPortfolio to set_holdings.
"""

import ast
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.application.services.misbuffet.algorithm.portfolio_rebalancer import CurrentPortfolio, PortfolioRebalancer
from src.application.services.portfolio_construction.portfolio_construction_service import (
    PortfolioConstructionService,
)
from src.domain.entities.factor.trading_strategy.spatio_temporal_momentum_strategy import (
    SpatioTemporalMomentumTradingStrategy,
)
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio

ROOT = Path(__file__).resolve().parents[2]
REL_TOL, ABS_TOL = 1e-12, 1e-15          # TOLERANCE: same arithmetic, so only float rounding may differ


def OLD_signals_to_weights(signals, daily_vol, target_vol=0.15, gross_cap=None, periods_per_year=252):
    """signals_to_weights as it was before P6 (stm_backtest.py), frozen for the regression."""
    n = len(signals)
    if n == 0:
        return {}
    weights = {}
    for asset, s in signals.items():
        vol = daily_vol.get(asset)
        if vol is None or not np.isfinite(vol) or vol <= 0:
            weights[asset] = 0.0
            continue
        weights[asset] = float(s) * target_vol / (vol * periods_per_year ** 0.5) / n
    if gross_cap:
        gross = sum(abs(w) for w in weights.values())
        if gross > gross_cap:
            weights = {a: w * gross_cap / gross for a, w in weights.items()}
    return weights


def NEW_target(scores, daily_vol, target_vol, gross_cap, periods_per_year, asset_ids=None):
    """What STMTradingCycle.step now does with the model's scores."""
    strategy = SpatioTemporalMomentumTradingStrategy(target_vol=target_vol, gross_cap=gross_cap,
                                                     periods_per_year=periods_per_year)
    signals = strategy.signals(scores, daily_vol)
    return PortfolioConstructionService().construct(signals, strategy.construction_method(), asset_ids=asset_ids,
                                                    strategy_name=strategy.name)


def close(a, b):
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def cases(n=400, seed=11):
    """Representative STM decisions: tanh-like and unbounded (TFT) signals, missing / zero / NaN vols, every cap."""
    rng = random.Random(seed)
    for _ in range(n):
        tickers = [f"T{i:02d}" for i in range(rng.randint(1, 30))]
        bound = rng.choice([1.0, 5.0])
        scores = {t: rng.uniform(-bound, bound) for t in tickers}
        vol = {}
        for t in tickers:
            r = rng.random()
            if r < 0.05:
                continue                                   # missing
            vol[t] = 0.0 if r < 0.08 else float("nan") if r < 0.1 else rng.uniform(0.002, 0.05)
        yield (scores, vol, rng.choice([0.10, 0.15, 0.25]), rng.choice([None, 0.5, 1.0, 3.0]),
               rng.choice([252, 252 * 39, 252 * 7]))


def test_new_target_portfolio_weights_match_the_old_stm_weights():
    checked = 0
    for scores, vol, target_vol, cap, periods in cases():
        old = OLD_signals_to_weights(scores, vol, target_vol, cap, periods)
        new = NEW_target(scores, vol, target_vol, cap, periods).weights()
        assert new.keys() == old.keys()                    # every scored asset (zero-vol ones at 0)
        assert all(close(new[a], old[a]) for a in old), (scores, vol, cap)
        assert all(np.sign(new[a]) == np.sign(old[a]) for a in old)
        checked += len(old)
    assert checked > 1000


def test_the_kept_signals_to_weights_wrapper_gives_the_old_weights_in_the_callers_order():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
        signals_to_weights,
    )
    for scores, vol, target_vol, cap, periods in cases(100, seed=3):
        old = OLD_signals_to_weights(scores, vol, target_vol, cap, periods)
        new = signals_to_weights(scores, vol, target_vol, cap, periods_per_year=periods)
        assert list(new) == list(old) and all(close(new[a], old[a]) for a in old)
    assert signals_to_weights({}, {}) == {}


def test_target_and_order_quantities_are_unchanged():
    """OLD weights through the class-keyed set_holdings path vs the NEW TargetPortfolio: same target and order
    quantities (held assets absent from the decision are liquidated in both)."""
    rng = random.Random(5)
    rebalancer = PortfolioRebalancer()
    compared = 0
    for scores, vol, target_vol, cap, periods in cases(200, seed=9):
        tickers = list(scores) + ["OLD1", "OLD2"]          # held, no longer scored
        prices = {t: round(rng.uniform(5, 600), 2) for t in tickers}
        held = {t: rng.randint(-40, 120) for t in tickers if rng.random() < 0.6}
        current = CurrentPortfolio.from_mappings(rng.uniform(5e4, 5e6), prices, held)
        liquidate = {t for t in held if t not in scores}
        old_weights = OLD_signals_to_weights(scores, vol, target_vol, cap, periods)
        old = rebalancer.plan(current, target_weights=old_weights, liquidate=liquidate).by_ticker()
        new = rebalancer.plan_target(NEW_target(scores, vol, target_vol, cap, periods), current,
                                     liquidate=liquidate).by_ticker()
        assert {t: (i.target_qty, i.order_qty) for t, i in new.items()} == {
            t: (i.target_qty, i.order_qty) for t, i in old.items()}
        compared += len(old)
    assert compared > 500


def test_the_live_shortable_restriction_edits_the_target_portfolio():
    target = NEW_target({"AAPL": 0.8, "JPM": -0.6, "XOM": -0.2}, {"AAPL": 0.01, "JPM": 0.02, "XOM": 0.015},
                        0.15, 1.0, 252, asset_ids={"AAPL": 1, "JPM": 2, "XOM": 3})
    restricted = target.with_weights({**target.weights(), "JPM": 0.0})
    assert restricted.weights() == {**target.weights(), "JPM": 0.0}
    assert restricted.get("JPM").financial_asset_id == 2 and restricted.strategy_name == target.strategy_name
    with pytest.raises(ValueError):
        target.with_weights({"MSFT": 0.1})


def test_the_cycle_has_no_private_signal_to_weight_rule_and_the_algorithms_pass_the_target():
    cycle = (ROOT / "src/application/services/data/entities/factor/spatio_temporal_momentum/stm_trading_cycle.py")
    tree = ast.parse(cycle.read_text(encoding="utf-8"))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "signals_to_weights" not in imported and "SpatioTemporalMomentumTradingStrategy" in imported
    assert "target_vol /" not in cycle.read_text(encoding="utf-8")
    for project in ("spatio_temporal_momentum_project_full", "spatio_temporal_momentum_project_10m_live"):
        text = (ROOT / "src/application/managers/project_managers" / project / "backtesting"
                / "base_project_algorithm.py").read_text(encoding="utf-8")
        on_data = text[text.index("def on_data"):]
        assert "set_holdings(" in on_data and "{CompanyShare: [{'name'" not in on_data, project
        assert "target_portfolio" in on_data, project


# -- the real cycle (tiny model, in-memory database) -------------------------------------------------------------

def test_the_trading_cycle_returns_the_old_weights_as_a_target_portfolio():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import periods_per_year
    from tests.spatio_temporal_momentum.helpers import synthetic_closes
    from tests.spatio_temporal_momentum.test_stm_trading_cycle import ENTITY_IDS, _bars, _Env
    env = _Env(synthetic_closes(900))
    try:
        cycle = env.cycle(retrain_every_days=120)
        results = [cycle.step(t) for t in _bars("2016-08-01", "2016-08-12")]
        scored = [r for r in results if r.scores]
        assert scored
        periods = periods_per_year(env.cfg.bar_minutes)
        for r in scored:
            assert isinstance(r.target_portfolio, TargetPortfolio) and r.weights == r.target_portfolio.weights()
            old = OLD_signals_to_weights(r.scores, r.daily_vol, env.cfg.training.target_vol, 1.0, periods)
            assert r.weights.keys() == old.keys() and all(close(r.weights[a], old[a]) for a in old)
            assert {p.asset_type for p in r.target_portfolio} == {"CompanyShare"}
            assert all(p.financial_asset_id == ENTITY_IDS[p.symbol] for p in r.target_portfolio)
            assert r.target_portfolio.as_of == pd.Timestamp(r.session).to_pydatetime()
    finally:
        env.close()
