"""
A failed or interrupted experiment can be retried from its page: a NEW experiment of the same strategy over the same
window and capital, linked to the failed one (which is kept); a running / succeeded one cannot.
"""

from datetime import datetime

import pytest

from tests.strategy.test_strategy_web import _create, _form


@pytest.fixture
def web(tmp_path, monkeypatch):
    from tests.strategy.test_strategy_web import web as base_web
    yield from base_web.__wrapped__(tmp_path, monkeypatch)


def _launch(web, cid):
    web.client.post(f"/strategies/{cid}/edit", data=_form(web, cid))
    r = web.client.post(f"/strategies/{cid}/launch", data={"confirm": "yes", "backtest_start": "2024-01-02",
                                                          "backtest_end": "2024-06-28", "initial_capital": "250000"})
    return int(r.headers["Location"].rstrip("/").split("/")[-1])


def _finish(web, experiment_id, how):
    s = web.services()
    e = s.experiments.get(experiment_id)
    if e.status == "queued":
        e.start(1, "web-test", datetime(2026, 11, 20))
    at = datetime(2026, 11, 20, 1)
    if how == "succeed":
        e.succeed(at)
    else:
        getattr(e, how)(at, "boom")
    s.experiments.repository.update(e)
    s.session.close()


def test_a_failed_experiment_is_retried_with_the_same_window(web):
    cid = _create(web)
    first = _launch(web, cid)
    page = web.client.get(f"/strategies/experiments/{first}").get_data(as_text=True)
    assert "Retry" not in page                                          # queued: nothing to retry
    _finish(web, first, "fail")
    assert ">Retry<" in web.client.get(f"/strategies/experiments/{first}").get_data(as_text=True)
    r = web.client.post(f"/strategies/experiments/{first}/retry")
    second = int(r.headers["Location"].rstrip("/").split("/")[-1])
    assert second != first and web.runner.started == [first, second]
    s = web.services()
    old, new = s.experiments.get(first), s.experiments.get(second)
    assert old.status == "failed"                                       # the failed run is kept
    assert (new.strategy_id, new.backtest_start, new.backtest_end, new.initial_capital) == (
        old.strategy_id, old.backtest_start, old.backtest_end, 250000.0)
    assert new.provenance["retry_of"] == first
    assert f"experiment {first}" in web.client.get(f"/strategies/experiments/{second}").get_data(as_text=True)


def test_only_failed_or_interrupted_experiments_can_be_retried(web):
    cid = _create(web)
    first = _launch(web, cid)
    _finish(web, first, "succeed")
    assert ">Retry<" not in web.client.get(f"/strategies/experiments/{first}").get_data(as_text=True)
    html = web.client.post(f"/strategies/experiments/{first}/retry", follow_redirects=True).get_data(as_text=True)
    assert "only a failed or interrupted experiment can be retried" in html and len(web.runner.started) == 1
    second = _launch(web, cid)
    _finish(web, second, "interrupt")
    r = web.client.post(f"/strategies/experiments/{second}/retry")
    assert r.status_code == 302 and len(web.runner.started) == 3
