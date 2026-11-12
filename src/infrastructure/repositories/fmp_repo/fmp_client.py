"""
Financial Modeling Prep HTTP client (the /stable API).

Holds the API key, the request pacing and the provider's error statuses; returns the decoded JSON rows. It knows no
domain entity: the repositories in this package normalize the rows.

Key: FMP_API_KEY in the environment, else the 'api_key' of a JSON credentials file (FMP_CREDENTIALS_FILE, default
FPM_credentials.json next to the repository folder - the file the FMP API service has used). The key is a query
parameter of every request; it never appears in an error message or a log line.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://financialmodelingprep.com/stable"
DEFAULT_CREDENTIALS_FILE = Path(__file__).resolve().parents[4].parent / "FPM_credentials.json"


class FMPError(Exception):
    """A request FMP did not answer with data."""


class FMPAuthenticationError(FMPError):
    """401 / 403: missing or invalid API key."""


class FMPSubscriptionError(FMPError):
    """402: the endpoint, the symbol or a parameter value (e.g. limit > 5) is outside the subscription."""


class FMPRateLimitError(FMPError):
    """429: too many requests."""


class FMPResponseError(FMPError):
    """The response is not the JSON list the endpoint documents."""


class FMPUnavailable(FMPError):
    """Network failure, timeout or a 5xx status."""


def load_api_key(credentials_path: Optional[str] = None) -> Optional[str]:
    """The API key from the environment or the credentials file, or None."""
    key = os.getenv("FMP_API_KEY")
    if key:
        return key.strip()
    path = Path(credentials_path or os.getenv("FMP_CREDENTIALS_FILE") or DEFAULT_CREDENTIALS_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            return (json.load(f).get("api_key") or "").strip() or None
    except (OSError, ValueError):
        return None


class FMPClient:
    """GET requests on the FMP /stable API (one request at a time, at least min_interval seconds apart)."""

    def __init__(self, api_key: str, base_url: str = BASE_URL, timeout: float = 30.0, min_interval: float = 0.25,
                 session=None, sleep=time.sleep, clock=time.monotonic):
        if not api_key:
            raise FMPAuthenticationError("an FMP API key is required")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.min_interval = min_interval
        if session is None:
            import requests
            session = requests.Session()
        self.session = session
        self._sleep = sleep
        self._clock = clock
        self._last_request: Optional[float] = None
        self.requests_made = 0

    @classmethod
    def from_environment(cls, credentials_path: Optional[str] = None, **kwargs) -> Optional["FMPClient"]:
        """A client with the configured key, or None when no key is configured."""
        key = load_api_key(credentials_path)
        return cls(key, **kwargs) if key else None

    def url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _pace(self) -> None:
        if self._last_request is not None:
            wait = self.min_interval - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()

    @staticmethod
    def _describe(endpoint: str, params: Dict[str, Any]) -> str:
        return f"{endpoint} {', '.join(f'{k}={v}' for k, v in sorted(params.items()))}"

    def get(self, endpoint: str, **params) -> List[Dict[str, Any]]:
        """The endpoint's rows (a JSON list; [] when FMP has no data). Raises an FMPError subclass otherwise."""
        what = self._describe(endpoint, params)
        self._pace()
        self.requests_made += 1
        try:
            response = self.session.get(self.url(endpoint), params={**params, "apikey": self._api_key},
                                        timeout=self.timeout)
        except Exception as e:                      # requests' ConnectionError / Timeout, without the URL (it has the key)
            raise FMPUnavailable(f"{what}: {type(e).__name__}") from None
        status = getattr(response, "status_code", None)
        text = (getattr(response, "text", "") or "")[:200].replace(self._api_key, "***")
        if status in (401, 403):
            raise FMPAuthenticationError(f"{what}: HTTP {status} {text}")
        if status == 402:
            raise FMPSubscriptionError(f"{what}: HTTP 402 {text}")
        if status == 429:
            raise FMPRateLimitError(f"{what}: HTTP 429 {text}")
        if status is None or status >= 500:
            raise FMPUnavailable(f"{what}: HTTP {status}")
        if status >= 400:
            raise FMPError(f"{what}: HTTP {status} {text}")
        try:
            data = response.json()
        except ValueError:
            raise FMPResponseError(f"{what}: not JSON: {text}") from None
        if isinstance(data, dict) and ("Error Message" in data or "error" in data):
            raise FMPError(f"{what}: {str(data.get('Error Message') or data.get('error'))[:200]}")
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise FMPResponseError(f"{what}: expected a list of objects, got {type(data).__name__}")
        return data
