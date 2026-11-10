"""
src/domain/entities/factor/finance/financial_assets/derivatives/option/share_option_factor.py

ShareOptionFactor - parent of the factors of options on shares (CompanyShareOptionFactor, the ETF share option
factors): the option choice and quote rules they share, mirroring the ShareOption entity parent.

Option choice: the expiry nearest a target number of days within [min_dte, max_dte], the strike nearest the
underlying price (min |K / S - 1|), the standard trading class of a chain; a departure from the reference expiry is
returned as an explicit exception, never substituted silently.
Quote rules: the price an option is traded at must be quoted (sold: its bid; bought: its ask), live (not frozen /
delayed unless allowed) and no older than max_age_seconds; volume / open interest minimums are optional. Each check
returns the reasons an option is unusable; empty = usable.

The rules read plain objects (a chain: multiplier / trading_class / expirations / strikes; a quote: bid / ask / error /
market_data_type / quote_time / volume; an option quote: quote / open_interest) and take their settings as arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, List, Optional, Sequence, Tuple

from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


@dataclass(frozen=True)
class ExpiryChoice:
    expiry: Optional[date]
    exception: Optional[str] = None          # why it is not the reference expiry / why there is none


class ShareOptionFactor(OptionFactor):
    """Factor of an option whose underlying is a share (company or ETF)."""

    STANDARD_MULTIPLIER = 100.0
    LIVE = 1                                  # IBKR market data type of a live quote
    SELL, BUY = "sell", "buy"

    def __init__(self, name: str, group: str, subgroup: Optional[str] = None, frequency: Optional[str] = None,
                 data_type: Optional[str] = None, source: Optional[str] = None, definition: Optional[str] = None,
                 factor_id: Optional[int] = None):
        super().__init__(name=name, group=group, subgroup=subgroup, frequency=frequency, data_type=data_type,
                         source=source, definition=definition, factor_id=factor_id)

    # ---- option choice ----
    @classmethod
    def standard_chain(cls, chains: Sequence[Any]) -> Tuple[Optional[Any], List[str]]:
        """The chain to trade: multiplier 100 with the most expirations (adjusted classes after corporate actions
        carry other multipliers / deliverables). Returns the notes about the classes left out."""
        if not chains:
            return None, ["no listed options"]
        standard = [c for c in chains if c.multiplier == cls.STANDARD_MULTIPLIER]
        pool = standard or list(chains)
        chosen = max(pool, key=lambda c: (len(c.expirations), len(c.strikes)))
        notes = [f"trading class {c.trading_class} x{c.multiplier:g} not used" for c in chains if c is not chosen]
        if not standard:
            notes.append(f"no x100 class: {chosen.trading_class} x{chosen.multiplier:g} used")
        return chosen, notes

    @staticmethod
    def eligible_expiries(expirations: Sequence[date], day: date, min_dte: int, max_dte: int) -> List[date]:
        return [e for e in expirations if min_dte <= (e - day).days <= max_dte]

    @classmethod
    def select_expiry(cls, expirations: Sequence[date], day: date, target_dte: int, min_dte: int,
                      max_dte: int) -> Optional[date]:
        """Nearest target_dte inside [min_dte, max_dte]; a tie goes to the earlier expiry."""
        candidates = cls.eligible_expiries(expirations, day, min_dte, max_dte)
        if not candidates:
            return None
        return min(candidates, key=lambda e: (abs((e - day).days - target_dte), e))

    @classmethod
    def select_common_expiry(cls, etf_expirations: Sequence[date], constituent_expirations: Sequence[Sequence[date]],
                             day: date, target_dte: int, min_dte: int, max_dte: int) -> Optional[date]:
        """The ETF expiry in [min_dte, max_dte] that the most constituents also list (many stocks list only the
        monthly expiries while the ETF lists weeklies), then the nearest target_dte, then the earlier."""
        candidates = cls.eligible_expiries(etf_expirations, day, min_dte, max_dte)
        if not candidates:
            return None
        listed = [set(e) for e in constituent_expirations]
        return min(candidates, key=lambda e: (-sum(e in s for s in listed), abs((e - day).days - target_dte), e))

    @staticmethod
    def common_expiries(etf_expirations: Sequence[date], constituent_expirations: Sequence[Sequence[date]],
                        day: date, min_dte: int, max_dte: int) -> List[date]:
        """The ETF expiries in [min_dte, max_dte] that every constituent also lists."""
        listed = [set(e) for e in constituent_expirations]
        return [e for e in sorted(etf_expirations)
                if min_dte <= (e - day).days <= max_dte and all(e in s for s in listed)]

    @classmethod
    def constituent_expiry(cls, expirations: Sequence[date], etf_expiry: date, day: date,
                           require_same_expiration: bool, min_dte: int, max_dte: int) -> ExpiryChoice:
        """The ETF's expiry when listed; otherwise none (same expiration required) or the nearest eligible one,
        each with the exception spelled out."""
        if etf_expiry in expirations:
            return ExpiryChoice(etf_expiry)
        if require_same_expiration:
            return ExpiryChoice(None, f"no {etf_expiry} expiry (same expiration required)")
        candidates = cls.eligible_expiries(expirations, day, min_dte, max_dte)
        if not candidates:
            return ExpiryChoice(None, f"no expiry within {min_dte}-{max_dte} days")
        chosen = min(candidates, key=lambda e: (abs((e - etf_expiry).days), e))
        return ExpiryChoice(chosen, f"expiry {chosen} instead of the ETF's {etf_expiry}")

    @staticmethod
    def select_atm_strike(strikes: Sequence[float], spot: float) -> Optional[float]:
        """Strike nearest the spot by |K / S - 1|; a tie goes to the lower strike."""
        if not strikes or not spot or spot <= 0:
            return None
        return min(strikes, key=lambda k: (abs(k / spot - 1.0), k))

    # ---- quote rules ----
    @classmethod
    def freshness_problems(cls, quote: Any, now: datetime, max_age_seconds: float,
                           allow_frozen: bool = False) -> List[str]:
        problems = []
        if quote.error:
            problems.append(f"quote error {quote.error}")
        if quote.market_data_type not in (None, cls.LIVE) and not allow_frozen:
            kind = {2: "frozen", 3: "delayed", 4: "delayed frozen"}.get(quote.market_data_type,
                                                                        str(quote.market_data_type))
            problems.append(f"{kind} quote (market closed or no live data)")
        if quote.quote_time is None:
            problems.append("no quote time")
        elif (now - quote.quote_time).total_seconds() > max_age_seconds:
            problems.append(f"quote {(now - quote.quote_time).total_seconds():.0f}s old (max {max_age_seconds:g}s)")
        return problems

    @classmethod
    def quality_problems(cls, option: Any, now: datetime, side: str, max_age_seconds: float,
                         allow_frozen: bool = False) -> List[str]:
        """side: SELL (its bid is the price) or BUY (its ask is the price). The other side, the spread and the
        greeks are information only."""
        q = option.quote
        problems = []
        if side == cls.SELL and not (q.bid is not None and q.bid > 0):
            problems.append(f"no bid (bid {q.bid})")
        if side == cls.BUY and not (q.ask is not None and q.ask > 0):
            problems.append(f"no ask (ask {q.ask})")
        return problems + cls.freshness_problems(q, now, max_age_seconds, allow_frozen)

    @staticmethod
    def liquidity_problems(option: Any, min_volume: float, min_open_interest: float) -> List[str]:
        """0 = no minimum. An unknown open interest fails a positive minimum."""
        q = option.quote
        problems = []
        if min_volume > 0 and (q.volume or 0) < min_volume:
            problems.append(f"volume {q.volume} < {min_volume:g}")
        if min_open_interest > 0 and (option.open_interest is None or option.open_interest < min_open_interest):
            problems.append(f"open interest {option.open_interest} < {min_open_interest:g}")
        return problems
