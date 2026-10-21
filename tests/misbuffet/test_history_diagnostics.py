"""The IBKR history diagnostic: one request per (whatToShow, useRTH), rows built from HistoryResult; read-only."""

from types import SimpleNamespace

import pytest

from src.application.services.misbuffet.brokers.ibkr.history_diagnostics import block_orders, run_matrix, stock
from src.application.services.misbuffet.brokers.ibkr.history_result import HistoryResult


class FakeBroker:
    def __init__(self):
        self.calls = []

    def format_ib_datetime(self, date_time, duration):
        return "20261021-20:00:00"

    def request_history(self, contract, end, duration, bar_size, what, use_rth=True, timeout=60):
        self.calls.append((what, use_rth))
        if what == "TRADES":
            return HistoryResult(len(self.calls), "complete", what, [{"date": "20261019"}, {"date": "20261021"}])
        return HistoryResult(len(self.calls), "failed", what, error_code=162,
                             error_message="No market data permissions for ISLAND STK.")


def test_the_matrix_requests_each_case_once_and_reports_it():
    broker = FakeBroker()
    rows = run_matrix(broker, stock("MSFT"))
    assert broker.calls == [(w, rth) for rth in (True, False) for w in ("TRADES", "MIDPOINT", "BID", "ASK")]
    trades, midpoint = rows[0], rows[1]
    assert (trades.status, trades.bars, trades.first_bar, trades.last_bar) == ("complete", 2, "20261019", "20261021")
    assert (midpoint.status, midpoint.failure, midpoint.error_code) == ("failed", "permission", 162)


def test_the_diagnostic_client_cannot_send_orders():
    client = SimpleNamespace()
    block_orders(client)
    with pytest.raises(RuntimeError, match="read-only"):
        client.placeOrder(1, None, None)


def test_occ_symbols_and_futures_are_built_for_the_diagnostic():
    from src.application.services.misbuffet.brokers.ibkr.history_diagnostics import (
        future_by_local_symbol, option_from_occ,
    )
    o = option_from_occ("SPY   281215C00775000")
    assert (o.symbol, o.secType, o.lastTradeDateOrContractMonth, o.right, o.strike, o.multiplier) == \
        ("SPY", "OPT", "20281215", "C", 775.0, "100")
    f = future_by_local_symbol("SR3Z6", "CME")
    assert (f.localSymbol, f.secType, f.exchange) == ("SR3Z6", "FUT", "CME")
