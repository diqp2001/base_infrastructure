"""
Eulerpool HTTP client (https://api.eulerpool.com/api/1) - the counterpart of fmp_repo/fmp_client.py.

Holds the API key, the request pacing, a short retry on 429 / 5xx and the provider's error statuses; returns the
decoded JSON. It knows no domain entity: the repositories in this package normalize the answers.

Key: EULERPOOL_API_KEY in the environment, else the 'api_key' of a JSON credentials file (EULERPOOL_CREDENTIALS_FILE,
default eulerpool_credentials.json next to the repository folder, like FPM_credentials.json). Base URL:
EULERPOOL_BASE_URL, else BASE_URL. The key is sent as 'Authorization: Bearer <key>' and never appears in an error
message or a log line. Quota (2026-11-13): 100,000 requests a month (x-ratelimit-* headers, kept in ``rate_limit``).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

BASE_URL = "https://api.eulerpool.com/api/1"
DEFAULT_CREDENTIALS_FILE = Path(__file__).resolve().parents[4].parent / "eulerpool_credentials.json"


class EulerpoolError(Exception):
    """A request Eulerpool did not answer with data."""


class EulerpoolAuthenticationError(EulerpoolError):
    """401 / 403: missing, invalid or unauthorized API key."""


class EulerpoolNotFound(EulerpoolError):
    """404: unknown security / identifier or no such resource."""


class EulerpoolRateLimitError(EulerpoolError):
    """429: too many requests (after the retries)."""


class EulerpoolResponseError(EulerpoolError):
    """The response is not the JSON the endpoint documents."""


class EulerpoolUnavailable(EulerpoolError):
    """Network failure, timeout or a 5xx status (after the retries)."""


def load_api_key(credentials_path: Optional[str] = None) -> Optional[str]:
    """The API key from the environment or the credentials file, or None."""
    key = os.getenv("EULERPOOL_API_KEY")
    if key:
        return key.strip()
    path = Path(credentials_path or os.getenv("EULERPOOL_CREDENTIALS_FILE") or DEFAULT_CREDENTIALS_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            return (json.load(f).get("api_key") or "").strip() or None
    except (OSError, ValueError):
        return None


def identifier_path(identifier: str) -> str:
    """A security identifier (ticker, ISIN, CUSIP, SEDOL, WKN) as a URL path segment."""
    value = str(identifier or "").strip().upper()
    if not value or "/" in value:
        raise ValueError(f"invalid Eulerpool identifier {identifier!r}")
    return quote(value, safe="")


class EulerpoolClient:
    """GET requests on the Eulerpool API (one at a time, at least min_interval seconds apart)."""

    RETRY_STATUSES = (429, 500, 502, 503, 504)

    def __init__(self, api_key: str, base_url: Optional[str] = None, timeout: float = 60.0,
                 min_interval: float = 0.1, retries: int = 2, backoff: float = 2.0, session=None,
                 sleep=time.sleep, clock=time.monotonic):
        if not api_key:
            raise EulerpoolAuthenticationError("a Eulerpool API key is required")
        self._api_key = api_key
        self.base_url = (base_url or os.getenv("EULERPOOL_BASE_URL") or BASE_URL).rstrip("/")
        self.timeout = timeout
        self.min_interval = min_interval
        self.retries = retries
        self.backoff = backoff
        if session is None:
            import requests
            session = requests.Session()
        self.session = session
        self._sleep = sleep
        self._clock = clock
        self._last_request: Optional[float] = None
        self.requests_made = 0
        self.rate_limit: Dict[str, str] = {}

    @classmethod
    def from_environment(cls, credentials_path: Optional[str] = None, **kwargs) -> Optional["EulerpoolClient"]:
        """A client with the configured key, or None when no key is configured."""
        key = load_api_key(credentials_path)
        return cls(key, **kwargs) if key else None

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _pace(self) -> None:
        if self._last_request is not None:
            wait = self.min_interval - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()

    def _mask(self, text: str) -> str:
        return (text or "")[:200].replace(self._api_key, "***")

    def get(self, path: str, **params) -> Any:
        """The endpoint's decoded JSON (list or object). Raises an EulerpoolError subclass otherwise."""
        params = {k: v for k, v in params.items() if v is not None}
        what = f"{path} {', '.join(f'{k}={v}' for k, v in sorted(params.items()))}".strip()
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        for attempt in range(self.retries + 1):
            self._pace()
            self.requests_made += 1
            try:
                response = self.session.get(self.url(path), params=params, headers=headers, timeout=self.timeout)
            except Exception as e:              # requests' ConnectionError / Timeout, never with the headers
                if attempt < self.retries:
                    self._sleep(self.backoff * (attempt + 1))
                    continue
                raise EulerpoolUnavailable(f"{what}: {type(e).__name__}") from None
            status = getattr(response, "status_code", None)
            self.rate_limit = {k.lower(): v for k, v in (getattr(response, "headers", None) or {}).items()
                               if "ratelimit" in k.lower()}
            if status in self.RETRY_STATUSES and attempt < self.retries:
                retry_after = (getattr(response, "headers", None) or {}).get("retry-after")
                try:
                    wait = float(retry_after) if retry_after else self.backoff * (attempt + 1)
                except ValueError:
                    wait = self.backoff * (attempt + 1)
                logger.warning(f"Eulerpool {what}: HTTP {status}, retry in {wait:.0f}s")
                self._sleep(wait)
                continue
            return self._decode(response, status, what)
        raise EulerpoolUnavailable(f"{what}: no answer")     # not reached

    def _decode(self, response, status, what: str) -> Any:
        text = self._mask(getattr(response, "text", "") or "")
        if status in (401, 403):
            raise EulerpoolAuthenticationError(f"{what}: HTTP {status} {text}")
        if status == 404:
            raise EulerpoolNotFound(f"{what}: HTTP 404 {text}")
        if status == 429:
            raise EulerpoolRateLimitError(f"{what}: HTTP 429 {text}")
        if status is None or status >= 500:
            raise EulerpoolUnavailable(f"{what}: HTTP {status}")
        if status >= 400:
            raise EulerpoolError(f"{what}: HTTP {status} {text}")
        try:
            data = response.json()
        except ValueError:
            raise EulerpoolResponseError(f"{what}: not JSON: {text}") from None
        if isinstance(data, dict) and set(data) == {"error"}:
            raise EulerpoolError(f"{what}: {self._mask(str(data['error']))}")
        if not isinstance(data, (list, dict)):
            raise EulerpoolResponseError(f"{what}: expected a JSON list or object, got {type(data).__name__}")
        return data
