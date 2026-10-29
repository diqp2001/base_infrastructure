"""LiveClock (wall-clock pacing of the engine for live / paper trading) and its hook in the engine loop."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.application.services.misbuffet.live.live_clock import RUN, SKIP, STOP, LiveClock


class FakeTime:
    def __init__(self, utc: datetime):
        self.t = utc
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += timedelta(seconds=seconds)


def clock_at(utc: datetime, **kw):
    ft = FakeTime(utc)
    return LiveClock("America/New_York", now=ft.now, sleep=ft.sleep, **kw), ft


UTC = timezone.utc


def test_a_step_runs_only_after_its_bar_has_closed_plus_grace():
    # 2026-10-29 is EDT (UTC-4): the 10:10 New York step is due at 14:10:20 UTC
    clock, ft = clock_at(datetime(2026, 10, 29, 14, 5, tzinfo=UTC), grace_seconds=20)
    assert clock.wait_for(datetime(2026, 10, 29, 10, 10)) == RUN
    assert ft.t >= datetime(2026, 10, 29, 14, 10, 20, tzinfo=UTC) and ft.sleeps
    assert clock.exchange_now() >= datetime(2026, 10, 29, 10, 10, 20)


def test_a_step_reached_too_late_is_skipped_not_traded():
    clock, ft = clock_at(datetime(2026, 10, 29, 14, 30, tzinfo=UTC), grace_seconds=20, max_lag_seconds=300)
    assert clock.wait_for(datetime(2026, 10, 29, 10, 10)) == SKIP           # 19m40s late
    assert clock.skipped == [datetime(2026, 10, 29, 10, 10)] and not ft.sleeps
    assert clock.wait_for(datetime(2026, 10, 29, 10, 30)) == RUN            # due 14:30:20: waits 20 s
    assert sum(ft.sleeps) == 20 and max(ft.sleeps) <= clock.poll_seconds


def test_stop_ends_the_wait():
    clock, ft = clock_at(datetime(2026, 10, 29, 14, 0, tzinfo=UTC))
    clock.request_stop("owner")
    assert clock.wait_for(datetime(2026, 10, 29, 10, 10)) == STOP and clock.stop_reason == "owner"


def test_the_engine_loop_waits_skips_and_stops_on_the_live_clock():
    from src.application.services.misbuffet.engine.misbuffet_engine import MisbuffetEngine

    verdicts = {datetime(2026, 10, 29, 10, 10): SKIP, datetime(2026, 10, 29, 10, 40): STOP}
    asked, seen = [], []

    class Clock:
        stop_reason = "test"

        def wait_for(self, t):
            asked.append(t)
            return verdicts.get(t, RUN)

    engine = MisbuffetEngine()
    engine.algorithm = SimpleNamespace(universe=["JPM"], bar_size_setting="10 mins", duration_str="1 D",
                                       on_data=lambda data: seen.append(data.time), time=None)
    engine.data_loader = SimpleNamespace(market_data_service=SimpleNamespace(
        create_data_slice=lambda t, *a: SimpleNamespace(has_data=True, time=t)))
    config = SimpleNamespace(live_clock=Clock(), custom_config={
        "start_date": datetime(2026, 10, 29, 10, 0), "end_date": datetime(2026, 10, 29, 11, 0),
        "custom_interval": {"custom_interval_minutes": 10, "session_start": "09:40", "session_end": "15:50"}})
    engine._run_simulation(config)
    t = lambda h, m: datetime(2026, 10, 29, h, m)  # noqa: E731
    assert asked == [t(10, 0), t(10, 10), t(10, 20), t(10, 30), t(10, 40)]
    assert seen == [t(10, 0), t(10, 20), t(10, 30)]                         # 10:10 skipped, stopped at 10:40


def test_the_engine_calls_before_step_on_due_steps_before_the_slice():
    from src.application.services.misbuffet.engine.misbuffet_engine import MisbuffetEngine

    events = []

    class Clock:
        stop_reason = None

        def wait_for(self, t):
            return SKIP if t == datetime(2026, 10, 29, 10, 10) else RUN

    engine = MisbuffetEngine()
    engine.algorithm = SimpleNamespace(universe=["JPM"], bar_size_setting="10 mins", duration_str="1 D", time=None,
                                       before_step=lambda t: events.append(("before", t)),
                                       on_data=lambda data: events.append(("data", data.time)))
    engine.data_loader = SimpleNamespace(market_data_service=SimpleNamespace(
        create_data_slice=lambda t, *a: events.append(("slice", t)) or SimpleNamespace(has_data=True, time=t)))
    config = SimpleNamespace(live_clock=Clock(), custom_config={
        "start_date": datetime(2026, 10, 29, 10, 0), "end_date": datetime(2026, 10, 29, 10, 10),
        "custom_interval": {"custom_interval_minutes": 10, "session_start": "09:40", "session_end": "15:50"}})
    engine._run_simulation(config)
    t = datetime(2026, 10, 29, 10, 0)
    assert events == [("before", t), ("slice", t), ("data", t)]            # 10:10 skipped: nothing called
