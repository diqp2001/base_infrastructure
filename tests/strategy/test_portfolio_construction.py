"""
P3 — TargetPortfolio and portfolio construction.

TargetPortfolio holds deterministic target positions; construction turns strategy scores into deterministic target
weights through selection -> weighting -> adjustments; two ready-made methods reproduce the weight rules that live in
the STM and CSM trading cycles today (golden tests: same weights); construction needs no TradeManager, broker,
Order, Transaction or Position.
"""

import ast
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals
from src.domain.entities.finance.portfolio.construction.construction_method import (
    PortfolioConstructionMethod,
    bucket_long_short,
    quantile_long_short_inverse_volatility,
    volatility_targeted_signals,
)
from src.domain.entities.finance.portfolio.construction.steps import (
    AllAssets,
    AssetWeightLimit,
    Buckets,
    ConstructionInputs,
    EqualWeighting,
    ExposureLimit,
    GrossExposureCap,
    Normalise,
    NetExposureLimit,
    QuantileLongShort,
    ScoreWeighting,
    Threshold,
    TopBottomN,
)
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio, TargetPortfolioPosition

AS_OF = datetime(2026, 1, 5, 16, 0)
ROOT = Path(__file__).resolve().parents[2]


# -- TargetPortfolio -----------------------------------------------------------------------------------------------

def test_a_target_portfolio_holds_deterministic_target_positions():
    target = TargetPortfolio(as_of=AS_OF, strategy_name="s", positions=(
        TargetPortfolioPosition("MSFT", -0.25, asset_type="CompanyShare", financial_asset_id=2),
        TargetPortfolioPosition("AAPL", 0.5, asset_type="CompanyShare", financial_asset_id=1),
        TargetPortfolioPosition("JPM", 0.0)))
    assert target.symbols() == ["AAPL", "JPM", "MSFT"]                   # sorted, whatever the input order
    assert target.weights() == {"AAPL": 0.5, "JPM": 0.0, "MSFT": -0.25}
    assert (target.gross_exposure, target.net_exposure) == (0.75, 0.25)
    assert [p.symbol for p in target.longs()] == ["AAPL"] and [p.symbol for p in target.shorts()] == ["MSFT"]
    assert target.get("AAPL").financial_asset_id == 1 and target.get("XOM") is None
    assert target.get("JPM").side == 0 and target.get("MSFT").side == -1
    same = TargetPortfolio.from_weights({"JPM": 0.0, "MSFT": -0.25, "AAPL": 0.5}, as_of=AS_OF, strategy_name="s")
    assert same.weights() == target.weights()


def test_a_target_portfolio_rejects_duplicates_and_non_finite_weights():
    with pytest.raises(ValueError):
        TargetPortfolio(as_of=AS_OF, positions=(TargetPortfolioPosition("AAPL", 0.1),
                                                TargetPortfolioPosition("AAPL", 0.2)))
    with pytest.raises(ValueError):
        TargetPortfolioPosition("AAPL", float("inf"))
    with pytest.raises(ValueError):
        TargetPortfolioPosition("", 0.1)


def test_a_target_position_is_not_an_account_position_or_holding():
    from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
    from src.domain.entities.finance.holding.position import Position
    assert not issubclass(TargetPortfolioPosition, (Position, PortfolioHolding))
    assert not issubclass(TargetPortfolio, (Position, PortfolioHolding))


# -- selection / weighting / adjustments --------------------------------------------------------------------------

SCORES = {"A": 0.9, "B": 0.1, "C": -0.4, "D": 0.5, "E": -0.8, "F": 0.0, "G": 0.3, "H": -0.2, "I": 0.7, "J": -0.6}


def test_selection_steps_are_deterministic():
    inputs = ConstructionInputs(scores=SCORES)
    assert QuantileLongShort(0.2).select(inputs) == {"A": 1, "I": 1, "E": -1, "J": -1}
    assert QuantileLongShort(0.2, long_only=True).select(inputs) == {"A": 1, "I": 1}
    assert QuantileLongShort(0.2).select(ConstructionInputs(scores={"A": 1.0})) == {}     # < 2 candidates
    assert TopBottomN(1, 2).select(inputs) == {"A": 1, "E": -1, "J": -1}
    assert Threshold(long_above=0.6, short_below=-0.5).select(inputs) == {"A": 1, "I": 1, "E": -1, "J": -1}
    assert AllAssets().select(inputs)["F"] == 0
    # ties are broken by symbol, not by input order
    tied = {"Z": 1.0, "Y": 1.0, "X": 0.0, "W": 0.0}
    assert QuantileLongShort(0.25).select(ConstructionInputs(scores=tied)) == {"Z": 1, "W": -1}
    assert QuantileLongShort(0.25).select(ConstructionInputs(scores=dict(reversed(tied.items())))) == {"Z": 1, "W": -1}


def test_weighting_and_adjustment_steps():
    inputs = ConstructionInputs(scores=SCORES)
    equal = PortfolioConstructionMethod("eq", QuantileLongShort(0.2), EqualWeighting(), (Normalise(1.0),))
    assert equal.weights(inputs) == {"A": 0.25, "E": -0.25, "I": 0.25, "J": -0.25}
    score = PortfolioConstructionMethod("score", Threshold(0.6, -0.5), ScoreWeighting(), (Normalise(3.0),))
    assert score.weights(inputs) == pytest.approx({"A": 0.9, "I": 0.7, "E": -0.8, "J": -0.6})
    assert GrossExposureCap(1.0).adjust({"A": 0.3, "B": -0.2}, inputs) == {"A": 0.3, "B": -0.2}     # never up
    assert GrossExposureCap(1.0).adjust({"A": 1.5, "B": -0.5}, inputs) == {"A": 0.75, "B": -0.25}
    net = NetExposureLimit(0.1).adjust({"A": 0.6, "B": -0.2}, inputs)                               # longs scaled
    assert net == pytest.approx({"A": 0.3, "B": -0.2}) and sum(net.values()) == pytest.approx(0.1)
    assert NetExposureLimit(0.0).adjust({"A": 0.2, "B": -0.5}, inputs) == pytest.approx({"A": 0.2, "B": -0.2})
    assert AssetWeightLimit(0.1).adjust({"A": 0.3, "B": -0.05, "C": -0.4}, inputs) == {"A": 0.1, "B": -0.05,
                                                                                        "C": -0.1}


# -- strategy-specific construction methods ------------------------------------------------------------------------

def test_strategy_a_quintiles_long_q5_short_q1():
    quintiles = {"AAPL": 5, "MSFT": 1, "JPM": 3, "XOM": 5, "CVX": 1, "KO": 2, "PG": 4}
    target = bucket_long_short().build(ConstructionInputs(scores=quintiles), as_of=AS_OF, strategy_name="lgbm_q",
                                       asset_type="CompanyShare")
    assert target.weights() == {"AAPL": 0.25, "CVX": -0.25, "MSFT": -0.25, "XOM": 0.25}
    assert target.construction == "bucket_long_short" and target.gross_exposure == 1.0 and target.net_exposure == 0
    with pytest.raises(ValueError):
        Buckets({5}, {5})


def test_strategy_b_reproduces_the_stm_volatility_targeted_weights():
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
        signals_to_weights,
    )
    signals = {"AAPL": 0.8, "MSFT": -0.3, "JPM": 0.05, "XOM": -0.9, "NOVOL": 0.4}
    vol = {"AAPL": 0.012, "MSFT": 0.02, "JPM": 0.015, "XOM": 0.03, "NOVOL": 0.0}      # NOVOL: no usable vol -> 0
    inputs = ConstructionInputs(scores=signals, volatility=vol)
    for cap in (None, 0.5, 10.0):
        expected = signals_to_weights(signals, vol, target_vol=0.15, gross_cap=cap)
        got = volatility_targeted_signals(0.15, gross_cap=cap).weights(inputs)
        assert got.keys() == expected.keys()
        assert all(math.isclose(got[a], expected[a], rel_tol=1e-12, abs_tol=1e-15) for a in expected), (cap, got)
    assert volatility_targeted_signals(0.15).weights(ConstructionInputs(scores={})) == {}


def test_the_quantile_inverse_volatility_method_reproduces_the_csm_weights():
    from src.application.services.data.entities.factor.cross_sectional_momentum.csm_trading_cycle import (
        long_short_weights,
    )
    scores = {f"S{i}": s for i, s in enumerate([0.61, 0.42, 0.55, 0.38, 0.71, 0.49, 0.33, 0.66, 0.52, 0.45])}
    vol = {a: 0.01 + 0.002 * i for i, a in enumerate(scores)}
    vol["S4"] = float("nan")                                      # not usable: not a candidate
    for quantile, gross in ((0.2, 1.0), (0.3, 2.0), (0.05, 1.0)):
        expected = long_short_weights(scores, vol, quantile, gross)
        got = quantile_long_short_inverse_volatility(quantile, gross).weights(
            ConstructionInputs(scores=scores, volatility=vol))
        assert got == pytest.approx(expected) and got.keys() == expected.keys(), (quantile, gross)


def test_strategy_c_option_selection_under_a_delta_limit():
    scores = {"AAPL_C150": 0.9, "AAPL_P140": -0.7, "MSFT_C400": 0.6, "MSFT_P380": -0.2}
    delta = {"AAPL_C150": 0.6, "AAPL_P140": -0.4, "MSFT_C400": 0.5, "MSFT_P380": -0.3}
    method = PortfolioConstructionMethod("options", Threshold(0.5, -0.5), EqualWeighting(),
                                         (Normalise(1.0), ExposureLimit("delta", 0.1)))
    weights = method.weights(ConstructionInputs(scores=scores, loadings={"delta": delta}))
    assert set(weights) == {"AAPL_C150", "AAPL_P140", "MSFT_C400"}
    assert abs(sum(w * delta[a] for a, w in weights.items())) == pytest.approx(0.1)
    with pytest.raises(ValueError):                               # a weighted option without delta: no default
        method.weights(ConstructionInputs(scores=scores, loadings={"delta": {"AAPL_C150": 0.6}}))


def test_construction_is_deterministic():
    shuffled = dict(sorted(SCORES.items(), key=lambda kv: -kv[1]))
    vol = {a: 0.01 * (i + 1) for i, a in enumerate(sorted(SCORES))}
    method = quantile_long_short_inverse_volatility(0.3, 1.0)
    first = method.build(ConstructionInputs(scores=SCORES, volatility=vol), as_of=AS_OF)
    second = method.build(ConstructionInputs(scores=shuffled, volatility=vol), as_of=AS_OF)
    assert first == second and list(first.weights()) == sorted(first.weights())
    with pytest.raises(ValueError):
        ConstructionInputs(scores={"A": float("nan")})


def test_the_service_turns_strategy_signals_into_a_target_portfolio():
    from src.application.services.portfolio_construction.portfolio_construction_service import (
        PortfolioConstructionService,
    )
    signals = StrategySignals(as_of=AS_OF, values={"AAPL": 0.8, "MSFT": -0.3}, asset_type="CompanyShare",
                              context={"volatility": {"AAPL": 0.01, "MSFT": 0.02}})
    target = PortfolioConstructionService().construct(signals, volatility_targeted_signals(0.15),
                                                      asset_ids={"AAPL": 1, "MSFT": 2}, strategy_name="stm")
    k = 0.15 / 252 ** 0.5 / 2
    assert target.weights() == pytest.approx({"AAPL": 0.8 * k / 0.01, "MSFT": -0.3 * k / 0.02})
    assert (target.as_of, target.strategy_name, target.get("MSFT").financial_asset_id) == (AS_OF, "stm", 2)
    assert target.get("AAPL").asset_type == "CompanyShare"


# -- separation from execution -------------------------------------------------------------------------------------

CONSTRUCTION_MODULES = (
    "src.domain.entities.finance.portfolio.target_portfolio",
    "src.domain.entities.finance.portfolio.construction.steps",
    "src.domain.entities.finance.portfolio.construction.construction_method",
    "src.application.services.portfolio_construction.portfolio_construction_service",
)
EXECUTION_MARKERS = ("trade_manager", "broker", "ibkr", "ibapi", "ib_insync", "sqlalchemy", ".order", ".transaction",
                     ".position", "portfolio_manager", "misbuffet")


def test_construction_does_not_import_execution_code():
    for name in CONSTRUCTION_MODULES:
        path = ROOT / (name.replace(".", "/") + ".py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not [m for m in imported if any(k in m.lower() for k in EXECUTION_MARKERS)], (name, imported)


def test_construction_runs_without_loading_any_execution_module():
    """In a fresh interpreter: build a TargetPortfolio, then check which modules got loaded."""
    code = (
        "import json, sys\n"
        "from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals\n"
        "from src.application.services.portfolio_construction.portfolio_construction_service import "
        "PortfolioConstructionService\n"
        "from src.domain.entities.finance.portfolio.construction.construction_method import bucket_long_short\n"
        "t = PortfolioConstructionService().construct(StrategySignals(as_of=None, values={'A': 5, 'B': 1}), "
        "bucket_long_short())\n"
        "print(json.dumps({'weights': t.weights(), 'modules': sorted(sys.modules)}))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    result = json.loads(out.stdout.strip().splitlines()[-1])
    assert result["weights"] == {"A": 0.5, "B": -0.5}
    loaded = [m for m in result["modules"] if m.startswith(("src.", "sqlalchemy", "ibapi", "ib_insync"))]
    assert not [m for m in loaded if any(k in m.lower() for k in EXECUTION_MARKERS)], loaded
