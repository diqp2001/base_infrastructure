"""
P5 — LGBM quintile long/short TradingStrategy.

    Universe -> LGBM cross-sectional quintile ranking factor -> TradingStrategy -> PortfolioConstruction
             -> TargetPortfolio     (never ranking factor -> order)

Deterministic ranking values: Q5 long, Q1 short, Q2-Q4 no position; weight normalisation; missing scores;
insufficient universe; the Universe stays a pure constituent listing; no order, transaction or position is written.
"""

import ast
import dataclasses
import inspect
from datetime import date, datetime
from pathlib import Path

import pytest

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (  # noqa: E501
    CompanyShareLGBMCSQuintileRankMomentumFactor as QuintileRank,
)
from src.domain.entities.factor.trading_strategy import lgbm_quintile_long_short_strategy as strategy_module
from src.domain.entities.factor.trading_strategy.lgbm_quintile_long_short_strategy import (
    CROSS_SECTIONAL_QUINTILES,
    LGBMQuintileLongShortStrategy,
)
from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy
from src.domain.entities.finance.portfolio.construction.steps import ConstructionInputs, quantile_labels
from src.domain.entities.finance.portfolio.target_portfolio import TargetPortfolio

AS_OF = datetime(2026, 1, 5, 16, 0)
QUINTILES = {"AAPL": 5.0, "MSFT": 5.0, "JPM": 1.0, "XOM": 1.0, "KO": 3.0, "PG": 2.0, "CVX": 4.0}


def target_of(strategy, per_constituent):
    """dependencies as the resolution service delivers them -> signals -> the strategy's construction."""
    signals = strategy.evaluate({"score": per_constituent}, as_of=AS_OF)
    return strategy.construction_method().build(ConstructionInputs(scores=dict(signals.values)), as_of=AS_OF,
                                                strategy_name=strategy.name, asset_type=signals.asset_type)


def stored(values):
    return {s: [v] for s, v in values.items()}


# -- the strategy over deterministic ranking values ----------------------------------------------------------------

def test_q5_long_q1_short_and_q2_to_q4_hold_nothing():
    target = target_of(LGBMQuintileLongShortStrategy(), stored(QUINTILES))
    assert target.weights() == {"AAPL": 0.25, "JPM": -0.25, "MSFT": 0.25, "XOM": -0.25}
    assert not {"KO", "PG", "CVX"} & set(target.symbols())
    assert target.get("AAPL").asset_type == "CompanyShare" and target.strategy_name == "lgbm_cs_quintile_long_short"


def test_weights_are_normalised_equal_inside_each_side_and_dollar_neutral():
    target = target_of(LGBMQuintileLongShortStrategy(gross=2.0), stored({**QUINTILES, "BA": 5.0}))
    longs, shorts = target.longs(), target.shorts()
    assert [p.target_weight for p in longs] == pytest.approx([1 / 3] * 3)       # 3 longs share gross/2 = 1.0
    assert [p.target_weight for p in shorts] == pytest.approx([-0.5] * 2)       # 2 shorts share 1.0
    assert target.gross_exposure == pytest.approx(2.0) and target.net_exposure == pytest.approx(0.0)


def test_a_model_label_returned_as_a_float_is_read_as_its_quintile():
    target = target_of(LGBMQuintileLongShortStrategy(), stored({"AAPL": 4.6, "JPM": 1.4, "KO": 3.2}))
    assert target.weights() == {"AAPL": 0.5, "JPM": -0.5}


def test_constituents_without_a_score_are_left_out():
    values = {**stored(QUINTILES), "BA": []}                    # a member the factor gave no value for
    target = target_of(LGBMQuintileLongShortStrategy(), values)
    assert "BA" not in target.symbols() and len(target) == 4


def test_an_insufficient_universe_gives_an_empty_target():
    strategy = LGBMQuintileLongShortStrategy()
    assert len(target_of(strategy, stored({"AAPL": 5.0, "MSFT": 4.0, "KO": 3.0}))) == 0   # no Q1: no short side
    assert len(target_of(strategy, {})) == 0
    assert strategy.evaluate({}).note == "no ranking value for any constituent"
    cross = LGBMQuintileLongShortStrategy(quintiles=CROSS_SECTIONAL_QUINTILES)
    assert len(target_of(cross, stored({"A": 0.9, "B": 0.1, "C": 0.5, "D": 0.3}))) == 0     # 4 < 5 constituents


def test_cross_sectional_quintiles_rank_the_values_like_the_decile_project():
    scores = {f"S{i:02d}": v for i, v in enumerate([0.61, 0.42, 0.55, 0.38, 0.71, 0.49, 0.33, 0.66, 0.52, 0.45])}
    target = target_of(LGBMQuintileLongShortStrategy(quintiles=CROSS_SECTIONAL_QUINTILES), stored(scores))
    assert target.weights() == {"S04": 0.25, "S07": 0.25, "S03": -0.25, "S06": -0.25}   # top 2 / bottom 2 of 10
    # ties broken by symbol, same bucket rule as portfolio_research.decile_portfolios.assign_deciles
    from src.application.services.portfolio_research.decile_portfolios import assign_deciles
    tied = {"B": 1.0, "A": 1.0, "C": 2.0, "E": 0.5, "D": 0.5, "F": 3.0, "G": 3.0}
    expected = dict(zip(*[assign_deciles(tied, 5)[c] for c in ("symbol", "decile")]))
    assert quantile_labels(tied, 5) == expected


def test_the_strategy_reads_the_existing_ranking_factor_and_does_not_score():
    strategy = LGBMQuintileLongShortStrategy()
    assert isinstance(strategy, TradingStrategy)
    (spec,) = strategy.calculate_dependencies
    assert spec.factor_type is QuintileRank and spec.per_entity and spec.source_in == ["calculated"]
    tree = ast.parse(inspect.getsource(strategy_module))                     # no model / scoring logic here
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | {
        n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"predict", "_provider", "provider", "fit", "lightgbm", "lgb"}
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and "lgbm_momentum" in (n.module or "")]
    with pytest.raises(ValueError):
        LGBMQuintileLongShortStrategy(quintiles="deciles")


def test_the_strategy_module_never_reaches_orders_or_infrastructure():
    tree = ast.parse(Path(inspect.getfile(strategy_module)).read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert all(m.startswith(("src.domain", "__future__", "datetime", "typing")) for m in imported), imported
    assert not [m for m in imported if any(k in m for k in (".order", ".transaction", "holding", "trade"))]


def test_the_universe_holds_no_score_rank_or_weight():
    from src.domain.entities.universe.universe import Universe
    from src.domain.entities.universe.universe_financial_asset import UniverseFinancialAsset
    universe = Universe(name="u")
    member = universe.add_financial_asset(1, start_date=date(2025, 1, 1))
    attributes = set(vars(universe)) | ({f.name for f in dataclasses.fields(member)} if dataclasses.is_dataclass(member)
                                        else set(vars(member)))
    assert isinstance(member, UniverseFinancialAsset)
    assert not [a for a in attributes if any(k in a.lower() for k in ("score", "rank", "weight", "quintile"))]


# -- end to end on the real repositories: Universe -> factor values -> TargetPortfolio, no order -------------------

@pytest.fixture
def world():
    from src.domain.entities.universe.universe import Universe
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from tests.misbuffet.sqlite_portfolio import SqlitePortfolio
    tickers = ("AAPL", "MSFT", "JPM", "XOM", "KO", "PG", "CVX", "BA", "WMT")
    p = SqlitePortfolio(cash=100_000.0, shares=tickers)
    f, s = p.factory, p.session
    shares = {t: f.company_share_local_repo.get_by_symbol(t) for t in tickers}
    universe = Universe(name="lgbm universe", version=1)
    for t in tickers[:-1]:                                     # WMT is stored but not a member
        universe.add_financial_asset(shares[t].id, start_date=date(2025, 1, 1))
    universe = f.universe_local_repo.add(universe)
    score = f.get_local_repository("CompanyShareLGBMCSQuintileRankMomentumFactor")._create_or_get(
        QuintileRank, primary_key="lgbm_cs_quintile_rank_momentum", group="momentum", subgroup="daily",
        frequency="1d", source="calculated")
    # stored model output (the model is never run here); BA has no value; WMT (not a member) is a Q5
    for ticker, value in {**QUINTILES, "WMT": 5.0}.items():
        s.add(FactorValueModel(factor_id=score.id, entity_id=shares[ticker].id, entity_type="CompanyShare",
                               date=AS_OF, value=repr(value)))
    s.commit()
    yield p, universe
    p.close()


def test_universe_to_target_portfolio_through_the_existing_resolution(world):
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    from src.application.services.data.entities.factor.trading_strategy_evaluation_service import (
        TradingStrategyEvaluationService,
    )
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    from src.infrastructure.models.finance.position import PositionModel
    from src.infrastructure.models.finance.order.order import OrderModel
    from src.infrastructure.models.finance.transaction.transaction import TransactionModel
    p, universe = world
    before = (p.session.query(OrderModel).count(), p.session.query(TransactionModel).count(),
              p.session.query(PositionModel).count())
    service = TradingStrategyEvaluationService(FactorValueResolutionService(factory=p.factory))
    target = service.target_portfolio(LGBMQuintileLongShortStrategy(), universe, AS_OF)
    assert isinstance(target, TargetPortfolio)
    assert target.weights() == {"AAPL": 0.25, "JPM": -0.25, "MSFT": 0.25, "XOM": -0.25}       # WMT: not a member
    assert target.construction == "bucket_long_short" and target.as_of == AS_OF
    # nothing executed or stored: no order, transaction or position, no value on the universe
    after = (p.session.query(OrderModel).count(), p.session.query(TransactionModel).count(),
             p.session.query(PositionModel).count())
    assert after == before
    assert p.session.query(FactorValueModel).filter(FactorValueModel.entity_type == "Universe").count() == 0
    # the universe is unchanged: the same members, nothing added to it
    reread = p.factory.universe_local_repo.get_by_id(universe.id)
    assert sorted(m.financial_asset_id for m in reread.financial_assets) == sorted(
        m.financial_asset_id for m in universe.financial_assets)
