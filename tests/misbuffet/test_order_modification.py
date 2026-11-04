"""P.03.04: a working LIMIT order is modified in place (IBKR: placeOrder with the same order id), through the
pre-trade gate judged on what the change adds, and recorded on the broker order. Nothing is sent anywhere."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
from src.application.services.misbuffet.brokers.pre_trade_gate import PreTradeGate
from src.application.services.misbuffet.common import Symbol
from src.application.services.misbuffet.common.enums import OrderDirection
from src.application.services.misbuffet.common.orders import LimitOrder, MarketOrder
from src.domain.entities.finance.order.broker_order import BrokerOrder
from src.domain.entities.finance.order.pre_trade_risk import AccountSnapshot, PriceSnapshot, RiskLimits
from src.domain.entities.finance.order.trading_control import ControlMode
from tests.misbuffet.test_pre_trade_risk import FakeBroker

NOW = datetime(2026, 11, 4, 15, 0)
FRESH = PriceSnapshot(100.0, NOW - timedelta(seconds=5))
ACCOUNT = AccountSnapshot(cash=100_000.0, positions={}, gross_exposure=0.0)
AT = datetime(2026, 11, 4, 15, 1)


def limit(qty, price=100.0, ticker="JPM"):
    return LimitOrder(symbol=Symbol.create_equity(ticker), quantity=qty, limit_price=price,
                      direction=OrderDirection.BUY if qty > 0 else OrderDirection.SELL)


# ---- domain ---------------------------------------------------------------------------------------------------------
def working(**kw):
    bo = BrokerOrder(order_id=5, broker="ibkr", symbol="JPM", side="BUY", requested_quantity=10, **kw)
    bo.mark_submitted(301, AT)
    return bo


def test_a_working_order_is_modified_never_below_its_fill():
    bo = working()
    bo.apply_status("PARTIALLY_FILLED", 4, 6, 100.0, AT)
    bo.modify(15, AT, "limit 101")
    assert (bo.requested_quantity, bo.remaining_quantity, bo.status) == (15.0, 11.0, "PARTIALLY_FILLED")
    assert "modified 10 -> 15 (limit 101)" in bo.message
    with pytest.raises(ValueError, match="must exceed the filled"):
        bo.modify(4, AT)


def test_closed_cancelling_or_unsent_orders_are_not_modified():
    unsent = BrokerOrder(order_id=6, broker="ibkr", symbol="JPM", side="BUY", requested_quantity=10)
    with pytest.raises(ValueError, match="not working"):
        unsent.modify(12, AT)
    cancelling = working()
    cancelling.request_cancel(AT)
    with pytest.raises(ValueError, match="being cancelled"):
        cancelling.modify(12, AT)
    filled = working()
    filled.apply_status("FILLED", 10, 0, 100.0, AT)
    with pytest.raises(ValueError, match="already FILLED"):
        filled.modify(12, AT)


# ---- gate -----------------------------------------------------------------------------------------------------------
class Controls:
    def __init__(self, mode):
        self.mode = mode

    def mode_for(self, account, strategy):
        return self.mode, ["operator"]


class RefusingThrottle:
    def refusal(self, symbol, quantity):
        return "duplicate: an order is working on this symbol"

    def record(self, symbol, quantity):
        pass


def gate(controls=None, limits=RiskLimits(max_order_quantity=20)):
    return PreTradeGate(limits, account_provider=lambda: ACCOUNT, price_provider=lambda s: FRESH,
                        clock=lambda: NOW, controls=controls, throttle=RefusingThrottle())


def test_the_gate_judges_a_modification_on_what_it_adds_and_never_throttles_it():
    g = gate()
    assert g.allows_modification(limit(25), previous_quantity=10)          # +15 within max_order_quantity 20
    assert not g.allows_modification(limit(35), previous_quantity=10)      # +25 over it
    assert "max_order_quantity" in g.rejections[-1][1][0]
    assert g.allows_modification(limit(5), previous_quantity=10)           # smaller: nothing to check
    assert g.throttle is not None                                          # restored after the check


def test_controls_apply_to_modifications():
    assert not gate(Controls(ControlMode.DISABLED)).allows_modification(limit(5), previous_quantity=10)
    reduce_only = gate(Controls(ControlMode.REDUCE_ONLY))
    assert reduce_only.allows_modification(limit(8), previous_quantity=10)            # a price / size cut
    assert not reduce_only.allows_modification(limit(12), previous_quantity=10)       # adds to a new position


def test_the_broker_sends_a_modification_only_through_the_gate():
    class Modifying(FakeBroker):
        def __init__(self):
            super().__init__()
            self.modified = []

        def _update_order_impl(self, order):
            self.modified.append(order.quantity)
            return True
    broker = Modifying()
    broker.attach_risk_gate(PreTradeGate(RiskLimits(max_order_quantity=20), account_provider=lambda: ACCOUNT,
                                         price_provider=lambda s: FRESH, clock=lambda: NOW))
    order = limit(10)
    assert broker.place_order(order) and broker.sent_quantities[order.id] == 10
    order.quantity = 25                                                     # changed in place: +15
    assert broker.update_order(order) and broker.modified == [25]
    order.quantity = 50                                                     # +25 from the 25 last sent
    assert broker.update_order(order) is False and broker.modified == [25]
    assert broker.sent_quantities[order.id] == 25


# ---- IBKR -------------------------------------------------------------------------------------------------------------
class FakeTWS:
    def __init__(self):
        self.modified = []

    def is_connected(self):
        return True

    def create_limit_order(self, action, quantity, price):
        return SimpleNamespace(action=action, totalQuantity=quantity, lmtPrice=price, orderRef="")

    def modify_order(self, order_id, contract, ib_order):
        self.modified.append((order_id, contract.symbol, ib_order.action, ib_order.totalQuantity, ib_order.lmtPrice,
                              ib_order.orderRef))
        return order_id


def ibkr_broker():
    broker = object.__new__(InteractiveBrokersBroker)
    broker.ib_connection, broker.pending_orders = FakeTWS(), {}
    broker.logger = SimpleNamespace(error=lambda *a, **k: None, info=lambda *a, **k: None)
    return broker


def test_ibkr_modifies_a_working_limit_order_with_the_same_order_id():
    broker = ibkr_broker()
    order = limit(10, price=100.0)
    order.tag = "MB42"
    broker.pending_orders[301] = order
    order.quantity, order.limit_price = 12, 100.5
    assert broker._update_order_impl(order)
    assert broker.ib_connection.modified == [(301, "JPM", "BUY", 12, 100.5, "MB42")]


def test_ibkr_does_not_modify_market_or_unknown_orders():
    broker = ibkr_broker()
    market = MarketOrder(symbol=Symbol.create_equity("JPM"), quantity=10, direction=OrderDirection.BUY)
    broker.pending_orders[302] = market
    assert broker._update_order_impl(market) is False
    assert broker._update_order_impl(limit(5)) is False                     # not placed: no TWS order id
    assert broker.ib_connection.modified == []


def test_the_tws_client_modifies_only_orders_it_placed():
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    client = object.__new__(IBTWSClient)
    client.placed_order_ids, client.sent = {301}, []
    client.is_connected = lambda: True
    client.get_managed_accounts = lambda: ["DUR314497"]
    client.placeOrder = lambda oid, contract, order: client.sent.append(oid)
    client.logger = SimpleNamespace(info=lambda *a, **k: None)
    ib_order = SimpleNamespace(action="BUY", totalQuantity=12, account="")
    contract = SimpleNamespace(symbol="JPM")
    with pytest.raises(ValueError, match="not placed by this client"):
        client.modify_order(999, contract, ib_order)
    assert client.modify_order(301, contract, ib_order) == 301 and client.sent == [301]
