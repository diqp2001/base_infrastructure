"""
Alert delivery (P.08.01): critical trading alerts and session events pushed to the owner's phone through ntfy
(https://ntfy.sh, owner's choice 2026-11-03). The dashboard alone needed someone watching it.

    NtfySender      POST https://ntfy.sh/<topic>; the topic is the only secret (NTFY_TOPIC: environment, else the
                    git-ignored .env.windows). Never raises: a delivery failure is logged and trading goes on.
    AlertNotifier   check(): the critical alerts of monitoring.service.trading_alerts (control DISABLED, blocking
                    discrepancy, order submission UNKNOWN / INTENT) + extra ones from the caller; each one is sent
                    ONCE while it lasts, and again if it comes back after clearing. event(): session start / end /
                    crash.

Messages carry the alert text only — no account number, no credential.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Set

NTFY_SERVER = "https://ntfy.sh"
ENV_FILE = Path(__file__).resolve().parents[4] / ".env.windows"
logger = logging.getLogger(__name__)


def _env_value(name: str, env_file: Optional[Path] = ENV_FILE) -> Optional[str]:
    value = os.environ.get(name)
    if value:
        return value.strip()
    if env_file is not None and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip() == name and val.strip():
                return val.strip()
    return None


def _header(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii")          # HTTP headers: ASCII only


class NtfySender:

    def __init__(self, topic: str, server: str = NTFY_SERVER, timeout: float = 5.0, post: Optional[Callable] = None):
        if not topic:
            raise ValueError("ntfy topic missing")
        self.url = f"{server.rstrip('/')}/{topic}"
        self.timeout = timeout
        self._post = post

    def send(self, title: str, message: str, priority: str = "high", tags: Iterable[str] = ()) -> bool:
        try:
            post = self._post
            if post is None:
                import requests
                post = requests.post
            response = post(self.url, data=message.encode("utf-8"), timeout=self.timeout,
                            headers={"Title": _header(title), "Priority": priority, "Tags": ",".join(tags)})
            ok = 200 <= getattr(response, "status_code", 0) < 300
            if not ok:
                logger.error(f"ntfy: delivery refused ({getattr(response, 'status_code', '?')}): {title}")
            return ok
        except Exception as e:
            logger.error(f"ntfy: delivery failed ({e!r}): {title}")
            return False


def sender_from_env(env_file: Optional[Path] = ENV_FILE) -> Optional[NtfySender]:
    """NtfySender from NTFY_TOPIC (+ optional NTFY_SERVER); None when no topic is configured."""
    topic = _env_value("NTFY_TOPIC", env_file)
    if not topic:
        return None
    return NtfySender(topic, server=_env_value("NTFY_SERVER", env_file) or NTFY_SERVER)


class AlertNotifier:

    def __init__(self, sender: NtfySender, source: str, state: Optional[Callable[[], Optional[Dict[str, Any]]]] = None,
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.sender = sender
        self.source = source                      # e.g. "STM_10M_BANKS paper"
        self.state = state                        # () -> monitoring trading_state
        self.clock = clock
        self._active: Set[str] = set()

    def check(self, extra: Iterable[str] = ()) -> int:
        """Send the critical alerts that were not active at the previous check. Returns how many were sent."""
        from src.application.services.monitoring.service import trading_alerts
        try:
            state = self.state() if self.state is not None else None
            messages = [a["message"] for a in trading_alerts(state or {}, self.clock()) if a["severity"] == "critical"]
        except Exception as e:
            logger.error(f"alert check failed: {e!r}")
            messages = [f"alert check failed: {e!r}"]
        messages += list(extra)
        delivered: Set[str] = set()
        for message in dict.fromkeys(messages):                 # each distinct message once, in order
            if message in self._active:
                delivered.add(message)                          # still active: already sent
            elif self.sender.send(f"{self.source}: CRITICAL", message, priority="urgent", tags=("rotating_light",)):
                delivered.add(message)
        sent = len(delivered - self._active)
        # cleared alerts drop out (sent again if they come back); a failed delivery is retried at the next check
        self._active = delivered
        return sent

    def event(self, what: str, message: str = "", priority: str = "default") -> bool:
        return self.sender.send(f"{self.source}: {what}", message or what, priority=priority)
