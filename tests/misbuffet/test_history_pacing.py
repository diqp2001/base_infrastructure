"""BI-029: IBKR historical pacing rules enforced before sending (fake clock, nothing waits for real)."""

from src.application.services.misbuffet.brokers.ibkr.history_pacing import HistoryPacer


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(round(s, 6))
        self.t += s


def pacer():
    c = Clock()
    return HistoryPacer(clock=c.now, sleep=c.sleep), c


def test_different_requests_go_immediately():
    p, c = pacer()
    for i in range(5):
        assert p.acquire(("SPY", i), ("SPY",)) == 0
    assert c.slept == []


def test_an_identical_request_waits_15_seconds():
    p, c = pacer()
    p.acquire(("SPY", "1 D"), ("SPY",))
    c.t += 4
    assert p.acquire(("SPY", "1 D"), ("SPY",)) == 11.0


def test_more_than_6_requests_for_one_contract_in_2_seconds_wait():
    p, c = pacer()
    for i in range(6):
        p.acquire(("SPY", i), ("SPY", "TRADES"))
    assert p.acquire(("SPY", 6), ("SPY", "TRADES")) == 2.0
    assert p.acquire(("QQQ", 0), ("QQQ", "TRADES")) == 0            # another contract is not held back


def test_more_than_60_requests_in_10_minutes_wait():
    p, c = pacer()
    for i in range(60):
        p.acquire(("C", i), (f"C{i}",))
        c.t += 1                                                     # one per second
    waited = p.acquire(("C", 60), ("C60",))
    assert waited == 600 - 60                                       # until the first one leaves the window
