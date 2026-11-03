"""P.08.01 alert delivery: critical alerts pushed once through ntfy (HTTP stubbed — nothing leaves the machine)."""

from datetime import datetime, timezone
from types import SimpleNamespace

from src.application.services.monitoring.alert_notifier import AlertNotifier, NtfySender, _env_value, sender_from_env

NOW = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)


class Post:
    def __init__(self, status=200, fail=False):
        self.calls, self.status, self.fail = [], status, fail

    def __call__(self, url, data, timeout, headers):
        self.calls.append((url, data.decode(), headers))
        if self.fail:
            raise ConnectionError("no network")
        return SimpleNamespace(status_code=self.status)


def blocking(key="BAC"):
    return {"open_discrepancies": [{"blocking": True, "kind": "position_mismatch", "key": key,
                                    "detail": f"{key}: strategy 4, broker 5"}],
            "controls": [{"mode": "reduce_only", "scope": "strategy", "target": "S", "reason": "r",
                          "changed_by": "me"}]}                     # a warning: never pushed


def notifier(post, state):
    return AlertNotifier(NtfySender("topic-x", post=post), "STM paper", state=lambda: state[0], clock=lambda: NOW)


def test_a_critical_alert_is_pushed_once_while_it_lasts_and_again_if_it_returns():
    post, state = Post(), [blocking()]
    n = notifier(post, state)
    assert n.check() == 1 and n.check() == 0
    url, body, headers = post.calls[0]
    assert url == "https://ntfy.sh/topic-x" and "position_mismatch BAC" in body
    assert headers["Priority"] == "urgent" and "CRITICAL" in headers["Title"]
    state[0] = {}                                                   # resolved
    assert n.check() == 0
    state[0] = blocking()                                           # back again: pushed again
    assert n.check() == 1 and len(post.calls) == 2


def test_extra_alerts_and_new_alerts_are_pushed_next_to_the_active_ones():
    post, state = Post(), [blocking()]
    n = notifier(post, state)
    n.check()
    assert n.check(extra=["split guard: JPM excluded"]) == 1
    state[0]["open_discrepancies"].append(blocking("WFC")["open_discrepancies"][0])
    assert n.check(extra=["split guard: JPM excluded"]) == 1 and len(post.calls) == 3


def test_a_failed_delivery_never_raises_and_is_retried():
    post, state = Post(fail=True), [blocking()]
    n = notifier(post, state)
    assert n.check() == 0
    post.fail = False
    assert n.check() == 1
    refused = Post(status=403)
    assert NtfySender("t", post=refused).send("title", "m") is False


def test_an_unreadable_state_is_itself_an_alert():
    post = Post()
    n = AlertNotifier(NtfySender("t", post=post), "S", state=lambda: 1 / 0, clock=lambda: NOW)
    assert n.check() == 1 and "alert check failed" in post.calls[0][1]


def test_session_events_and_non_ascii_titles():
    post = Post()
    n = AlertNotifier(NtfySender("t", post=post), "STM — paper")
    assert n.event("session started", "09:40 .. 15:50")
    assert post.calls[0][2]["Title"] == "STM ? paper: session started" and post.calls[0][2]["Priority"] == "default"


def test_the_topic_comes_from_the_environment_or_the_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    env_file = tmp_path / ".env.windows"
    assert sender_from_env(env_file) is None
    env_file.write_text("IBKR_PORT=7497\nNTFY_TOPIC=abc123\n", encoding="utf-8")
    assert sender_from_env(env_file).url == "https://ntfy.sh/abc123"
    monkeypatch.setenv("NTFY_TOPIC", "from-env")
    assert _env_value("NTFY_TOPIC", env_file) == "from-env"


def test_ops_notify_test_reports_the_outcome():
    from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.ops import notify_test
    out = []
    assert notify_test(out.append, sender=NtfySender("t", post=Post())) == 0 and out == ["test push sent"]
    assert notify_test(out.append, sender=NtfySender("t", post=Post(fail=True))) == 1
