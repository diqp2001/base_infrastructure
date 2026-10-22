"""
Checklist 9.1 / 9.3 / 9.6 — the repositories that write every order, in detail (SQLite, no IBKR).

``expectedFailure`` tests name a known bug in their docstring.
"""

import logging
import unittest
from datetime import date, datetime
from types import SimpleNamespace

from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)
logging.getLogger("src.infrastructure.repositories.local_repo.finance.order.order_repository").setLevel(logging.CRITICAL)


def name_of(value):
    return getattr(value, "name", str(value).split(".")[-1])


class OrderAndTransactionRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.p = SqlitePortfolio()
        self.p.trade("AAPL", 1, 100.0)                     # creates holding + account rows to reference
        self.holding_id = self.p.orders()[0].holding_id
        self.account_id = self.p.orders()[0].account_id
        self.orders = self.p.factory.order_local_repo
        self.txns = self.p.factory.transaction_local_repo

    def tearDown(self):
        self.p.close()

    def order(self, ext):
        return self.orders._create_or_get(external_order_id=ext, order_type="MARKET", side="BUY", quantity=3,
                                          created_at=T0, status="FILLED", holding_id=self.holding_id,
                                          account_id=self.account_id)

    def test_order_create_or_get_is_idempotent_and_creates_no_transaction(self):
        before = len(self.p.transactions())
        a, b = self.order("EXT-1"), self.order("EXT-1")
        self.assertEqual(a.id, b.id)
        self.assertEqual(self.orders.get_by_external_order_id("EXT-1").id, a.id)
        self.assertEqual(len(self.p.transactions()), before)

    def test_order_without_holding_is_refused_and_session_stays_usable(self):
        try:
            result = self.orders._create_or_get(external_order_id="EXT-X", order_type="MARKET", side="BUY",
                                                quantity=1, created_at=T0, status="FILLED",
                                                account_id=self.account_id)
        except Exception:
            result = None
        self.assertIsNone(result)
        self.assertIsNone(self.orders.get_by_external_order_id("EXT-X"))   # session not left broken
        self.assertIsNotNone(self.order("EXT-OK"))

    def test_transaction_keeps_the_dates_it_is_given_and_is_idempotent(self):
        order = self.order("EXT-2")
        kwargs = dict(order_id=order.id, date=T0, trade_date=T0.date(), value_date=T0.date(),
                      settlement_date=date(2026, 1, 6), status="EXECUTED", transaction_type="MARKET_ORDER",
                      account_id=self.account_id)
        a = self.txns._create_or_get("TXN-A", **kwargs)
        b = self.txns._create_or_get("TXN-A", **kwargs)
        self.assertEqual(a.id, b.id)
        row = next(t for t in self.p.transactions() if t.transaction_id == "TXN-A")
        self.assertEqual((row.date, row.trade_date, row.settlement_date, name_of(row.status)),
                         (T0, T0.date(), date(2026, 1, 6), "EXECUTED"))
        self.assertEqual([t.id for t in self.txns.get_by_order_id(order.id)], [a.id])

    def test_transaction_without_dates_is_refused(self):
        """No wall-clock default: a transaction without a date is not created."""
        order = self.order("EXT-3")
        result = self.txns._create_or_get("TXN-B", order_id=order.id, account_id=self.account_id)
        self.assertIsNone(result)


class PortfolioRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.p = SqlitePortfolio(cash=50_000.0)

    def tearDown(self):
        self.p.close()

    def test_registration_builds_the_cash_tree_once(self):
        self.assertEqual(self.p.cash(), 50_000.0)
        again = self.p.upm.register_portfolio_with_config({"name": "TEST", "initial_cash": 50_000.0})
        self.assertEqual(again.id, self.p.portfolio.id)
        self.assertEqual(self.p.cash(), 50_000.0)             # no second cash holding

    def test_related_entities_dispatch_to_the_holding_types(self):
        repo = self.p.factory.portfolio_local_repo
        types_before = {type(e).__name__ for e in repo.get_related_entities(self.p.portfolio.id)}
        self.assertEqual(types_before, {"CurrencyPortfolioPortfolioHolding"})
        self.p.trade("AAPL", 2, 100.0)
        types_after = {type(e).__name__ for e in repo.get_related_entities(self.p.portfolio.id)}
        self.assertEqual(types_after, {"CurrencyPortfolioPortfolioHolding", "CompanySharePortfolioPortfolioHolding"})

    def test_company_share_portfolio_holding_points_to_the_share(self):
        self.p.trade("AAPL", 2, 100.0)
        sub_id = self.p.container("AAPL")
        repo = self.p.factory.get_local_repository("CompanySharePortfolio")
        holdings = repo.get_related_entities(sub_id)
        self.assertEqual(len(holdings), 1)
        holding_repo = self.p.factory.get_local_repository("CompanySharePortfolioHolding")
        share = holding_repo.get_related_entities(holdings[0].id)
        share = share[0] if isinstance(share, list) else share
        self.assertEqual((type(share).__name__, share.symbol), ("CompanyShare", "AAPL"))

    def test_sub_portfolio_link_is_idempotent(self):
        self.assertEqual(self.p.container("AAPL"), self.p.container("MSFT"))
        self.assertEqual(self.p.container("AAPL"), self.p.container("AAPL"))


class CompanyShareRepositoryTest(unittest.TestCase):

    def setUp(self):
        self.p = SqlitePortfolio(shares=("AAPL",))
        self.repo = self.p.factory.company_share_local_repo

    def tearDown(self):
        self.p.close()

    def test_existing_symbol_is_returned(self):
        self.assertEqual(self.repo._create_or_get("AAPL").symbol, "AAPL")
        self.assertEqual(self.repo.get_by_symbol("AAPL").symbol, "AAPL")
        self.assertIsNone(self.repo.get_by_symbol("NOPE"))

    def test_new_symbol_can_be_created(self):
        share = self.repo._create_or_get("NVDA")
        self.assertEqual(share.symbol, "NVDA")
        self.assertEqual(self.repo._create_or_get("NVDA").id, share.id)
        self.assertEqual(self.p.factory.currency_local_repo.get_by_id(share.currency_id).symbol, "USD")


class IBKRRoutingTest(unittest.TestCase):

    def test_what_to_show_routing(self):
        from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import (
            IBKRFactorValueRepository,
        )
        route = IBKRFactorValueRepository._resolve_what_to_show_from_group
        self.assertEqual(route(None, "volatility", "implied"), "OPTION_IMPLIED_VOLATILITY")
        self.assertEqual(route(None, "volatility", "historical"), "HISTORICAL_VOLATILITY")
        self.assertEqual(route(None, "price", "ohlc"), "MIDPOINT")        # BI-026: price marks midpoint-first
        self.assertEqual(route(None, "price", "option"), "MIDPOINT")
        self.assertEqual(route(None, "momentum", ""), "TRADES")

    def test_repository_and_history_service_share_one_rule(self):
        """Both IBKR fetch paths decide whatToShow with what_to_show.resolve_what_to_show: an option close
        stored with subgroup 'ohlc' is MIDPOINT in both."""
        from src.application.services.misbuffet.data.market_data_history_service import MarketDataHistoryService
        option_close = type("CompanyShareOptionFactor", (), {"name": "close", "group": "price", "subgroup": "ohlc",
                                                            "source": "ibkr"})()
        share_close = type("CompanyShareFactor", (), {"name": "close", "group": "price", "subgroup": "ohlc",
                                                      "source": "ibkr"})()
        service = MarketDataHistoryService.__new__(MarketDataHistoryService)
        self.assertEqual(service._resolve_what_to_show_for_factor(option_close), "MIDPOINT")
        self.assertEqual(service._resolve_what_to_show_for_factor(share_close), "TRADES")   # BI-043: shares

    def test_contract_mapper_keeps_stock_and_option_identity(self):
        from ibapi.contract import Contract, ContractDetails
        from src.infrastructure.repositories.ibkr_repo.services.contract_instrument_mapper import (
            IBKRContractInstrumentMapper,
        )
        mapper = IBKRContractInstrumentMapper()
        for sec_type, local in (("STK", "SPY"), ("OPT", "SPY   281215C00775000")):
            contract = Contract()
            contract.conId, contract.symbol, contract.secType = 1234, "SPY", sec_type
            contract.exchange, contract.currency, contract.localSymbol = "SMART", "USD", local
            instrument = mapper.contract_to_instrument(contract, ContractDetails(),
                                                       asset=SimpleNamespace(id=1, symbol="SPY"),
                                                       timestamp=datetime(2026, 1, 5))
            with self.subTest(sec_type=sec_type):
                self.assertIsNotNone(instrument)
                self.assertEqual((instrument.security_type, instrument.local_symbol, instrument.contract_id),
                                 (sec_type, local, 1234))


if __name__ == "__main__":
    unittest.main()
