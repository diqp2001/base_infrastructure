"""EulerpoolClient: authentication, configuration, errors, retries - with a fake session (no request leaves)."""

import json

import pytest

from src.infrastructure.repositories.eulerpool_repo.eulerpool_client import (
    BASE_URL,
    EulerpoolAuthenticationError,
    EulerpoolClient,
    EulerpoolError,
    EulerpoolNotFound,
    EulerpoolRateLimitError,
    EulerpoolResponseError,
    EulerpoolUnavailable,
    identifier_path,
    load_api_key,
)
from tests.eulerpool.fake_eulerpool import KEY, FakeSession, Response


class Scripted:
    """Answers the given responses in order (then the last one again)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r


def client(session, **kw):
    return EulerpoolClient(KEY, session=session, min_interval=0, sleep=lambda s: None, **kw)


def test_the_key_goes_in_a_bearer_header_never_in_the_url():
    session = FakeSession()
    client(session).get("fundamentals/company/ACME")
    url, params, headers = session.calls[0]
    assert headers["Authorization"] == f"Bearer {KEY}" and headers["Accept"] == "application/json"
    assert KEY not in url and KEY not in json.dumps(params)
    assert url == f"{BASE_URL}/fundamentals/company/ACME"


def test_a_missing_key_is_refused_and_a_wrong_one_is_an_authentication_error_without_the_key():
    with pytest.raises(EulerpoolAuthenticationError):
        EulerpoolClient("")
    wrong = EulerpoolClient("wrong-key-123", session=FakeSession(), min_interval=0)
    with pytest.raises(EulerpoolAuthenticationError) as e:
        wrong.get("fundamentals/company/ACME")
    assert "wrong-key-123" not in str(e.value)


@pytest.mark.parametrize("status, error", [(401, EulerpoolAuthenticationError), (403, EulerpoolAuthenticationError),
                                           (404, EulerpoolNotFound), (400, EulerpoolError)])
def test_error_statuses(status, error):
    c = client(Scripted(Response(status, {"error": f"echo {KEY}"}, text=f"echo {KEY}")))
    with pytest.raises(error) as e:
        c.get("fundamentals/company/X")
    assert KEY not in str(e.value)


def test_429_and_5xx_are_retried_then_raised():
    waits = []
    c = EulerpoolClient(KEY, session=Scripted(Response(429, text="slow down", headers={"retry-after": "7"}),
                                              Response(503, text="down"), Response(200, [{"a": 1}])),
                        min_interval=0, sleep=waits.append, retries=2)
    assert c.get("fundamentals/x") == [{"a": 1}] and waits == [7.0, 4.0] and c.requests_made == 3
    with pytest.raises(EulerpoolRateLimitError):
        client(Scripted(Response(429, text="slow down")), retries=1).get("fundamentals/x")
    with pytest.raises(EulerpoolUnavailable):
        client(Scripted(Response(500, {"error": "Internal server error"})), retries=1).get("fundamentals/x")
    with pytest.raises(EulerpoolUnavailable):
        client(Scripted(ConnectionError(f"https://x?{KEY}")), retries=1).get("fundamentals/x")


def test_malformed_and_error_bodies():
    with pytest.raises(EulerpoolResponseError):
        client(Scripted(Response(200, ValueError("bad json"), text="<html>"))).get("fundamentals/x")
    with pytest.raises(EulerpoolResponseError):
        client(Scripted(Response(200, "a string"))).get("fundamentals/x")
    with pytest.raises(EulerpoolError):
        client(Scripted(Response(200, {"error": "Something"}))).get("fundamentals/x")
    assert client(Scripted(Response(200, []))).get("fundamentals/x") == []          # empty answer: no data, no error


def test_rate_limit_headers_are_kept():
    c = client(FakeSession())
    c.get("fundamentals/company/ACME")
    assert c.rate_limit["x-ratelimit-limit"] == "100000"


def test_configuration_from_environment_and_credentials_file(tmp_path, monkeypatch):
    monkeypatch.delenv("EULERPOOL_API_KEY", raising=False)
    path = tmp_path / "eulerpool_credentials.json"
    path.write_text(json.dumps({"api_key": " file-key "}), encoding="utf-8")
    monkeypatch.setenv("EULERPOOL_CREDENTIALS_FILE", str(path))
    assert load_api_key() == "file-key"
    monkeypatch.setenv("EULERPOOL_API_KEY", "env-key")
    assert load_api_key() == "env-key"
    monkeypatch.delenv("EULERPOOL_API_KEY")
    monkeypatch.setenv("EULERPOOL_CREDENTIALS_FILE", str(tmp_path / "missing.json"))
    assert load_api_key() is None and EulerpoolClient.from_environment() is None
    monkeypatch.setenv("EULERPOOL_BASE_URL", "https://example.test/api/1/")
    assert EulerpoolClient("k", session=FakeSession()).url("fundamentals/x") == "https://example.test/api/1/fundamentals/x"


def test_identifiers():
    assert identifier_path(" aapl ") == "AAPL" and identifier_path("US0378331005") == "US0378331005"
    assert identifier_path("BRK.B") == "BRK.B"
    for bad in ("", "  ", "A/B", None):
        with pytest.raises(ValueError):
            identifier_path(bad)
