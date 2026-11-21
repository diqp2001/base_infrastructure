"""
P2 — TradingStrategy is a first-class Factor: it declares factor dependencies, the existing resolution service
resolves its dependency graph on its parent entity (a Universe: its members in force), it is persisted through the
factor infrastructure, and the domain class depends on neither SQLAlchemy nor broker / execution code.
"""

import ast
import inspect
from datetime import date, datetime
from pathlib import Path

import pytest

from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_lgbm_cs_quintile_rank_momentum_factor import (  # noqa: E501
    CompanyShareLGBMCSQuintileRankMomentumFactor as QuintileRank,
)
from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.trading_strategy import trading_strategy as trading_strategy_module
from src.domain.entities.factor.trading_strategy.trading_strategy import StrategySignals, TradingStrategy
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

AS_OF = datetime(2026, 1, 5, 16, 0)


class ScoreSignStrategy(TradingStrategy):
    """Test strategy on the LGBM cross-sectional ranking factor: long the constituents ranked above the
    cross-sectional mean, short those below (the real P5 strategy is the quintile one)."""

    @property
    def calculate_dependencies(self) -> list:
        return [DependencySpec(factor_type=QuintileRank, group="momentum", source_in=["calculated"],
                               per_entity=True, key="score")]

    def evaluate(self, dependencies, as_of=None) -> StrategySignals:
        scores = {symbol: values[-1] for symbol, values in (dependencies.get("score") or {}).items() if values}
        if not scores:
            return StrategySignals(as_of=as_of, values={}, asset_type="CompanyShare", note="no score")
        mean = sum(scores.values()) / len(scores)
        return StrategySignals(as_of=as_of, asset_type="CompanyShare",
                               values={s: (1.0 if v > mean else -1.0 if v < mean else 0.0) for s, v in scores.items()})


# -- the domain class -----------------------------------------------------------------------------------------------

def test_a_trading_strategy_is_a_factor_of_the_strategy_group():
    strategy = TradingStrategy(name="base")
    assert isinstance(strategy, Factor)
    assert (strategy.group, strategy.subgroup, strategy.source) == ("strategy", "trading_strategy", "calculated")
    assert strategy.calculate({"anything": [1.0]}) is None          # no scalar value: nothing stored
    with pytest.raises(NotImplementedError):
        strategy.evaluate({})


def test_a_trading_strategy_declares_factor_dependencies():
    deps = ScoreSignStrategy(name="score_sign").calculate_dependencies
    assert len(deps) == 1 and deps[0].factor_type is QuintileRank and deps[0].per_entity
    assert TradingStrategy(name="base").calculate_dependencies == []


def test_strategy_signals_are_finite_numbers():
    signals = StrategySignals(as_of=AS_OF, values={"AAPL": 1.0, "MSFT": -0.5})
    assert len(signals) == 2 and signals.assets() == ["AAPL", "MSFT"]
    with pytest.raises(ValueError):
        StrategySignals(as_of=AS_OF, values={"AAPL": float("nan")})


def _imports(module) -> set:
    tree = ast.parse(Path(inspect.getfile(module)).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_the_domain_class_has_no_sqlalchemy_dependency():
    assert not [m for m in _imports(trading_strategy_module) if m.startswith("sqlalchemy")
                or m.startswith("src.infrastructure")]


def test_the_domain_class_has_no_broker_or_execution_dependency():
    forbidden = ("src.application", "src.infrastructure", "ibapi", "ib_insync")
    imports = _imports(trading_strategy_module)
    assert not [m for m in imports if m.startswith(forbidden)], imports
    assert all(m.startswith(("src.domain", "__future__", "dataclasses", "datetime", "typing", "math", "abc"))
               for m in imports), imports


# -- persistence and resolution -------------------------------------------------------------------------------------

@pytest.fixture
def world():
    p = SqlitePortfolio(cash=100_000.0, shares=("AAPL", "MSFT", "JPM", "XOM"))
    f, s = p.factory, p.session
    shares = {t: f.company_share_local_repo.get_by_symbol(t) for t in ("AAPL", "MSFT", "JPM", "XOM")}
    # a universe of AAPL, MSFT, JPM; XOM is a stored share that is NOT a member; JPM left the universe before AS_OF
    from src.domain.entities.universe.universe import Universe
    universe = Universe(name="test universe", version=1)
    universe.add_financial_asset(shares["AAPL"].id, start_date=date(2025, 1, 1))
    universe.add_financial_asset(shares["MSFT"].id, start_date=date(2025, 1, 1))
    universe.add_financial_asset(shares["JPM"].id, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
    universe = f.universe_local_repo.add(universe)
    # the ranking factor (LGBM cross-sectional quintile, 1-5) and its stored values per share at AS_OF: the model is
    # never run here, the stored values are reused as they are
    score = f.get_local_repository("CompanyShareLGBMCSQuintileRankMomentumFactor")._create_or_get(
        QuintileRank, primary_key="lgbm_cs_quintile_rank_momentum", group="momentum", subgroup="daily",
        frequency="1d", source="calculated")
    assert score is not None
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    for ticker, value in (("AAPL", 5.0), ("MSFT", 1.0), ("JPM", 3.0), ("XOM", 4.0)):
        s.add(FactorValueModel(factor_id=score.id, entity_id=shares[ticker].id, entity_type="CompanyShare",
                               date=AS_OF, value=repr(value)))
    s.commit()
    yield p, universe, shares
    p.close()


def test_the_universe_gives_its_members_in_force_as_related_entities(world):
    p, universe, shares = world
    repo = p.factory.universe_local_repo
    assert [e.symbol for e in repo.get_related_entities(universe.id, AS_OF)] == ["AAPL", "MSFT"]   # JPM left
    assert sorted(e.symbol for e in repo.get_related_entities(universe.id)) == ["AAPL", "JPM", "MSFT"]


def test_the_existing_resolution_service_resolves_a_trading_strategy_graph(world):
    from src.application.services.data.entities.factor.factor_value_resolution_service import (
        FactorValueResolutionService,
    )
    from src.application.services.data.entities.factor.trading_strategy_evaluation_service import (
        TradingStrategyEvaluationService,
    )
    p, universe, _ = world
    resolution = FactorValueResolutionService(factory=p.factory)
    strategy = ScoreSignStrategy(name="score_sign")
    inputs = resolution.resolve_dependencies(strategy, universe, AS_OF)
    assert inputs["score"] == {"AAPL": [5.0], "MSFT": [1.0]}            # members in force only, per constituent
    signals = TradingStrategyEvaluationService(resolution).evaluate(strategy, universe, AS_OF)
    assert dict(signals.values) == {"AAPL": 1.0, "MSFT": -1.0} and signals.as_of == AS_OF
    # nothing is stored for the strategy itself
    from src.infrastructure.models.factor.factor_value import FactorValueModel
    assert p.session.query(FactorValueModel).filter(FactorValueModel.entity_type == "Universe").count() == 0


def test_a_trading_strategy_is_persisted_through_the_factor_infrastructure(world):
    from src.infrastructure.repositories.mappers.factor.factor_mapper import DISCRIMINATOR_CLASS_MAP, FactorMapper
    p, _, _ = world
    repo = p.factory.trading_strategy_local_repo
    first = repo._create_or_get(TradingStrategy, primary_key="lgbm_quintile_long_short")
    again = repo._create_or_get(TradingStrategy, primary_key="lgbm_quintile_long_short")
    assert isinstance(first, TradingStrategy) and first.id == again.id and first.group == "strategy"
    orm = p.session.query(repo.model_class).filter(repo.model_class.id == first.id).one()
    assert orm.factor_type == "trading_strategy" and type(FactorMapper.to_domain(orm)) is TradingStrategy
    assert DISCRIMINATOR_CLASS_MAP["trading_strategy"] is TradingStrategy
    assert FactorMapper.to_orm(TradingStrategy(name="x")).factor_type == "trading_strategy"
