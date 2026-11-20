"""
Frequency — a schedule as a category and a count: every 10 minutes, 2 hours, 1 day, 2 weeks, 3 months.

Token form (what bar_frequency already uses): '10m', '2h', '1d', '2w', '3mo'.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

UNITS: Tuple[str, ...] = ("minutes", "hours", "days", "weeks", "months")
UNIT_LABELS: Dict[str, str] = {"minutes": "Minutes", "hours": "Hourly", "days": "Daily", "weeks": "Weekly",
                               "months": "Monthly"}
_TOKENS: Dict[str, str] = {"minutes": "m", "hours": "h", "days": "d", "weeks": "w", "months": "mo"}
_FROM_TOKEN: Dict[str, str] = {v: k for k, v in _TOKENS.items()}
_SINGULAR: Dict[str, str] = {"minutes": "minute", "hours": "hour", "days": "day", "weeks": "week", "months": "month"}
DAYS_PER: Dict[str, int] = {"days": 1, "weeks": 7, "months": 30}       # calendar days (a month ~ 30)
# the counts offered for each category (any whole number >= 1 is valid)
COUNT_CHOICES: Dict[str, Tuple[int, ...]] = {
    "minutes": (1, 2, 3, 5, 10, 15, 20, 30, 45),
    "hours": (1, 2, 3, 4, 6, 8),
    "days": (1, 2, 3, 4, 5, 10, 14, 15, 21),
    "weeks": (1, 2, 3, 4, 6, 8, 13, 26),
    "months": (1, 2, 3, 4, 6, 12),
}
_TOKEN_RE = re.compile(r"^\s*(\d+)\s*(mo|m|h|d|w)\s*$", re.I)


@dataclass(frozen=True)
class Frequency:
    unit: str
    count: int = 1

    def __post_init__(self):
        if self.unit not in UNITS:
            raise ValueError(f"frequency category must be one of {', '.join(UNITS)}, got {self.unit!r}")
        if not isinstance(self.count, int) or isinstance(self.count, bool) or self.count < 1:
            raise ValueError(f"frequency count must be a whole number >= 1, got {self.count!r}")

    @classmethod
    def of(cls, unit: str, count) -> "Frequency":
        try:
            n = int(str(count).strip())
        except (TypeError, ValueError):
            raise ValueError(f"frequency count must be a whole number, got {count!r}")
        return cls(str(unit or "").strip().lower(), n)

    @classmethod
    def parse(cls, token: Optional[str]) -> Optional["Frequency"]:
        """'10m' / '2h' / '1d' / '2w' / '3mo' -> Frequency (None when empty or not a token)."""
        m = _TOKEN_RE.match(token or "")
        if not m:
            return None
        return cls(_FROM_TOKEN[m.group(2).lower()], int(m.group(1)))

    @classmethod
    def from_minutes(cls, minutes: int) -> "Frequency":
        return cls("hours", minutes // 60) if minutes >= 60 and minutes % 60 == 0 else cls("minutes", int(minutes))

    @classmethod
    def from_days(cls, days: int) -> "Frequency":
        """Calendar days in the largest whole category: 30 -> 1 month, 14 -> 2 weeks, 21 -> 3 weeks, 10 -> 10 days."""
        for unit in ("months", "weeks"):
            if days >= DAYS_PER[unit] and days % DAYS_PER[unit] == 0:
                return cls(unit, days // DAYS_PER[unit])
        return cls("days", int(days))

    @property
    def token(self) -> str:
        return f"{self.count}{_TOKENS[self.unit]}"

    @property
    def minutes(self) -> Optional[int]:
        return {"minutes": self.count, "hours": self.count * 60}.get(self.unit)

    @property
    def days(self) -> Optional[int]:
        return self.count * DAYS_PER[self.unit] if self.unit in DAYS_PER else None

    @property
    def label(self) -> str:
        noun = _SINGULAR[self.unit] if self.count == 1 else self.unit
        return f"every {noun}" if self.count == 1 else f"every {self.count} {noun}"

    def __str__(self) -> str:
        return self.label
