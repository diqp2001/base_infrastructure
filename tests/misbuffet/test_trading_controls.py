"""
P.05 — pre-trade risk and trading controls (pure rules, fakes and in-memory SQLite; no IBKR, no orders sent).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.application.services.misbuffet.brokers.pre_trade_gate import PreTradeGate
from src.application.services.misbuffet.brokers.trading_controls import (
    IBKRAccountProvider,
    OrderThrottle,
    StreamingPriceProvider,
    TradingControlsService,
    cancel_working_orders,
)
from src.domain.entities.finance.order.pre_trade_risk import (
    AccountSnapshot,
    OrderIntent,
    PriceSnapshot,
    RiskLimits,
    check_order,
)
from src.domain.entities.finance.order.trading_control import (
    ControlMode,
    ControlScope,
    TradingControl,
    effective_mode,
    reduces_position,
)

NOW = datetime(2026, 10, 29, 15, 0)


def control(scope, target, mode, minutes=0, id=None):
    return TradingControl(scope, target, mode, "test", "owner", NOW + timedelta(minutes=minutes), id=id)


# ── domain ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_the_most_restrictive_latest_control_applies():
    rows = [control(ControlScope.GLOBAL, "*", ControlMode.DISABLED, 0),
            control(ControlScope.GLOBAL, "*", ControlMode.ENABLED, 5),          # kill switch lifted later
            control(ControlScope.STRATEGY, "CSM", ControlMode.REDUCE_ONLY, 1),
            control(ControlScope.ACCOUNT, "U2", ControlMode.DISABLED, 1)]
    assert effective_mode(rows, "U1", "CSM")[0] is ControlMode.REDUCE_ONLY
    assert effective_mode(rows, "U2", "CSM")[0] is ControlMode.DISABLED
    mode, reasons = effective_mode(rows, "U1", "STM")
    assert mode is ControlMode.ENABLED and reasons == []
    assert effective_mode([], None, None)[0] is ControlMode.ENABLED


def test_a_control_needs_a_reason_and_an_author():
    with pytest.raises(ValueError):
        TradingControl(ControlScope.GLOBAL, "*", ControlMode.DISABLED, " ", "owner", NOW)
    with pytest.raises(ValueError):
        TradingControl(ControlScope.ACCOUNT, "", ControlMode.DISABLED, "x", "owner", NOW)
    assert TradingControl(ControlScope.GLOBAL, "anything", ControlMode.DISABLED, "x", "o", NOW).target == "*"


@pytest.mark.parametrize("before,qty,ok", [(10, -4, True), (10, -10, True), (10, -12, False), (10, 2, False),
                                          (0, -1, False), (-5, 3, True), (-5, 6, False)])
def test_reduce_only_means_toward_zero_without_crossing(before, qty, ok):
    assert reduces_position(before, qty) is ok


def _fails(results):
    return {r.rule for r in results if not r.passed}


def test_new_limits_net_concentration_buying_power_and_unusable_prices():
    price = PriceSnapshot(100.0, NOW)
    account = AccountSnapshot(cash=1e9, positions={"AAPL": 100}, gross_exposure=10_000, net_exposure=10_000,
                              net_liquidation=50_000, buying_power=2_000)
    limits = RiskLimits(max_net_exposure=12_000, max_concentration=0.25, require_buying_power=True,
                        max_quote_age_seconds=None)
    assert _fails(check_order(OrderIntent("AAPL", 30), price, account, limits, NOW)) == \
        {"max_net_exposure", "max_concentration", "buying_power"}
    assert _fails(check_order(OrderIntent("AAPL", -50), price, account, limits, NOW)) == set()   # reduces: no BP
    assert _fails(check_order(OrderIntent("AAPL", 10), price, account, limits, NOW)) == set()
    no_bp = AccountSnapshot(cash=1e9, net_liquidation=None, buying_power=None)
    assert _fails(check_order(OrderIntent("MSFT", 1), price, no_bp, limits, NOW)) == {"max_concentration",
                                                                                     "buying_power"}
    results = check_order(OrderIntent("AAPL", 1), PriceSnapshot(None, None, unusable_reason="delayed"), account,
                          limits, NOW)
    assert [r.reason for r in results if not r.passed] == ["no usable price for AAPL (delayed)"]


# ── gate ─────────────────────────────────────────────────────────────────────────────────────────────────────────

class FakeControls:
    def __init__(self, mode=ControlMode.ENABLED):
        self.mode = mode

    def mode_for(self, account, strategy):
        return self.mode, ([] if self.mode is ControlMode.ENABLED else [f"global *: {self.mode.value}"])


def gate(controls=None, throttle=None, positions=None):
    account = AccountSnapshot(cash=1e6, positions=positions or {"AAPL": 10})
    return PreTradeGate(RiskLimits(max_quote_age_seconds=None), lambda: account,
                        lambda s: PriceSnapshot(100.0, NOW), clock=lambda: NOW, controls=controls,
                        account="U1", strategy="CSM", throttle=throttle)


def order(qty, symbol="AAPL"):
    return SimpleNamespace(id="o", symbol=symbol, quantity=qty)


def test_the_kill_switch_refuses_everything_and_reduce_only_lets_only_reductions_through():
    controls = FakeControls(ControlMode.DISABLED)
    g = gate(controls)
    assert not g.allows(order(-5)) and "trading disabled" in g.rejections[-1][1][0]
    controls.mode = ControlMode.REDUCE_ONLY
    assert g.allows(order(-5)) and g.allows(order(-10))
    assert not g.allows(order(1)) and not g.allows(order(-11)) and not g.allows(order(1, "MSFT"))
    controls.mode = ControlMode.ENABLED
    assert g.allows(order(1, "MSFT"))


def test_unreadable_controls_fail_closed():
    repo = Mock(**{"get_all.side_effect": RuntimeError("db down")})
    g = gate(TradingControlsService(repo))
    assert not g.allows(order(1)) and "fail closed" in g.rejections[-1][1][0]


def test_order_rate_and_duplicates():
    t = [0.0]
    throttle = OrderThrottle(max_orders=2, window_seconds=60, duplicate_seconds=30, clock=lambda: t[0])
    g = gate(throttle=throttle)
    assert g.allows(order(1))
    assert not g.allows(order(1)) and "duplicate" in g.rejections[-1][1][0]
    t[0] = 31
    assert g.allows(order(1))                                            # not a duplicate any more
    assert not g.allows(order(2)) and "order rate" in g.rejections[-1][1][0]
    t[0] = 200
    assert g.allows(order(2))
    refused = gate(throttle=OrderThrottle(working_symbols=lambda: ["AAPL"], clock=lambda: t[0]))
    assert not refused.allows(order(1)) and "still working" in refused.rejections[-1][1][0]


def test_a_refused_order_is_not_counted_by_the_throttle():
    throttle = OrderThrottle(max_orders=1, clock=lambda: 0.0)
    g = gate(controls=FakeControls(ControlMode.DISABLED), throttle=throttle)
    assert not g.allows(order(1))
    g.controls.mode = ControlMode.ENABLED
    assert g.allows(order(1))


def test_the_ibkr_broker_sends_nothing_without_a_gate():
    from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
    assert InteractiveBrokersBroker.requires_risk_gate is True


# ── controls service (SQLite) ────────────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def repo():
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.local_repo.finance.order.broker_order_repository import (
        TradingControlRepository,
    )
    engine = create_engine("sqlite:///:memory:")
    ModelBase.metadata.create_all(engine)
    session = Session(engine)
    yield TradingControlRepository(session)
    session.close()
    engine.dispose()


def test_controls_are_append_only_and_audited(repo):
    t = [datetime(2026, 10, 29, 15, 0, tzinfo=timezone.utc)]
    svc = TradingControlsService(repo, clock=lambda: t[0])
    svc.kill("broker incident", "owner")
    assert svc.mode_for("U1", "CSM")[0] is ControlMode.DISABLED
    t[0] += timedelta(minutes=1)
    svc.set(ControlScope.GLOBAL, "*", ControlMode.REDUCE_ONLY, "liquidating", "owner")
    t[0] += timedelta(minutes=1)
    svc.set(ControlScope.GLOBAL, "*", ControlMode.ENABLED, "incident closed", "owner")
    assert svc.mode_for("U1", "CSM")[0] is ControlMode.ENABLED
    assert [c.mode for c in svc.history()] == [ControlMode.DISABLED, ControlMode.REDUCE_ONLY, ControlMode.ENABLED]
    with pytest.raises(NotImplementedError):
        repo.update(svc.history()[0])


# ── providers and emergency action ───────────────────────────────────────────────────────────────────────────────

def test_streaming_prices_size_orders_only_when_executable():
    from src.domain.entities.finance.market_data.streaming_observation import Assessment, Usability
    obs = SimpleNamespace(bid=99.9, ask=100.1, quote_time=NOW, received_at=NOW)
    svc = Mock()
    svc.observation.return_value = obs
    svc.assess.return_value = Assessment(Usability.CURRENT, True, ())
    snap = StreamingPriceProvider(svc, clock=lambda: NOW)("AAPL")
    assert (snap.price, snap.as_of, snap.unusable_reason) == (100.1, NOW, None)
    svc.assess.assert_called_with("STK:AAPL", NOW)
    svc.assess.return_value = Assessment(Usability.DELAYED, False, ("delayed data: never executable",))
    snap = StreamingPriceProvider(svc, clock=lambda: NOW)("AAPL")
    assert snap.price is None and "delayed" in snap.unusable_reason


class FakeAccountClient:
    def __init__(self):
        self.values_ok = self.positions_ok = True
        self.account_values_snapshot = {"U1": {"NetLiquidation": ("50000", "USD"), "TotalCashValue": ("20000", "USD"),
                                               "BuyingPower": ("80000", "USD")},
                                        "U2": {"NetLiquidation": ("1", "USD")}}
        self.positions_snapshot = [{"account": "U1", "symbol": "AAPL", "secType": "STK", "position": 100},
                                   {"account": "U1", "symbol": "SPY", "secType": "OPT",
                                    "localSymbol": "SPY   261218C00700000", "position": -2},
                                   {"account": "U2", "symbol": "MSFT", "secType": "STK", "position": 7}]

    def request_account_values_snapshot(self, timeout=10.0):
        return self.values_ok

    def request_positions_snapshot(self, timeout=10.0):
        return self.positions_ok


def test_the_ibkr_account_provider_values_one_account_and_fails_closed():
    client = FakeAccountClient()
    prices = {"AAPL": PriceSnapshot(150.0, NOW), "SPY 261218C00700000": PriceSnapshot(5.0, NOW)}
    provider = IBKRAccountProvider(client, "U1", prices.get, multiplier_provider=lambda s: 100.0 if "SPY" in s else 1)
    snap = provider()
    assert snap.positions == {"AAPL": 100, "SPY 261218C00700000": -2}
    assert (snap.cash, snap.net_liquidation, snap.buying_power) == (20_000, 50_000, 80_000)
    assert (snap.gross_exposure, snap.net_exposure) == (15_000 + 1_000, 15_000 - 1_000)
    del prices["AAPL"]
    with pytest.raises(RuntimeError, match="no price"):
        provider()
    client.values_ok = False
    with pytest.raises(RuntimeError, match="incomplete"):
        provider()
    with pytest.raises(ValueError):
        IBKRAccountProvider(client, "", prices.get)


def test_cancel_working_orders_requests_cancels_only():
    bos = [SimpleNamespace(order_id=1, broker_order_id=601, cancel_requested_at=None),
           SimpleNamespace(order_id=2, broker_order_id=None, cancel_requested_at=None),      # never reached IBKR
           SimpleNamespace(order_id=3, broker_order_id=603, cancel_requested_at=NOW),       # already requested
           SimpleNamespace(order_id=4, broker_order_id=604, cancel_requested_at=None)]
    ledger = Mock(**{"open_orders.return_value": bos})
    client = Mock()
    client.cancel_order.side_effect = [None, ConnectionError("down")]
    assert cancel_working_orders(ledger, client, "kill switch") == [1]
    ledger.request_cancel.assert_called_once_with(1)


def test_the_ibkr_client_collects_account_values():
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    c = IBTWSClient("127.0.0.1", 7497, 99)
    c._account_summary_collecting = True
    c.accountSummary(1, "U1", "NetLiquidation", "123.4", "USD")
    c.accountSummaryEnd(1)
    c.accountSummary(1, "U1", "BuyingPower", "9", "USD")                # after the end: not collected
    assert c.account_values_snapshot == {"U1": {"NetLiquidation": ("123.4", "USD")}}
    assert c._account_summary_end_event.is_set()


def test_liquidate_all_targets_zero_for_every_held_instrument():
    from src.application.services.misbuffet.brokers.trading_controls import liquidate_all
    upm = Mock(**{"_get_all_held_tickers.return_value": {"MSFT", "AAPL"}, "set_holdings.return_value": {"AAPL": True}})
    assert liquidate_all(upm, "data") == {"AAPL": True}
    upm.set_holdings.assert_called_once_with({"AAPL": 0.0, "MSFT": 0.0}, "data", tag="liquidate_all")
    assert liquidate_all(Mock(**{"_get_all_held_tickers.return_value": set()}), "data") == {}
