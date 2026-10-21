"""BI-022: shared pre-trade risk gate. Pure rules, then the gate on a fake broker. Nothing is sent anywhere."""

import logging
from datetime import datetime, timedelta

import pytest

from src.application.services.misbuffet.brokers.base_broker import BaseBroker
from src.application.services.misbuffet.brokers.pre_trade_gate import PreTradeGate
from src.application.services.misbuffet.common import Symbol
from src.application.services.misbuffet.common.enums import OrderDirection
from src.application.services.misbuffet.common.orders import MarketOrder
from src.domain.entities.finance.order.pre_trade_risk import (
    AccountSnapshot, OrderIntent, PriceSnapshot, RiskLimits, check_order,
)

NOW = datetime(2026, 10, 21, 15, 0)
FRESH = PriceSnapshot(100.0, NOW - timedelta(seconds=5))
ACCOUNT = AccountSnapshot(cash=10_000.0, positions={"SPY": 20.0}, gross_exposure=2_000.0)


def failed(results):
    return {r.rule for r in results if not r.passed}


def check(qty, limits, price=FRESH, account=ACCOUNT, multiplier=1.0):
    return failed(check_order(OrderIntent("SPY", qty, multiplier), price, account, limits, NOW))


# ---- rules -----------------------------------------------------------------------------------

def test_an_order_within_every_limit_passes():
    limits = RiskLimits(max_order_quantity=50, max_order_notional=5_000, max_position_quantity=100,
                        max_gross_exposure=10_000)
    assert check(30, limits) == set()


@pytest.mark.parametrize("qty, limits, rule", [
    (60, RiskLimits(max_order_quantity=50), "max_order_quantity"),
    (60, RiskLimits(max_order_notional=5_000), "max_order_notional"),
    (90, RiskLimits(max_position_quantity=100), "max_position_quantity"),        # 20 held + 90
    (90, RiskLimits(max_gross_exposure=10_000), "max_gross_exposure"),           # 11 000 after
    (150, RiskLimits(), "cash_available"),                                       # 15 000 > 10 000 cash
    (0, RiskLimits(), "quantity_nonzero"),
])
def test_each_limit_rejects(qty, limits, rule):
    assert rule in check(qty, limits)


def test_a_sell_needs_no_cash_and_reduces_the_position():
    assert check(-20, RiskLimits(max_position_quantity=0)) == set()              # closes the position exactly
    assert check(-150, RiskLimits()) == set()                                    # short allowed, no cash needed


def test_stale_or_missing_prices_refuse_the_order():
    assert "fresh_price" in check(1, RiskLimits(), price=PriceSnapshot(100.0, NOW - timedelta(minutes=5)))
    assert "fresh_price" in check(1, RiskLimits(), price=PriceSnapshot(100.0, None))
    assert "price_available" in check(1, RiskLimits(), price=None)
    assert "price_available" in check(1, RiskLimits(), price=PriceSnapshot(0.0, NOW))


def test_the_contract_multiplier_counts_in_the_notional():
    assert "max_order_notional" in check(1, RiskLimits(max_order_notional=5_000), multiplier=100)   # 10 000


# ---- gate on the broker ----------------------------------------------------------------------

class FakeBroker(BaseBroker):
    def __init__(self):
        super().__init__({})
        self.sent = []

    def get_required_config_fields(self):
        return []

    def is_connected(self):
        return True

    def _connect_impl(self):
        return True

    def _disconnect_impl(self):
        pass

    def _place_order_impl(self, order):
        self.sent.append(order)
        return True

    def _update_order_impl(self, order):
        return False

    def _cancel_order_impl(self, order):
        return False

    def _update_account_info(self):
        pass


def market(qty, ticker="SPY"):
    return MarketOrder(symbol=Symbol.create_equity(ticker), quantity=qty,
                       direction=OrderDirection.BUY if qty > 0 else OrderDirection.SELL)


def gate(limits=RiskLimits(max_order_quantity=50), price=FRESH, account=lambda: ACCOUNT):
    return PreTradeGate(limits, account_provider=account, price_provider=lambda s: price, clock=lambda: NOW)


def test_without_a_gate_nothing_changes():
    broker = FakeBroker()
    assert broker.place_order(market(500)) and len(broker.sent) == 1


def test_a_refused_order_is_never_sent_and_is_logged(caplog):
    broker = FakeBroker()
    broker.attach_risk_gate(gate())
    with caplog.at_level(logging.WARNING):
        assert broker.place_order(market(60)) is False
    assert broker.sent == [] and "max_order_quantity" in caplog.text
    assert broker.place_order(market(10)) and len(broker.sent) == 1


def test_a_failing_snapshot_refuses_the_order():
    def no_account():
        raise ConnectionError("account summary unavailable")
    broker = FakeBroker()
    g = gate(account=no_account)
    broker.attach_risk_gate(g)
    assert broker.place_order(market(1)) is False and broker.sent == []
    assert "account summary unavailable" in g.rejections[0][1][0]


def test_the_gate_uses_the_held_position_of_the_order_symbol():
    broker = FakeBroker()
    broker.attach_risk_gate(gate(RiskLimits(max_position_quantity=25)))
    assert broker.place_order(market(10)) is False                               # 20 held + 10 > 25
    assert broker.place_order(market(10, ticker="QQQ")) and len(broker.sent) == 1  # nothing held in QQQ
