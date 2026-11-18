"""ETFShareOptionPortfolio (2026-11-16): options on an ETF share get their own sub-portfolio in the engine, as options
on a company share do (CompanyShareOptionPortfolio). In-memory SQLite, real repositories; no IBKR, no orders."""

import logging
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.misbuffet.algorithm.trade_manager import TradeManager
from src.application.services.misbuffet.algorithm.unified_portfolio_manager import UnifiedPortfolioManager
from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
from src.domain.entities.finance.holding.etf_share_option_portfolio_holding import ETFShareOptionPortfolioHolding
from src.domain.entities.finance.portfolio.etf_share_option_portfolio import ETFShareOptionPortfolio
from src.infrastructure.repositories.repository_factory import RepositoryFactory

SYMBOL = "DIA   210219C00300000"
NOW = datetime(2021, 1, 15, 16, 0)


@pytest.fixture()
def world():
    from src.infrastructure.models import ModelBase
    from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    f = RepositoryFactory(session)
    dia = f.get_local_repository("ETFShare")._create_or_get("DIA", asset_class="equity")
    option = f.get_local_repository("ETFShareOption")._create_or_get(
        symbol=SYMBOL, name="DIA 2021-02-19 C 300", option_type="call", underlying_asset_id=dia.id,
        strike_price=300.0, expiry="20210219", multiplier=100.0, start_date=date(2021, 1, 15))
    main = PortfolioModel(name="Dispersion_Test_Portfolio", portfolio_type="Portfolio", start_date=NOW)
    session.add(main)
    session.commit()
    yield SimpleNamespace(session=session, factory=f, option=option, main=main)
    session.close()


def make_upm(w):
    upm = UnifiedPortfolioManager.__new__(UnifiedPortfolioManager)
    upm.logger = logging.getLogger("test_etf_share_option_portfolio")
    upm.repository_factory = w.factory
    upm.portfolio_repo = SimpleNamespace(session=w.session)
    upm._current_portfolio_entity = SimpleNamespace(id=w.main.id, name=w.main.name)
    return upm


def test_the_family_is_registered(world):
    f = world.factory
    assert f.get_local_repository("ETFShareOptionPortfolio").entity_class is ETFShareOptionPortfolio
    assert f.get_local_repository("ETFShareOptionPortfolioHolding").entity_class is ETFShareOptionPortfolioHolding
    assert f.get_local_repository("ETFShareOptionPortfolioPortfolioHolding") is not None


def test_set_holdings_puts_an_etf_option_in_its_own_sub_portfolio(world):
    from src.infrastructure.models.finance.holding.etf_share_option_portfolio_holding import (
        ETFShareOptionPortfolioHoldingModel,
    )
    from src.infrastructure.models.finance.holding.etf_share_option_portfolio_portfolio_holding import (
        ETFShareOptionPortfolioPortfolioHoldingModel,
    )
    upm = make_upm(world)
    assert upm._probe_asset_class_name(SYMBOL) == "ETFShareOption"
    sub_id = upm._ensure_asset_container(SYMBOL, NOW, asset_class=ETFShareOption)
    assert sub_id is not None and sub_id != world.main.id
    assert upm._ensure_asset_container(SYMBOL, NOW, asset_class=ETFShareOption) == sub_id      # idempotent
    s = world.session
    link = s.query(ETFShareOptionPortfolioPortfolioHoldingModel).one()
    assert (link.container_id, link.asset_id) == (world.main.id, sub_id)
    holding = s.query(ETFShareOptionPortfolioHoldingModel).one()
    assert (holding.etf_share_option_id, holding.etf_share_option_portfolio_id) == (world.option.id, sub_id)
    sub = world.factory.get_local_repository("ETFShareOptionPortfolio").get_by_id(sub_id)
    assert isinstance(sub, ETFShareOptionPortfolio) and sub.name == f"{world.main.name}_ESO"

    # a short fill: the trade manager books it on the ETF option holding's position
    TradeManager(world.factory)._update_position(SYMBOL, -18, world.main.id)
    assert upm._qty_in_container(SYMBOL, world.main.id) == -18          # found through the ESO sub-portfolio
    assert upm._container_holding(SYMBOL, world.main.id) == sub_id
    # the position the resolution service reads follows the fill
    assert world.factory.get_local_repository("ETFShareOptionPortfolio").update_option_holding_quantity(SYMBOL, -18)
    # the main portfolio lists the ESO sub-portfolio among its sub-portfolio holdings
    related = world.factory.get_local_repository("Portfolio").get_related_entities(world.main.id)
    assert any(type(r).__name__ == "ETFShareOptionPortfolioPortfolioHolding" for r in related)
