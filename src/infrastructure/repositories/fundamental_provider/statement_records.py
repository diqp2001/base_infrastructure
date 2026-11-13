"""
Helpers shared by the financial statement providers (FMP, Eulerpool): parsing of the providers' numbers and dates,
and the point-in-time cleanup of a statement's history (StatementRecord, see
src/domain/ports/factor/financial_statement_source_port.py).
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.domain.ports.factor.financial_statement_source_port import StatementRecord

logger = logging.getLogger(__name__)


def number(value: Any) -> Optional[float]:
    """A finite float, or None (None, booleans, text, NaN, infinity)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def parse_date(value: Any) -> Optional[date]:
    """'2025-09-27', '2025-09-27T00:00:00.000Z', ... -> date, else None."""
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


def parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            continue
    return None


def deduplicate(records: List[StatementRecord], provider: str = "") -> List[StatementRecord]:
    """One record per moment, in publication order, each newer than the previous one:

    * one record per fiscal period: the first published;
    * two periods published at the same moment: the later period only (one value per series and moment);
    * a period first published after a LATER period (e.g. a comparative figure seen only in a later filing): dropped,
      or the series would step back in time - read as of a date, it must give the latest period known then.
    Each drop is logged."""
    by_period: Dict[tuple, StatementRecord] = {}
    for r in records:
        key = (r.fiscal_year, r.period, r.period_end)
        kept = by_period.get(key)
        if kept is not None:
            logger.warning(f"{provider} {r.statement} {r.symbol} {r.period} {r.period_end}: duplicate period - "
                           f"keeping the first published ({min(kept.available_at, r.available_at)})")
            if r.available_at >= kept.available_at:
                continue
        by_period[key] = r
    by_stamp: Dict[datetime, StatementRecord] = {}
    for r in by_period.values():
        kept = by_stamp.get(r.available_at)
        if kept is not None:
            later = max((kept, r), key=lambda x: x.period_end)
            logger.warning(f"{provider} {r.statement} {r.symbol}: periods {kept.period_end} and {r.period_end} "
                           f"published at the same moment {r.available_at} - keeping {later.period_end}")
            r = later
        by_stamp[r.available_at] = r
    out, latest = [], None
    for r in sorted(by_stamp.values(), key=lambda x: x.available_at):
        if latest is not None and r.period_end <= latest:
            logger.warning(f"{provider} {r.statement} {r.symbol}: period {r.period_end} first published at "
                           f"{r.available_at}, after the later period {latest} - dropped")
            continue
        out.append(r)
        latest = r.period_end
    return out
