"""
End-to-end: IBKR history -> stored factor values -> valuation -> set_holdings -> booked trade.

Layers crossed: IBKR adapter (InteractiveBrokersBroker + IBTWSClient callbacks, constructed bars)
-> IBKRFactorValueRepository (ingestion, persistence) -> FactorValueResolutionService
(mid price -> share value) -> UnifiedPortfolioManager.set_holdings (sizing on the full portfolio
value) -> TradeManager (order, transaction, position, cash) -> PortfolioService valuation.

Deterministic: the bars, prices and dates are fixed relative to "today" (the broker refuses end
dates older than 6 months). Nothing connects to IBKR, no order is sent.
"""

import logging
import threading
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
    CompanyShareValueFactor,
)
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio, slice_at

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)


def last_weekdays():
    """(previous session, decision session) — two consecutive weekdays a couple of weeks ago."""
    day = datetime.now(ZoneInfo("US/Eastern")).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    day -= timedelta(days=14)
    while day.weekday() != 1:                       # a Tuesday, so the previous session is Monday
        day -= timedelta(days=1)
    return day - timedelta(days=1), day


PREVIOUS, DECISION = last_weekdays()
DECISION_TIME = DECISION.replace(hour=16)


class ScriptedBroker:
    """InteractiveBrokersBroker whose TWS client answers reqHistoricalData with fixed daily bars."""

    def __init__(self, closes):
        self.broker = InteractiveBrokersBroker({"host": "127.0.0.1", "port": 1, "client_id": 1})
        client = IBTWSClient("127.0.0.1", 1, 1)
        client.is_connected = lambda: True
        self.broker.ib_connection = client
        self.requests = []

        def req(req_id, contract, end, duration, bar_size, what, rth, fmt, keep_up, options):
            self.requests.append(dict(symbol=contract.symbol, sec_type=contract.secType, what=what, bar_size=bar_size))

            def play():
                for day, close in closes.get(contract.symbol, []):
                    client.historicalData(req_id, SimpleNamespace(date=day.strftime("%Y%m%d"), open=close, high=close,
                                                                  low=close, close=close, volume=1_000, barCount=1))
                client.historicalDataEnd(req_id, "", "")
            threading.Thread(target=play, daemon=True).start()

        client.reqHistoricalData = req


@pytest.fixture
def world():
    p = SqlitePortfolio(cash=100_000.0, shares=("AAPL",))
    p.upm._algorithm.time = DECISION_TIME
    p.upm._algorithm.bar_size_setting = "1 day"
    p.upm._algorithm.config = {"backtest_start": "2020-01-01 00:00:00", "backtest_end": "2100-01-01 00:00:00"}
    feed = ScriptedBroker({"AAPL": [(PREVIOUS - timedelta(days=3), 140.0), (PREVIOUS, 150.0),
                                    (DECISION, 999.0)]})       # the decision-day bar is still open
    # as in the application: the factory owns the IBKR client and its IBKR repositories
    p.factory.ibkr_client = feed.broker
    p.factory._available_repository_families["ibkr"] = True
    p.factory.create_ibkr_repositories(feed.broker)
    ibkr = p.factory.factor_value_ibkr_repo or IBKRFactorValueRepository(ibkr_client=feed.broker, factory=p.factory)
    from src.infrastructure.models.factor.factor import CompanyShareFactorModel
    close = CompanyShareFactorModel(name="close", group="price", subgroup="ohlc", frequency="1d",
                                    data_type="numeric", source="ibkr", definition="close",
                                    factor_type="company_share_factor")
    p.session.add(close)
    p.session.commit()
    from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
    yield SimpleNamespace(p=p, feed=feed, ibkr=ibkr, close=FactorMapper.to_domain(close),
                          aapl=p.factory.company_share_local_repo.get_by_symbol("AAPL"))
    p.close()


def ingest(world):
    return world.ibkr._create_or_get("AAPL", factor=world.close, entity=world.aapl,
                                     date=DECISION_TIME.strftime("%Y-%m-%d %H:%M:%S"),
                                     bar_size_setting="1 day", duration_str="10 D")


def test_ingestion_requests_trades_daily_bars_and_returns_the_last_closed_bar(world):
    """Share price marks are requested TRADES first (source policy, BI-043: no US-equity quote permission); the feed
    answers, so no MIDPOINT request."""
    value = ingest(world)
    assert float(value.value) == 150.0                      # not the open decision-day bar (999)
    req, = world.feed.requests
    assert (req["symbol"], req["what"], req["bar_size"]) == ("AAPL", "TRADES", "1 day")
    stored = sorted((row[2], row[3]) for row in world.p.factor_values("close"))
    assert (PREVIOUS, 150.0) in stored


def test_ingested_bars_value_the_share_without_calling_ibkr_again(world):
    ingest(world)
    service = FactorValueResolutionService(factory=world.p.factory, logger=logging.getLogger("e2e"))
    repo = world.p.factory.get_local_repository("CompanyShareValueFactor")
    d = CompanyShareValueFactor()
    value_factor = repo._create_or_get(CompanyShareValueFactor, d.name, group=d.group, subgroup=d.subgroup,
                                       data_type=d.data_type, source=d.source, frequency="1d")
    value = service.resolve_factor_value(value_factor, world.aapl, DECISION_TIME)
    assert float(value.value) == 150.0
    assert len(world.feed.requests) == 1


def test_weight_target_is_sized_booked_and_reconciled_on_ingested_prices(world):
    ingest(world)
    result = world.p.upm.set_holdings({CompanyShare: {"name": "AAPL", "weight": 0.10}},
                                      slice_at(DECISION_TIME, AAPL=150.0))
    assert result == {"AAPL": True}
    assert world.p.qty("AAPL") == 66                       # int(100 000 * 10 % / 150)
    assert world.p.cash() == 100_000.0 - 66 * 150.0
    order, cash_order = world.p.orders()
    assert (order.quantity, order.average_fill_price) == (66, 150.0)
    value = world.p.upm.get_portfolio_value(backtest_date=DECISION_TIME)
    assert float(getattr(value, "value", value)) == pytest.approx(100_000.0)


def test_duplicate_bars_from_the_provider_are_stored_once(world):
    world.feed.__init__({"AAPL": [(PREVIOUS, 150.0), (PREVIOUS, 150.0), (PREVIOUS - timedelta(days=1), 149.0)]})
    world.p.factory.ibkr_client = world.feed.broker
    world.p.factory._ibkr_repositories = {}
    world.p.factory.create_ibkr_repositories(world.feed.broker)
    world.ibkr = world.p.factory.factor_value_ibkr_repo
    ingest(world)
    rows = [row for row in world.p.factor_values("close") if row[2] == PREVIOUS]
    assert len(rows) == 1


def test_ingesting_the_same_window_twice_adds_no_rows(world):
    ingest(world)
    before = len(world.p.factor_values("close"))
    world.ibkr._create_or_get("AAPL", factor=world.close, entity=world.aapl,
                              date=(DECISION_TIME + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
                              bar_size_setting="1 day", duration_str="10 D")
    assert len(world.p.factor_values("close")) == before
