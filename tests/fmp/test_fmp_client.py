"""FMPClient: configuration, request construction, authentication and the provider's error statuses (fake session -
nothing is downloaded)."""

import json

import pytest

from src.infrastructure.repositories.fmp_repo.fmp_client import (
    BASE_URL, FMPAuthenticationError, FMPClient, FMPError, FMPRateLimitError, FMPResponseError, FMPSubscriptionError,
    FMPUnavailable, load_api_key,
)
from tests.fmp.fake_fmp import FakeSession, Response

KEY = "secret-test-key"


class _One:
    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def client(response, **kwargs):
    session = _One(response)
    return FMPClient(KEY, session=session, min_interval=0, **kwargs), session


def test_the_key_comes_from_the_environment_then_the_credentials_file(tmp_path, monkeypatch):
    path = tmp_path / "creds.json"
    path.write_text(json.dumps({"api_key": "from-file"}), encoding="utf-8")
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    assert load_api_key(str(path)) == "from-file"
    monkeypatch.setenv("FMP_API_KEY", "from-env")
    assert load_api_key(str(path)) == "from-env"
    monkeypatch.delenv("FMP_API_KEY")
    assert load_api_key(str(tmp_path / "missing.json")) is None
    assert FMPClient.from_environment(str(tmp_path / "missing.json")) is None
    with pytest.raises(FMPAuthenticationError):
        FMPClient("")


def test_a_request_is_the_stable_endpoint_with_the_key_as_a_parameter():
    c, session = client(Response(200, [{"symbol": "ACME"}]))
    assert c.get("income-statement", symbol="ACME", period="Q1", limit=5) == [{"symbol": "ACME"}]
    url, params, timeout = session.calls[0]
    assert url == f"{BASE_URL}/income-statement" and BASE_URL.endswith("/stable")
    assert params == {"symbol": "ACME", "period": "Q1", "limit": 5, "apikey": KEY} and timeout == 30.0
    assert c.url("/balance-sheet-statement") == f"{BASE_URL}/balance-sheet-statement"


def test_an_empty_answer_is_no_rows():
    assert client(Response(200, []))[0].get("income-statement", symbol="ACME") == []


@pytest.mark.parametrize("response, error", [
    (Response(401, {"Error Message": "Invalid API KEY"}), FMPAuthenticationError),
    (Response(403, {}), FMPAuthenticationError),
    (Response(402, text="Restricted Endpoint"), FMPSubscriptionError),
    (Response(429, text="Limit Reach"), FMPRateLimitError),
    (Response(503, text="down"), FMPUnavailable),
    (Response(404, text="nope"), FMPError),
    (Response(200, {"Error Message": "something"}), FMPError),
    (Response(200, {"symbol": "ACME"}), FMPResponseError),            # an object, not a list
    (Response(200, [1, 2]), FMPResponseError),                          # a list of scalars
    (Response(200, ValueError("bad json"), text="<html>"), FMPResponseError),
    (ConnectionError("https://financialmodelingprep.com/stable/x?apikey=" + KEY), FMPUnavailable),
])
def test_every_failure_is_an_fmp_error_that_never_shows_the_key(response, error):
    c, _ = client(response)
    with pytest.raises(error) as raised:
        c.get("income-statement", symbol="ACME")
    assert KEY not in str(raised.value)


def test_requests_are_paced():
    waits, now = [], [0.0]
    c = FMPClient(KEY, session=FakeSession(), min_interval=0.5, sleep=waits.append, clock=lambda: now[0])
    c.get("income-statement", symbol="ACME", period="FY")
    now[0] = 0.2
    c.get("income-statement", symbol="ACME", period="FY")
    assert waits == [pytest.approx(0.3)] and c.requests_made == 2
