"""
Outcome of one IBKR historical-data request (reqHistoricalData), classified from the evidence IBKR gives:
bars received, historicalDataEnd, and the error callback's code + message for that request id.

Status
  complete      historicalDataEnd received, no error for the request, at least one bar
  empty         historicalDataEnd received, no error, zero bars (IBKR had nothing for the window)
  failed        IBKR reported an error for the request (bars received before it are NOT a complete answer)
  timeout       neither historicalDataEnd nor an error within the timeout
  not_sent      no connection: nothing was requested

Failure kinds (from the IBKR error; never guessed beyond what the message says)
  permission    the message states missing market-data permissions / subscription (e.g. 162 "No market data
                permissions for ISLAND STK ... requires additional subscription for API")
  pacing        162 "pacing violation"
  no_data       162 "HMDS query returned no data" / "no data"
  no_security   200 no security definition (contract not found / ambiguous)
  invalid       321 malformed request
  transient     errors worth a bounded retry (ibkr_settings.TRANSIENT_HISTORY_ERRORS: 322, 366, 1100, 2103, ...)
  other         any other error: code and message kept verbatim

Only `transient`, `pacing` and `timeout` are retried. A permission failure is final: retrying cannot help.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

COMPLETE, EMPTY, FAILED, TIMEOUT, NOT_SENT = "complete", "empty", "failed", "timeout", "not_sent"

# IBKR codes that are notices, not request errors: they must not end a historical request
WARNING_CODES = frozenset(range(2100, 2200)) | {10167}
from .ibkr_settings import TRANSIENT_HISTORY_ERRORS as TRANSIENT_CODES   # one list (BI-029): 322, 366, 1100, ...
QUOTE_TYPES = frozenset({"MIDPOINT", "BID", "ASK", "BID_ASK"})

_PERMISSION = re.compile(r"no market data permissions|requires additional subscription|not subscribed|"
                         r"no permission", re.IGNORECASE)


def is_warning(code: int) -> bool:
    return code in WARNING_CODES


def classify_error(code: Optional[int], message: str = "") -> Optional[str]:
    if code is None:
        return None
    text = message or ""
    if code == 162 and "pacing" in text.lower():
        return "pacing"
    if _PERMISSION.search(text):
        return "permission"
    if code == 162 and ("no data" in text.lower() or "returned no data" in text.lower()):
        return "no_data"
    if code == 200:
        return "no_security"
    if code == 321:
        return "invalid"
    if code in TRANSIENT_CODES:
        return "transient"
    return "other"


@dataclass
class HistoryResult:
    req_id: Optional[int]
    status: str
    what_to_show: str = ""
    bars: List[dict] = field(default_factory=list)
    error_code: Optional[int] = None
    error_message: str = ""
    elapsed: float = 0.0
    partial_bars: int = 0                 # bars received before an error / timeout (discarded)

    @property
    def failure(self) -> Optional[str]:
        if self.status == TIMEOUT:
            return "timeout"
        if self.status == FAILED:
            return classify_error(self.error_code, self.error_message)
        return None

    @property
    def ok(self) -> bool:
        return self.status in (COMPLETE, EMPTY)

    @property
    def retryable(self) -> bool:
        return self.failure in ("transient", "pacing", "timeout")

    def explanation(self) -> str:
        """One actionable line for the log; states only what IBKR's answer supports."""
        if self.status == COMPLETE:
            return f"{len(self.bars)} bars"
        if self.status == EMPTY:
            return "IBKR completed the request with zero bars (no data in the window)"
        if self.status == NOT_SENT:
            return "not connected: nothing was requested"
        if self.status == TIMEOUT:
            return ("no historicalDataEnd and no error within the timeout"
                    + (f" ({self.partial_bars} partial bars discarded)" if self.partial_bars else ""))
        text = f"IBKR error {self.error_code}: {self.error_message}"
        if self.failure == "permission":
            exchange = re.search(r"permissions for ([A-Z0-9.]+ [A-Z]+)", self.error_message or "")
            where = exchange.group(1) if exchange else "this instrument"
            hint = (f" — IBKR states the API session has no market-data permission for {where}"
                    f" {self.what_to_show} data.")
            if self.what_to_show in QUOTE_TYPES:
                hint += (" Quote-based types (MIDPOINT / BID / ASK / BID_ASK) need a quote subscription for that"
                         " exchange even when TRADES history is returned; check Client Portal > Market Data"
                         " Subscriptions (and that the subscription is shared with the API session).")
            text += hint
        if self.partial_bars:
            text += f" ({self.partial_bars} bars received before the error were discarded)"
        return text
