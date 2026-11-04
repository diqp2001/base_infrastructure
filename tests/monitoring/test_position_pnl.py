"""P.08.09: per-position average cost, realized and unrealized P&L from the stored fills (domain), and the monitoring
Trading page's positions table read from booked executions (in-memory SQLite)."""

import datetime as dt
import unittest

from sqlalchemy import insert

from src.domain.entities.finance.position_pnl import Fill, position_pnl, positions_pnl, signed_quantity
from src.infrastructure.models import ModelBase
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import MonitoringReadRepository
from tests.monitoring.helpers import _defaults_for, sqlite_engine


class PositionPnLTest(unittest.TestCase):

    def test_buy_partial_sell_add_flatten(self):
        fills = [Fill("JPM", 10, 100.0, 1.0),           # long 10 @ 100
                 Fill("JPM", -4, 110.0, 1.0),           # realize (110 - 100) x 4 = 40; 6 left @ 100
                 Fill("JPM", 6, 106.0, 1.0),            # add: 12 @ (6 x 100 + 6 x 106) / 12 = 103
                 Fill("JPM", -12, 101.0, 1.0)]          # realize (101 - 103) x 12 = -24 -> flat
        p = position_pnl("JPM", fills)
        self.assertEqual((p.quantity, p.average_cost), (0.0, None))
        self.assertAlmostEqual(p.realized, 16.0)
        self.assertEqual((p.commission, p.unrealized, p.net, p.fills), (4.0, 0.0, 12.0, 4))

    def test_open_position_unrealized_and_no_price(self):
        fills = [Fill("JPM", 10, 100.0), Fill("JPM", -4, 110.0)]
        p = position_pnl("JPM", fills, last_price=105.0)
        self.assertEqual((p.quantity, p.average_cost, p.realized, p.unrealized), (6.0, 100.0, 40.0, 30.0))
        self.assertIsNone(position_pnl("JPM", fills).unrealized)               # no price: unknown, not 0
        self.assertIsNone(position_pnl("JPM", fills).net)

    def test_short_and_flip_through_zero(self):
        p = position_pnl("BAC", [Fill("BAC", -5, 50.0), Fill("BAC", 8, 48.0)], last_price=49.0)
        # short 5 @ 50 bought back @ 48: +10 realized; the other 3 open long @ 48
        self.assertEqual((p.quantity, p.average_cost, p.realized, p.unrealized), (3.0, 48.0, 10.0, 3.0))

    def test_option_multiplier_and_sides(self):
        p = position_pnl("OPT", [Fill("OPT", 2, 1.5), Fill("OPT", -2, 2.0)], multiplier=100)
        self.assertAlmostEqual(p.realized, 100.0)
        self.assertEqual((signed_quantity("BUY", 3), signed_quantity("SELL", 3), signed_quantity("SLD", 3)),
                         (3.0, -3.0, -3.0))
        with self.assertRaises(ValueError):
            signed_quantity("HOLD", 1)
        self.assertEqual([p.symbol for p in positions_pnl([Fill("B", 1, 1.0), Fill("A", 1, 1.0)])], ["A", "B"])


class TradingPagePositionsTest(unittest.TestCase):

    def test_positions_equal_the_sum_over_booked_fills(self):
        engine = sqlite_engine()                                                # SPY = financial asset 1
        ex = ModelBase.metadata.tables["broker_executions"]
        ModelBase.metadata.create_all(engine, tables=[ex, ModelBase.metadata.tables["broker_orders"]])
        t0 = dt.datetime(2026, 11, 3, 15, 0)
        with engine.begin() as conn:
            conn.execute(insert(FactorModel.__table__).values(**_defaults_for(FactorModel.__table__, {
                "id": 3, "name": "close", "group": "price", "subgroup": "TRADES", "frequency": "10m",
                "source": "ibkr", "factor_type": "factor", "data_type": "numeric", "definition": "close"})))
            for i, (minutes, value) in enumerate([(0, "99.0"), (10, "104.5")]):
                conn.execute(insert(FactorValueModel.__table__).values(**_defaults_for(FactorValueModel.__table__, {
                    "id": 10 + i, "factor_id": 3, "entity_id": 1, "entity_type": "CompanyShare",
                    "date": t0 + dt.timedelta(minutes=minutes), "value": value})))
            for i, (side, qty, price, booked) in enumerate([("BUY", 10, 100.0, True), ("SELL", 4, 110.0, True),
                                                            ("BUY", 50, 1.0, False)]):      # unbooked: ignored
                conn.execute(insert(ex).values(**_defaults_for(ex, {
                    "id": i + 1, "broker": "ibkr", "exec_id": f"e{i}", "symbol": "SPY", "side": side,
                    "quantity": qty, "price": price, "executed_at": t0 + dt.timedelta(minutes=i),
                    "commission": 1.0, "booked": booked, "commission_booked": booked})))
        positions = MonitoringReadRepository(engine).positions_pnl()
        self.assertEqual(positions, [{
            "symbol": "SPY", "quantity": 6.0, "average_cost": 100.0, "last_price": 104.5, "realized_pnl": 40.0,
            "unrealized_pnl": 27.0, "commission": 2.0, "net_pnl": 65.0, "fills": 2}])


if __name__ == "__main__":
    unittest.main()
