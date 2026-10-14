"""
In-memory SQLite portfolio built through the real repositories (no IBKR, no orders).

    main Portfolio (initial cash through PortfolioRepository._create_or_get → CurrencyPortfolio tree)
      └─ CompanySharePortfolio sub-portfolio + holdings, created lazily by
         UnifiedPortfolioManager._ensure_asset_container exactly like set_holdings does.
"""

import logging
from collections import namedtuple
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.misbuffet.algorithm.unified_portfolio_manager import UnifiedPortfolioManager
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.models import ModelBase
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.models.finance.order.order import OrderModel
from src.infrastructure.models.finance.position import PositionModel
from src.infrastructure.models.finance.transaction.transaction import TransactionModel
from src.infrastructure.repositories.repository_factory import RepositoryFactory

T0 = datetime(2026, 1, 5, 16, 0)
Sym = namedtuple("Sym", "value")


def slice_at(time=T0, **closes):
    """Minimal Slice: data.time + data.bars {Symbol-like: bar with .close}."""
    return SimpleNamespace(time=time, bars={Sym(t): SimpleNamespace(close=px) for t, px in closes.items()})


class SqlitePortfolio:

    def __init__(self, cash=100_000.0, shares=("AAPL", "MSFT"), engine=None, live=False):
        # Never let a lazily created factory / market-data service open a real IBKR connection
        # (RepositoryFactory.create_ibkr_client connects to the configured TWS / Gateway).
        from ibapi.client import EClient
        self._no_ibkr = patch.object(RepositoryFactory, "create_ibkr_client", return_value=None)
        self._no_socket = patch.object(EClient, "connect", side_effect=ConnectionRefusedError("tests never connect to IBKR"))
        self._no_ibkr.start()
        self._no_socket.start()
        # any prepared engine (tests.persistence.Backend), or a fresh in-memory SQLite database
        self._owns_engine = engine is None
        self.engine = engine if engine is not None else create_engine("sqlite:///:memory:")
        if self._owns_engine:
            ModelBase.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.logger = logging.getLogger("sqlite_portfolio")
        self.upm = UnifiedPortfolioManager(SimpleNamespace(repository_factory=self.factory), None, logger=self.logger)
        self._n = 0
        self.market_order = Mock(side_effect=self._ticket)
        # live=True: registration resumes an existing book (a restart / second process), backtest resets it
        self.upm._algorithm = SimpleNamespace(market_order=self.market_order, live_mode=live, time=T0,
                                              config={"backtest_start": "2026-01-01 00:00:00",
                                                      "backtest_end": "2027-01-01 00:00:00"})
        self.portfolio = self.upm.register_portfolio_with_config({"name": "TEST", "initial_cash": cash})
        assert self.portfolio is not None, "portfolio registration failed"
        for symbol in shares:
            if self._owns_engine:
                # foreign keys are not enforced on this private SQLite database: placeholder ids
                self.factory.company_share_local_repo.add(
                    CompanyShare(id=None, symbol=symbol, exchange_id=1, company_id=1, currency_id=1,
                                 start_date=date(2020, 1, 1)))
            else:
                # shared backends enforce foreign keys: exchange / company / currency are created
                # by the repository, on top of real reference rows (see seed_reference_data)
                self.seed_reference_data()
                assert self.factory.company_share_local_repo._create_or_get(symbol) is not None, symbol
        self.tm = self.upm._trade_manager

    def seed_reference_data(self):
        """Continent / country / sector / industry id 1 — CompanyShareRepository._create_or_get links new
        companies and exchanges to these ids (see test_company_share_needs_no_placeholder_references)."""
        from src.infrastructure.models.continent import ContinentModel
        from src.infrastructure.models.country import CountryModel
        from src.infrastructure.models.industry import IndustryModel
        from src.infrastructure.models.sector import SectorModel
        rows = [(ContinentModel, dict(name="North America")), (SectorModel, dict(name="Technology")),
                (CountryModel, dict(name="United States", iso_code="USA", continent_id=1)),
                (IndustryModel, dict(name="Technology", sector_id=1))]
        for model, fields in rows:                       # parents first; keep rows that already exist
            if self.session.get(model, 1) is None:
                self.session.add(model(id=1, **fields))
                self.session.flush()
        self.session.commit()

    def _ticket(self, ticker, qty, tag=""):
        self._n += 1
        return SimpleNamespace(order_id=f"QC{self._n}")

    def seed_close(self, ticker, when, price, frequency="1d"):
        """Store a raw daily close for `ticker` the way the IBKR import does (bar stamped at its start).
        A bar is only usable once closed, so value a date with the previous session's bar."""
        from src.infrastructure.models.factor.factor import CompanyShareFactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        factor = self.session.query(CompanyShareFactorModel).filter_by(name="close", frequency=frequency).first()
        if factor is None:
            factor = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency=frequency,
                                             data_type="numeric", source="ibkr", definition="close",
                                             factor_type="company_share_factor")
            self.session.add(factor)
            self.session.commit()
        share = self.factory.company_share_local_repo.get_by_symbol(ticker)
        self.session.add(FactorValueModel(factor_id=factor.id, entity_id=share.id, entity_type="CompanyShare",
                                          date=when, value=repr(float(price))))
        self.session.commit()

    def factor_values(self, factor_name):
        """[(entity_type, entity_id, date, float value)] stored for a factor name."""
        from src.infrastructure.models.factor.factor import FactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        rows = (self.session.query(FactorValueModel)
                .join(FactorModel, FactorModel.id == FactorValueModel.factor_id)
                .filter(FactorModel.name == factor_name).order_by(FactorValueModel.id).all())
        return [(r.entity_type, r.entity_id, r.date, float(r.value)) for r in rows]

    def container(self, ticker, when=T0):
        return self.upm._ensure_asset_container(ticker, when, asset_class=CompanyShare)

    def trade(self, ticker, qty, price, when=T0, submit=None):
        return self.tm.execute_trade(ticker=ticker, order_qty=qty, price=price,
                                     portfolio_id=self.container(ticker, when), current_time=when,
                                     submit_order_fn=submit or self.market_order,
                                     main_portfolio_id=self.portfolio.id)

    # ---- reads -------------------------------------------------------------------------------
    def qty(self, ticker):
        return self.upm._get_current_position_qty(ticker)

    def cash(self):
        return float(self.upm._get_cash_balance())

    def orders(self):
        return self.session.query(OrderModel).order_by(OrderModel.id).all()

    def transactions(self):
        return self.session.query(TransactionModel).order_by(TransactionModel.id).all()

    def holdings(self):
        return self.session.query(HoldingModel).all()

    def positions(self):
        return self.session.query(PositionModel).all()

    def close(self):
        self.session.close()
        if self._owns_engine:
            self.engine.dispose()
        self._no_ibkr.stop()
        self._no_socket.stop()
