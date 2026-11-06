"""
P.04 ATM option selection (pure): the expiry nearest TARGET_DTE within [MIN_DTE, MAX_DTE], the strike nearest the
underlying price (min |K / S - 1|), the standard trading class of a chain. Every departure from the ETF's expiry is
returned as an explicit exception, never substituted silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Sequence, Tuple

from src.domain.entities.finance.dispersion.option_data import OptionChain
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig

STANDARD_MULTIPLIER = 100.0


@dataclass(frozen=True)
class ExpiryChoice:
    expiry: Optional[date]
    exception: Optional[str] = None          # why it is not the ETF's expiry / why there is none


def standard_chain(chains: Sequence[OptionChain]) -> Tuple[Optional[OptionChain], List[str]]:
    """The chain to trade: multiplier 100 with the most expirations (adjusted classes after corporate actions
    carry other multipliers / deliverables). Returns the notes about the classes left out."""
    if not chains:
        return None, ["no listed options"]
    standard = [c for c in chains if c.multiplier == STANDARD_MULTIPLIER]
    pool = standard or list(chains)
    chosen = max(pool, key=lambda c: (len(c.expirations), len(c.strikes)))
    notes = [f"trading class {c.trading_class} x{c.multiplier:g} not used" for c in chains if c is not chosen]
    if not standard:
        notes.append(f"no x100 class: {chosen.trading_class} x{chosen.multiplier:g} used")
    return chosen, notes


def eligible_expiries(expirations: Sequence[date], screening_date: date,
                      config: DispersionScreenConfig) -> List[date]:
    return [e for e in expirations if config.min_dte <= (e - screening_date).days <= config.max_dte]


def select_expiry(expirations: Sequence[date], screening_date: date, config: DispersionScreenConfig) -> Optional[date]:
    """Nearest TARGET_DTE inside [MIN_DTE, MAX_DTE]; a tie goes to the earlier expiry."""
    candidates = eligible_expiries(expirations, screening_date, config)
    if not candidates:
        return None
    return min(candidates, key=lambda e: (abs((e - screening_date).days - config.target_dte), e))


def select_common_expiry(etf_expirations: Sequence[date], constituent_expirations: Sequence[Sequence[date]],
                         screening_date: date, config: DispersionScreenConfig) -> Optional[date]:
    """The ETF expiry in [MIN_DTE, MAX_DTE] that the most constituents also list (many stocks list only the monthly
    expiries while the ETF lists weeklies), then the nearest TARGET_DTE, then the earlier."""
    candidates = eligible_expiries(etf_expirations, screening_date, config)
    if not candidates:
        return None
    listed = [set(e) for e in constituent_expirations]
    return min(candidates, key=lambda e: (-sum(e in s for s in listed),
                                          abs((e - screening_date).days - config.target_dte), e))


def common_expiries(etf_expirations: Sequence[date], constituent_expirations: Sequence[Sequence[date]],
                    screening_date: date, min_dte: int, max_dte: int) -> List[date]:
    """The ETF expiries in [min_dte, max_dte] that every constituent also lists (the maturities view)."""
    listed = [set(e) for e in constituent_expirations]
    return [e for e in sorted(etf_expirations)
            if min_dte <= (e - screening_date).days <= max_dte and all(e in s for s in listed)]


def constituent_expiry(expirations: Sequence[date], etf_expiry: date, screening_date: date,
                       config: DispersionScreenConfig) -> ExpiryChoice:
    """The ETF's expiry when listed; otherwise none (REQUIRE_SAME_EXPIRATION) or the nearest eligible one,
    each with the exception spelled out."""
    if etf_expiry in expirations:
        return ExpiryChoice(etf_expiry)
    if config.require_same_expiration:
        return ExpiryChoice(None, f"no {etf_expiry} expiry (same expiration required)")
    candidates = eligible_expiries(expirations, screening_date, config)
    if not candidates:
        return ExpiryChoice(None, f"no expiry within {config.min_dte}-{config.max_dte} days")
    chosen = min(candidates, key=lambda e: (abs((e - etf_expiry).days), e))
    return ExpiryChoice(chosen, f"expiry {chosen} instead of the ETF's {etf_expiry}")


def select_atm_strike(strikes: Sequence[float], spot: float) -> Optional[float]:
    """Strike nearest the spot by |K / S - 1|; a tie goes to the lower strike."""
    if not strikes or not spot or spot <= 0:
        return None
    return min(strikes, key=lambda k: (abs(k / spot - 1.0), k))
