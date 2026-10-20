"""
Quote validation and data freshness (BI-027) — pure domain. Produces ValidationResults (observation_quality) and
the status they imply; the provenance of a stored value records them (BI-025).

  validate_bar_value(value, is_price)          finite number; positive when it is a price
  validate_quote(quote, policy, decision_time)  positive bid / ask, no missing side or zero placeholder, not crossed,
                                                spread within limits, not stale
  check_price_move(previous, current, policy)  a large move is FLAGGED (passed, with a note) — never rejected:
                                                large moves happen; downstream rules decide
  status_from(validations)                      INVALID when any validation failed, else VALID

QuotePolicy holds the configurable limits (spread, staleness, move threshold); different instruments / uses get
different policies (e.g. a looser spread for illiquid long-dated options). Freshness of stored BARS uses the trading
calendar (bar_calendar.bar_is_current, enforced on read); a quote's freshness is its age at the decision time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.entities.factor.observation_quality import ObservationStatus, ValidationResult


@dataclass(frozen=True)
class Quote:
    bid: Optional[float]
    ask: Optional[float]
    observed_at: datetime

    @property
    def mid(self) -> Optional[float]:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2.0


@dataclass(frozen=True)
class QuotePolicy:
    max_spread_bps: Optional[float] = None          # relative spread (ask - bid) / mid, in basis points
    max_spread_abs: Optional[float] = None          # absolute spread in price units
    max_age: Optional[timedelta] = None             # quote age at the decision time
    large_move: Optional[float] = None              # relative move vs the previous valid value that is flagged
    name: str = "quote-policy"


INTRADAY_LIQUID = QuotePolicy(max_spread_bps=50, max_age=timedelta(minutes=15), large_move=0.10, name="intraday-liquid")
DAILY = QuotePolicy(max_spread_bps=200, max_age=timedelta(days=1), large_move=0.20, name="daily")
ILLIQUID_OPTION = QuotePolicy(max_spread_bps=2000, max_age=timedelta(days=1), large_move=0.50, name="illiquid-option")


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate_bar_value(value, is_price: bool) -> List[ValidationResult]:
    """A stored bar field: a finite number, and > 0 when it is a price (0 is IBKR's placeholder for no trade)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return [ValidationResult("numeric", False, f"value {value!r} is not a number")]
    results = [ValidationResult("finite", math.isfinite(number), "" if math.isfinite(number) else
                                f"value {value!r} is not finite")]
    if is_price:
        ok = math.isfinite(number) and number > 0
        results.append(ValidationResult("positive_price", ok, "" if ok else f"price {number} <= 0"))
    return results


def validate_quote(quote: Quote, policy: QuotePolicy, decision_time: Optional[datetime] = None) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    for side, price in (("bid", quote.bid), ("ask", quote.ask)):
        if price is None:
            results.append(ValidationResult(f"{side}_present", False, f"missing {side}"))
        elif not _finite(price) or price <= 0:
            results.append(ValidationResult(f"{side}_positive", False, f"{side} {price!r} is not a positive price"))
        else:
            results.append(ValidationResult(f"{side}_positive", True))
    sides_ok = all(r.passed for r in results)
    if sides_ok:
        crossed = quote.bid > quote.ask
        results.append(ValidationResult("not_crossed", not crossed,
                                        f"crossed: bid {quote.bid} > ask {quote.ask}" if crossed else ""))
        if not crossed:
            spread = quote.ask - quote.bid
            if policy.max_spread_abs is not None:
                ok = spread <= policy.max_spread_abs
                results.append(ValidationResult("max_spread_abs", ok,
                                                "" if ok else f"spread {spread:.4g} > {policy.max_spread_abs}"))
            if policy.max_spread_bps is not None:
                bps = spread / quote.mid * 10_000
                ok = bps <= policy.max_spread_bps
                results.append(ValidationResult("max_spread_bps", ok,
                                                "" if ok else f"spread {bps:.0f} bps > {policy.max_spread_bps} bps"))
    if decision_time is not None and policy.max_age is not None:
        age = decision_time - quote.observed_at
        ok = timedelta(0) <= age <= policy.max_age
        reason = ("" if ok else f"observed after the decision time ({quote.observed_at} > {decision_time})"
                  if age < timedelta(0) else f"stale: {age} old > {policy.max_age}")
        results.append(ValidationResult("fresh", ok, reason))
    return results


def check_price_move(previous: Optional[float], current: float, policy: QuotePolicy) -> List[ValidationResult]:
    """A move larger than policy.large_move is flagged (passed=True, reason says why) — a legitimate large move must
    not be rejected; consumers may still require no flag."""
    if previous is None or policy.large_move is None or not _finite(previous) or previous <= 0 or not _finite(current):
        return []
    move = abs(current / previous - 1.0)
    if move > policy.large_move:
        return [ValidationResult("large_move", True, f"flag: moved {move:.1%} vs previous {previous} "
                                                     f"(threshold {policy.large_move:.0%})")]
    return [ValidationResult("large_move", True)]


def status_from(validations) -> ObservationStatus:
    return ObservationStatus.INVALID if any(not v.passed for v in validations) else ObservationStatus.VALID
