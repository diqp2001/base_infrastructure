"""
IBKR historical-data adapter (InteractiveBrokersBroker.get_historical_data + IBTWSClient callbacks).

A real IBTWSClient is used; only reqHistoricalData is replaced by a script that plays constructed
IBKR callbacks (historicalData / historicalDataEnd / error) on another thread, like the API does.
Nothing connects to IBKR.
"""

import threading
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from ibapi.contract import Contract

from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker

ET = ZoneInfo("US/Eastern")


def bar(day, close):
    return SimpleNamespace(date=day, open=close - 1, high=close + 1, low=close - 2, close=close, volume=1_000, barCount=10)


@pytest.fixture
def broker(monkeypatch):
    monkeypatch.setenv("IBKR_HISTORY_RETRIES", "2")
    monkeypatch.setenv("IBKR_HISTORY_RETRY_DELAY", "0")          # retries without waiting (backoff tested below)
    b = InteractiveBrokersBroker({"host": "127.0.0.1", "port": 1, "client_id": 1})
    client = IBTWSClient("127.0.0.1", 1, 1)
    client.is_connected = lambda: True
    b.ib_connection = client
    from src.application.services.misbuffet.brokers.ibkr.history_pacing import HistoryPacer
    b.history_pacer = HistoryPacer(sleep=lambda seconds: None)    # pacing has its own tests; never wait here
    b.requests = []
    b.script = lambda req_id: [("end",)]

    def fake_req_historical_data(req_id, contract, end, duration, bar_size, what, rth, fmt, keep_up, options):
        b.requests.append(dict(req_id=req_id, contract=contract, end=end, duration=duration, bar_size=bar_size,
                               what=what, rth=rth, keep_up=keep_up))

        def play():
            for step in b.script(req_id):
                kind = step[0]
                if kind == "bar":
                    client.historicalData(req_id, step[1])
                elif kind == "sleep":
                    time.sleep(step[1])
                elif kind == "error":
                    client.error(req_id, step[1], step[2])
                elif kind == "end":
                    client.historicalDataEnd(req_id, "start", "end")
        threading.Thread(target=play, daemon=True).start()

    client.reqHistoricalData = fake_req_historical_data
    return b


def stock(symbol="SPY"):
    c = Contract()
    c.symbol, c.secType, c.exchange, c.currency = symbol, "STK", "SMART", "USD"
    return c


def recent(days=10, hour=10, minute=0):
    d = (datetime.now(ET) - timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return d.replace(tzinfo=None)


class TestRequestParameters:

    def test_parameters_reach_reqHistoricalData(self, broker):
        broker.script = lambda r: [("bar", bar("20260105", 100.0)), ("end",)]
        broker.get_historical_data(stock(), end_date_time=recent(), duration_str="3 D", bar_size_setting="1 hour",
                                   what_to_show="MIDPOINT", use_rth=False, timeout=5)
        req, = broker.requests
        assert (req["duration"], req["bar_size"], req["what"], req["rth"], req["keep_up"]) == \
            ("3 D", "1 hour", "MIDPOINT", False, False)
        assert req["contract"].secType == "STK"

    def test_request_ids_are_unique(self, broker):
        for _ in range(50):
            broker.get_historical_data(stock(), end_date_time="", timeout=5)
        ids = [r["req_id"] for r in broker.requests]
        assert len(set(ids)) == len(ids) == 50

    def test_disconnected_client_sends_nothing(self, broker):
        broker.ib_connection.is_connected = lambda: False
        assert broker.get_historical_data(stock(), timeout=1) == []
        assert broker.requests == []


class TestCallbackHandling:

    def test_all_bars_until_historical_data_end(self, broker):
        broker.script = lambda r: [("bar", bar("20260105", 100.0)), ("bar", bar("20260106", 101.0)), ("end",)]
        bars = broker.get_historical_data(stock(), timeout=5)
        assert [(b["date"], b["close"]) for b in bars] == [("20260105", 100.0), ("20260106", 101.0)]
        assert set(bars[0]) == {"date", "open", "high", "low", "close", "volume", "barCount"}

    def test_slow_delivery_is_not_truncated(self, broker):
        """Regression: completion was 'some bars and 2 s' — bars arriving later were dropped."""
        broker.script = lambda r: [("bar", bar("20260105", 100.0)), ("sleep", 2.6), ("bar", bar("20260106", 101.0)),
                                   ("end",)]
        assert len(broker.get_historical_data(stock(), timeout=10)) == 2

    def test_empty_answer_returns_without_waiting_for_the_timeout(self, broker):
        """Regression: an empty history always waited the full timeout (90 s by default)."""
        broker.script = lambda r: [("end",)]
        started = time.monotonic()
        assert broker.get_historical_data(stock(), timeout=30) == []
        assert time.monotonic() - started < 3

    def test_no_data_error_ends_the_request(self, broker):
        broker.script = lambda r: [("error", 162, "Historical Market Data Service error message: no data")]
        started = time.monotonic()
        assert broker.get_historical_data(stock(), timeout=30) == []
        assert time.monotonic() - started < 3
        assert len(broker.requests) == 1                          # an answer: never retried

    def test_informational_messages_do_not_end_the_request(self, broker):
        broker.script = lambda r: [("error", 2106, "HMDS data farm connection is OK"), ("bar", bar("20260105", 1.0)),
                                   ("end",)]
        assert len(broker.get_historical_data(stock(), timeout=5)) == 1

    def test_no_end_signal_gives_no_data_after_the_timeout(self, broker):
        broker.script = lambda r: [("bar", bar("20260105", 100.0))]
        assert broker.get_historical_data(stock(), timeout=1) == []
        assert len(broker.requests) == 3                          # 1 + IBKR_HISTORY_RETRIES, then gives up

    def test_cached_requests_are_not_sent_twice(self, broker):
        broker.max_import_ibkr = True
        broker.script = lambda r: [("bar", bar("20260105", 100.0)), ("end",)]
        end = recent()
        first = broker.get_historical_data(stock(), end_date_time=end, timeout=5)
        second = broker.get_historical_data(stock(), end_date_time=end, timeout=5)
        assert first == second and len(broker.requests) == 1


class TestEndDateFormatting:
    """IBKR end boundary is exclusive and in UTC: 'yyyymmdd-hh:mm:ss'."""

    @pytest.fixture
    def fmt(self, broker):
        return broker.format_ib_datetime

    def test_empty_means_now(self, fmt):
        assert fmt("") == "" and fmt(None) == ""

    def test_naive_times_are_eastern_with_daylight_saving(self, fmt):
        assert fmt(datetime(2026, 1, 15, 9, 35)) == "20260115-14:35:01"      # EST, UTC-5
        assert fmt(datetime(2026, 7, 15, 9, 35)) == "20260715-13:35:01"      # EDT, UTC-4

    def test_midnight_includes_the_whole_last_day(self, fmt):
        assert fmt(datetime(2026, 1, 15)) == "20260116-05:00:00"

    def test_duration_extends_the_window_by_the_session(self, fmt):
        assert fmt(datetime(2026, 1, 15, 9, 35), duration="1 D") == "20260115-21:35:01"

    def test_iso_strings_are_accepted_and_garbage_is_refused(self, fmt):
        assert fmt("2026-01-15T09:35:00") == "20260115-14:35:01"
        with pytest.raises(ValueError):
            fmt("15/01/2026")
        with pytest.raises(TypeError):
            fmt(20260115)

    def test_aware_utc_input_is_kept_in_utc(self, fmt):
        assert fmt(datetime(2026, 1, 15, 14, 35, tzinfo=timezone.utc)) == "20260115-14:35:01"


class TestSixMonthWindow:

    @pytest.fixture
    def check(self, broker):
        return broker.validate_end_date_within_6_months

    def test_recent_dates_and_now_are_accepted(self, check):
        check(recent(days=10))
        check("")

    def test_future_dates_are_refused(self, check):
        with pytest.raises(ValueError, match="future"):
            check(datetime.now(ET).replace(tzinfo=None) + timedelta(days=2))

    def test_dates_older_than_six_months_are_refused(self, check):
        with pytest.raises(ValueError, match="6 months"):
            check(recent(days=200))


class TestRetries:
    """BI-029: transient failures retried, bounded, with exponential backoff; answers are final."""

    PACING = (162, "Historical Market Data Service error message:Historical data request pacing violation")

    def test_a_pacing_violation_is_retried_and_the_retry_succeeds(self, broker):
        broker.script = lambda r: ([("error", *self.PACING)] if len(broker.requests) == 1
                                   else [("bar", bar("20260105", 100.0)), ("end",)])
        assert len(broker.get_historical_data(stock(), timeout=5)) == 1
        assert len(broker.requests) == 2 and len({r["req_id"] for r in broker.requests}) == 2

    def test_retries_are_bounded(self, broker):
        broker.script = lambda r: [("error", 10182, "Failed to request historical data: data farm disconnected")]
        assert broker.get_historical_data(stock(), timeout=5) == []
        assert len(broker.requests) == 3

    def test_backoff_doubles(self, broker, monkeypatch):
        monkeypatch.setenv("IBKR_HISTORY_RETRY_DELAY", "10")
        broker.script = lambda r: [("error", *self.PACING)]
        with patch("src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker.time.sleep") as sleep:
            assert broker.get_historical_data(stock(), timeout=5) == []
        assert [c.args[0] for c in sleep.call_args_list] == [10.0, 20.0]

    def test_no_retry_when_disabled(self, broker, monkeypatch):
        monkeypatch.setenv("IBKR_HISTORY_RETRIES", "0")
        broker.script = lambda r: [("error", *self.PACING)]
        assert broker.get_historical_data(stock(), timeout=5) == []
        assert len(broker.requests) == 1
