"""
The model-filtered dispersion project on the strategy architecture: DispersionTradingCycle opens a month through
ETFCallDispersionTradingStrategy -> construct_dispersion_trade -> dispersion_target_portfolio, and the algorithm sends
result.target_portfolio (option contracts) to set_holdings.

Regression: on the synthetic world, every trade, and every step's contract targets, equal what the pre-refactor cycle
built from the same legs and scores (select_constituents + DispersionPortfolioConstructionService, then
{ETF call: -N, selected calls: q} at an opening and 0 for the traded legs at a settlement).
"""

import ast
from datetime import date
from pathlib import Path

import pytest

from src.application.managers.project_managers.etf_dispersion_stm_project.backtesting.synthetic_demo import (
    run_synthetic_demo,
)
from src.application.services.dispersion.dispersion_portfolio_construction_service import (
    WHOLE,
    DispersionPortfolioConstructionService,
)
from src.application.services.dispersion.dispersion_trading_cycle import MODEL_FILTERED, ORIGINAL
from src.application.services.dispersion.model_selection import ModelFilterConfig, select_constituents

pytestmark = pytest.mark.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[2]


def _old_targets(results, traded):
    """The pre-refactor cycle's targets, step by step, from each month's legs and scores."""
    out, open_month = [], None
    for r in results:
        targets = {}
        if r.settled is not None:
            legs = r.settled.trade.original if traded == ORIGINAL else r.settled.trade.filtered
            etf = r.settled.trade.etf.symbol
            for underlying in [etf] + list(legs.positions):
                targets[r.settled.option_symbols[underlying]] = 0
        if r.opened is not None:
            m = r.opened
            selection = select_constituents([c.symbol for c in m.trade.constituents], m.scores.scores,
                                            ModelFilterConfig(minimum_model_score=0.0), m.scores.unscored)
            trade = DispersionPortfolioConstructionService(WHOLE).construct(m.opened, m.expiry, m.trade.etf,
                                                                            m.trade.constituents, selection)
            assert trade.etf_contracts == m.trade.etf_contracts
            assert trade.original.positions == m.trade.original.positions
            assert trade.filtered.positions == m.trade.filtered.positions
            assert dict(trade.selection.rejected) == dict(m.trade.selection.rejected)
            legs = trade.original if traded == ORIGINAL else trade.filtered
            etf = trade.etf.symbol
            for underlying, qty in [(etf, -legs.etf_contracts)] + list(legs.positions.items()):
                targets[m.option_symbols[underlying]] = int(round(qty))
            open_month = m
        out.append(targets)
    assert open_month is not None
    return out


@pytest.mark.parametrize("traded", [MODEL_FILTERED, ORIGINAL])
def test_the_cycle_targets_are_the_pre_refactor_targets(traded):
    results, cycle, _ = run_synthetic_demo(end=date(2020, 12, 31), traded=traded)
    expected = _old_targets(results, traded)
    assert any(r.settled is not None for r in results) and any(r.opened is not None for r in results)
    for r, old in zip(results, expected):
        assert r.targets == old, r.time
        if not old:
            assert r.target_portfolio is None
            continue
        target = r.target_portfolio
        assert {p.symbol: int(round(p.target_quantity)) for p in target} == old
        assert all(p.asset_type == ("ETFShareOption" if cycle.is_etf_leg(p.symbol) else "CompanyShareOption")
                   for p in target)
        assert target.strategy_name == "etf_call_dispersion"
        if r.opened is not None:
            assert target.context["etf_contracts"] == r.opened.trade.etf_contracts


def test_a_step_that_settles_and_opens_carries_both_in_one_target():
    results, _, _ = run_synthetic_demo(end=date(2020, 12, 31))
    both = [r for r in results if r.settled is not None and r.opened is not None]
    assert both
    r = both[0]
    closing = {r.settled.option_symbols[u] for u in [r.settled.trade.etf.symbol] + list(r.settled.trade.filtered.positions)}
    assert closing <= set(r.target_portfolio.symbols())
    assert all(r.target_portfolio.get(s).target_quantity == 0 for s in closing)


def test_the_algorithm_sends_the_target_portfolio_to_set_holdings():
    path = (ROOT / "src/application/managers/project_managers/etf_dispersion_stm_project/backtesting"
            / "base_project_algorithm.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "set_holdings"]
    assert len(calls) == 1
    assert ast.unparse(calls[0].args[0]) == "result.target_portfolio"
    assert {k.arg: ast.unparse(k.value) for k in calls[0].keywords}["liquidate_unlisted"] == "False"
