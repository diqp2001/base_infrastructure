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
from unittest.mock import Mock

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

    def __init__(self, cash=100_000.0, shares=("AAPL", "MSFT")):
        self.engine = create_engine("sqlite:///:memory:")
        ModelBase.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.factory = RepositoryFactory(self.session)
        self.logger = logging.getLogger("sqlite_portfolio")
        self.upm = UnifiedPortfolioManager(SimpleNamespace(repository_factory=self.factory), None, logger=self.logger)
        self.portfolio = self.upm.register_portfolio_with_config({"name": "TEST", "initial_cash": cash})
        assert self.portfolio is not None, "portfolio registration failed"
        for symbol in shares:
            self.factory.company_share_local_repo.add(
                CompanyShare(id=None, symbol=symbol, exchange_id=1, company_id=1, currency_id=1,
                             start_date=date(2020, 1, 1)))
        self._n = 0
        self.market_order = Mock(side_effect=self._ticket)
        self.upm._algorithm = SimpleNamespace(market_order=self.market_order, live_mode=False, time=T0,
                                              config={"backtest_start": "2026-01-01 00:00:00",
                                                      "backtest_end": "2027-01-01 00:00:00"})
        self.tm = self.upm._trade_manager

    def _ticket(self, ticker, qty, tag=""):
        self._n += 1
        return SimpleNamespace(order_id=f"QC{self._n}")

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
        self.engine.dispose()
