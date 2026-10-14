"""
Checklist section 2 — TradeManager bookkeeping on a real (in-memory SQLite) portfolio tree.

Orders are never sent anywhere: submit_order_fn is a Mock returning a ticket.
``expectedFailure`` tests name a known bug in their docstring.
"""

import logging
import unittest
from datetime import timedelta
from unittest.mock import Mock

from src.infrastructure.models.finance.holding.holding import HoldingModel
from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)


def enum_name(value):
    return getattr(value, "name", str(value).split(".")[-1])


class TradeManagerTest(unittest.TestCase):

    def setUp(self):
        self.p = SqlitePortfolio(cash=100_000.0)

    def tearDown(self):
        self.p.close()

    def test_failed_submission_writes_nothing(self):
        before = (self.p.qty("AAPL"), self.p.cash(), len(self.p.orders()), len(self.p.transactions()))
        self.assertFalse(self.p.trade("AAPL", 10, 150.0, submit=Mock(return_value=None)))
        self.assertEqual((self.p.qty("AAPL"), self.p.cash(), len(self.p.orders()), len(self.p.transactions())), before)

    def test_buy_records_order_fill_position_and_cash(self):
        self.assertTrue(self.p.trade("AAPL", 10, 150.0))
        self.assertEqual(self.p.qty("AAPL"), 10)
        self.assertEqual(self.p.cash(), 100_000.0 - 1_500.0)
        asset_order, cash_order = self.p.orders()
        self.assertEqual((enum_name(asset_order.side), asset_order.quantity, enum_name(asset_order.status)),
                         ("BUY", 10, "FILLED"))
        self.assertEqual((enum_name(cash_order.side), cash_order.quantity), ("SELL", 1_500))
        self.assertIsNotNone(asset_order.holding_id)
        self.assertIsNotNone(asset_order.account_id)

    def test_one_transaction_per_order_at_the_simulation_date(self):
        self.p.trade("AAPL", 10, 150.0)
        self.p.trade("MSFT", 5, 400.0, when=T0 + timedelta(days=1))
        txns = self.p.transactions()
        self.assertEqual(sorted(t.order_id for t in txns), sorted(o.id for o in self.p.orders()))
        self.assertEqual(len({t.order_id for t in txns}), len(txns))          # never two per order
        self.assertEqual({t.date for t in txns}, {T0, T0 + timedelta(days=1)})
        self.assertTrue(all(t.trade_date == t.date.date() for t in txns))
        self.assertEqual({enum_name(t.status) for t in txns}, {"EXECUTED"})
        self.assertEqual({o.created_at for o in self.p.orders()}, {T0, T0 + timedelta(days=1)})

    def test_position_created_before_holding_and_reused(self):
        self.p.trade("AAPL", 10, 150.0)
        self.p.trade("AAPL", 5, 150.0)
        aapl = self.p.factory.company_share_local_repo.get_by_symbol("AAPL")
        holdings = self.p.session.query(HoldingModel).filter(HoldingModel.asset_id == aapl.id).all()
        self.assertEqual(len(holdings), 1)
        self.assertIsNotNone(holdings[0].position_id)
        self.assertEqual(len({o.holding_id for o in self.p.orders()[::2]}), 1)   # asset orders share it

    def test_account_is_created_once_and_reused(self):
        from src.infrastructure.models.finance.account import AccountModel
        self.p.trade("AAPL", 1, 150.0)
        self.p.trade("MSFT", 1, 400.0)
        self.assertEqual(self.p.session.query(AccountModel).count(), 1)
        self.assertEqual(len({o.account_id for o in self.p.orders()}), 1)

    def test_position_through_buy_partial_sell_close_and_short(self):
        steps = [(10, 10), (-4, 6), (-6, 0), (-3, -3), (3, 0)]
        for delta, expected in steps:
            self.p.trade("AAPL", delta, 100.0)
            self.assertEqual(self.p.qty("AAPL"), expected, f"after {delta:+d}")
        position_types = {enum_name(p.position_type) for p in self.p.positions()}
        self.assertTrue(position_types <= {"LONG", "SHORT"})

    def test_short_position_is_typed_short(self):
        self.p.trade("AAPL", -3, 100.0)
        aapl = self.p.factory.company_share_local_repo.get_by_symbol("AAPL")
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )
        holding = self.p.session.query(CompanySharePortfolioHoldingModel).filter_by(asset_id=aapl.id).one()
        position = next(p for p in self.p.positions() if p.id == holding.position_id)
        self.assertEqual((position.quantity, enum_name(position.position_type)), (-3, "SHORT"))

    def test_cash_moves_by_price_times_quantity_with_the_right_sign(self):
        self.p.trade("AAPL", 10, 150.0)
        self.assertEqual(self.p.cash(), 98_500.0)
        self.p.trade("AAPL", -4, 200.0)
        self.assertEqual(self.p.cash(), 99_300.0)
        self.p.trade("AAPL", -10, 100.0)          # going short raises cash
        self.assertEqual(self.p.cash(), 100_300.0)

    def test_tree_adds_up_after_a_sequence(self):
        trades = [("AAPL", 10, 150.0), ("MSFT", 5, 400.0), ("AAPL", -4, 150.0), ("MSFT", -5, 400.0)]
        for ticker, qty, price in trades:
            self.p.trade(ticker, qty, price)
        held_value = self.p.qty("AAPL") * 150.0 + self.p.qty("MSFT") * 400.0
        self.assertEqual(self.p.cash() + held_value, 100_000.0)
        self.assertEqual(self.p.upm._get_all_held_tickers(), {"AAPL"})

    @unittest.expectedFailure
    def test_cash_keeps_cents(self):
        """BUG (needs a schema migration): positions.quantity is an INTEGER column, so the cash position
        can only hold whole dollars — _update_cash_for_trade books int(round(qty * price)) and cents
        are lost on every trade. Fix: positions.quantity -> DECIMAL(18, 4), then book the exact amount."""
        self.p.trade("AAPL", 10, 150.255)
        self.assertAlmostEqual(self.p.cash(), 100_000.0 - 1_502.55, places=2)

    def test_fill_price_is_recorded(self):
        self.p.trade("AAPL", 10, 150.0)
        asset_order = self.p.orders()[0]
        self.assertEqual((asset_order.average_fill_price, asset_order.filled_quantity), (150.0, 10))

    def test_unregistered_order_moves_no_cash(self):
        """A ticker with no financial asset cannot be booked: nothing is sent, no cash moves."""
        cash = self.p.cash()
        ok = self.p.tm.execute_trade(ticker="NOPE", order_qty=10, price=100.0, portfolio_id=self.p.portfolio.id,
                                     current_time=T0, submit_order_fn=self.p.market_order,
                                     main_portfolio_id=self.p.portfolio.id)
        self.assertEqual(self.p.cash(), cash)
        self.assertFalse(ok)
        self.p.market_order.assert_not_called()


if __name__ == "__main__":
    unittest.main()
