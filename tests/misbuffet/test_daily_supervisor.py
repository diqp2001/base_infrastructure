"""P.08.06 daily start and supervision: starts on trading days only, restarts a crash at most N times, alerts."""

import json
import sys
from datetime import date, datetime, time, timedelta

import pandas as pd
import pytest

from src.application.services.misbuffet.live.daily_supervisor import (
    ALREADY_RUNNING,
    DailySupervisor,
    SupervisorConfig,
    heartbeat_age_seconds,
)

CFG = SupervisorConfig(start_time=time(9, 20), max_restarts=3, restart_delay_seconds=60,
                       no_start_before_close_minutes=10)
SATURDAY, MONDAY = date(2026, 11, 7), date(2026, 11, 9)


def weekdays(start, end):
    """Fake exchange calendar: Monday to Friday, close 16:00."""
    return [(d.date(), datetime.combine(d.date(), time(16))) for d in pd.bdate_range(start, end)]


class Clock:
    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, seconds):
        self.at += timedelta(seconds=seconds)


class Alerts:
    def __init__(self):
        self.sent = []

    def event(self, what, message="", priority="default"):
        self.sent.append((what, message, priority))
        return True


def supervisor(now, codes, tmp_path, minutes_per_run=30):
    """codes: exit codes of the successive session runs; each run takes minutes_per_run."""
    clock, alerts, runs = Clock(now), Alerts(), []

    def run_session():
        runs.append(clock())
        clock.advance(60 * minutes_per_run)
        return codes[len(runs) - 1]
    sup = DailySupervisor("STM_10M_BANKS", CFG, weekdays, run_session, clock, alerts,
                          heartbeat_path=str(tmp_path / "S.supervisor.json"))
    sup.stop_event.wait = lambda seconds: clock.advance(seconds)        # sleeping = advancing the fake clock
    return sup, clock, alerts, runs


def test_nothing_starts_on_a_day_without_a_session(tmp_path):
    sup, _, alerts, runs = supervisor(datetime.combine(SATURDAY, time(9)), [], tmp_path)
    assert sup.run_once() is None and runs == [] and alerts.sent == []
    assert json.load(open(tmp_path / "S.supervisor.json"))["state"] == "no session today"


def test_a_trading_day_starts_at_the_start_time_and_a_normal_end_is_not_restarted(tmp_path):
    sup, _, alerts, runs = supervisor(datetime.combine(MONDAY, time(7)), [0], tmp_path)
    outcome = sup.run_once()
    assert runs == [datetime.combine(MONDAY, time(9, 20))]
    assert (outcome.status, outcome.attempts) == ("ended", 1) and alerts.sent == []


def test_a_crash_is_alerted_and_restarted_at_most_max_restarts_times(tmp_path):
    sup, _, alerts, runs = supervisor(datetime.combine(MONDAY, time(9, 20)), [1, 1, -9, 1, 0], tmp_path)
    outcome = sup.run_once()
    assert (outcome.status, outcome.exit_codes) == ("gave up", [1, 1, -9, 1]) and len(runs) == 4
    assert [a[0] for a in alerts.sent] == ["session crashed, restarting"] * 3 + ["session down for the day"]
    assert all(a[2] == "urgent" for a in alerts.sent)
    assert "restart 1/3 in 60 s" in alerts.sent[0][1] and "exit code -9" in alerts.sent[2][1]
    assert not any("DU" in m or "U1" in m for _, m, _ in alerts.sent)                  # never an account id


def test_a_restart_that_works_continues_the_day(tmp_path):
    sup, _, alerts, runs = supervisor(datetime.combine(MONDAY, time(9, 20)), [1, 0], tmp_path)
    assert sup.run_once().status == "ended" and len(runs) == 2 and len(alerts.sent) == 1
    assert runs[1] - runs[0] == timedelta(minutes=31)                                  # 30 min run + 60 s delay


def test_a_second_session_is_not_restarted_but_alerted(tmp_path):
    sup, _, alerts, runs = supervisor(datetime.combine(MONDAY, time(9, 20)), [ALREADY_RUNNING], tmp_path)
    assert sup.run_once().status == "already running" and len(runs) == 1
    assert [a[0] for a in alerts.sent] == ["not started"]


def test_nothing_starts_after_the_last_decision_and_no_restart_near_the_close(tmp_path):
    sup, _, alerts, runs = supervisor(datetime.combine(MONDAY, time(15, 52)), [0], tmp_path)
    assert sup.run_once().status == "session closed" and runs == [] and alerts.sent == []
    sup, _, alerts, runs = supervisor(datetime.combine(MONDAY, time(15, 0)), [1, 0], tmp_path, minutes_per_run=50)
    assert sup.run_once().status == "session closed" and len(runs) == 1
    assert [a[0] for a in alerts.sent] == ["session down"]


def test_the_daily_loop_runs_each_trading_day_once(tmp_path):
    sup, clock, _, runs = supervisor(datetime.combine(date(2026, 11, 6), time(17)), [0, 0, 0], tmp_path)
    original = sup.run_day

    def run_day(day, close):
        outcome = original(day, close)
        if len(runs) == 2:
            sup.stop()
        return outcome
    sup.run_day = run_day
    sup.run_forever()
    assert runs == [datetime.combine(MONDAY, time(9, 20)), datetime.combine(MONDAY + timedelta(1), time(9, 20))]


def test_a_real_child_process_crash_is_seen_as_a_crash(tmp_path):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.supervise import (
        ChildSession,
    )
    crash = ChildSession([sys.executable, "-c", "import os; os._exit(7)"])
    clock, alerts = Clock(datetime.combine(MONDAY, time(9, 20))), Alerts()
    codes = []

    def run():
        codes.append(crash())
        return codes[-1] if len(codes) == 1 else 0
    sup = DailySupervisor("S", CFG, weekdays, run, clock, alerts)
    sup.stop_event.wait = lambda seconds: clock.advance(seconds)
    assert sup.run_once().exit_codes == [7, 0] and "exit code 7" in alerts.sent[0][1]


def test_the_live_project_supervisor_uses_its_config_and_heartbeat(tmp_path):
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live import config as cfg
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.supervise import (
        build_supervisor,
    )
    config = {**cfg.get_config(), "results_dir": str(tmp_path)}
    sup = build_supervisor(config, run_session=lambda: pytest.fail("no session on a Saturday"),
                           now=lambda: datetime.combine(SATURDAY, time(9)), sessions=weekdays, alerts=None)
    assert sup.config == CFG and sup.run_once() is None
    assert heartbeat_age_seconds(str(tmp_path / "STM_10M_BANKS.supervisor.json")) < 60
    assert heartbeat_age_seconds(str(tmp_path / "missing.json")) is None
