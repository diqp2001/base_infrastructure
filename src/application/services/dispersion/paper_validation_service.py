"""
P.11 read-only paper validation: quote every leg of the best priced candidates again, some minutes after the screen,
and record whether the screened prices would still have filled. Market data only (OptionMarketDataPort: streaming
quotes, no snapshots); no order code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Callable, List, Optional, Sequence

from src.application.services.dispersion.dispersion_screening_service import Candidate
from src.domain.ports.finance.dispersion.option_market_data_port import OptionMarketDataPort


@dataclass
class Validation:
    etf: str
    screened_status: str
    screened_at: Optional[datetime]
    checked_at: datetime
    screened_net_premium: float
    check: FillCheck

    @property
    def requoted_net_premium(self) -> Optional[float]:
        s = self.check.slippage
        return None if s is None else self.screened_net_premium - s

    def row(self) -> dict:
        def r(x, n=2):
            return None if x is None else round(float(x), n)
        return {
            'etf': self.etf, 'screened_status': self.screened_status,
            'screened_at': str(self.screened_at) if self.screened_at else None, 'checked_at': str(self.checked_at),
            'screened_net_premium': r(self.screened_net_premium), 'requoted_net_premium': r(self.requoted_net_premium),
            'slippage': r(self.check.slippage), 'legs': len(self.check.legs), 'legs_quoted': len(self.check.quoted),
            'legs_would_fill': self.check.legs_filled, 'all_legs_would_fill': self.check.all_fill,
            'leg_checks': [{
                'symbol': c.leg.symbol, 'side': c.leg.side, 'contracts': c.leg.contracts,
                'screened_price': c.leg.screened_price, 'bid': c.bid, 'ask': c.ask,
                'market_data_type': c.market_data_type, 'would_fill': c.would_fill, 'slippage': r(c.slippage),
                'problem': c.problem,
            } for c in self.check.legs],
        }


def priced(candidates: Sequence[Candidate]) -> List[Candidate]:
    """Candidates with an executable sizing and premium (opportunities first: the screen's ranking)."""
    return [c for c in candidates if c.sizing is not None and c.premium is not None and c.etf_option is not None]


class PaperValidationService:

    def __init__(self, market_data: OptionMarketDataPort, require_live: bool = True,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.md = market_data
        self.require_live = require_live
        self.now = now

    def validate(self, candidates: Sequence[Candidate], screening_date: date, top: int = 5) -> List[Validation]:
        out = []
        for c in priced(candidates)[:top]:
            legs = [(c.etf_option.contract, LegToCheck(c.etf, "sell", c.sizing.etf_contracts,
                                                       c.etf_option.contract.multiplier, c.etf_option.quote.bid))]
            for r in c.constituents:
                q = c.sizing.positions.get(r.symbol)
                if q and r.option is not None:
                    legs.append((r.option.contract, LegToCheck(r.symbol, "buy", q, r.option.contract.multiplier,
                                                               r.option.quote.ask)))
            quotes = self.md.option_quotes([spec for spec, _ in legs], screening_date)
            checks = []
            for spec, leg in legs:
                oq = quotes.get(spec.key)
                quote = oq.quote if oq else None
                checks.append(check_leg(leg, quote.bid if quote else None, quote.ask if quote else None,
                                        quote.market_data_type if quote else None, self.require_live))
            out.append(Validation(c.etf, c.status, c.screened_at, self.now(), c.premium.net_premium,
                                  fill_check(checks)))
        return out


# ---- fill check: would each leg fill at its quoted price? ----

LIVE = 1                          # IBKR market data type of a live quote


@dataclass(frozen=True)
class LegToCheck:
    symbol: str
    side: str                        # "sell" (the ETF call) | "buy" (a constituent call)
    contracts: float
    multiplier: float
    screened_price: float            # the bid sold / the ask bought at the screen


@dataclass
class LegCheck:
    leg: LegToCheck
    bid: Optional[float]
    ask: Optional[float]
    market_data_type: Optional[int]
    problem: Optional[str] = None    # no two-sided quote / not live

    @property
    def executable_price(self) -> Optional[float]:
        return self.bid if self.leg.side == "sell" else self.ask

    @property
    def would_fill(self) -> bool:
        p = self.executable_price
        if self.problem or p is None:
            return False
        return p >= self.leg.screened_price if self.leg.side == "sell" else p <= self.leg.screened_price

    @property
    def slippage(self) -> Optional[float]:
        """Dollars against us vs the screened price (positive = worse)."""
        p = self.executable_price
        if self.problem or p is None:
            return None
        per_share = self.leg.screened_price - p if self.leg.side == "sell" else p - self.leg.screened_price
        return per_share * self.leg.contracts * self.leg.multiplier


@dataclass
class FillCheck:
    legs: List[LegCheck] = field(default_factory=list)

    @property
    def quoted(self) -> List[LegCheck]:
        return [c for c in self.legs if c.problem is None]

    @property
    def complete(self) -> bool:
        return bool(self.legs) and len(self.quoted) == len(self.legs)

    @property
    def legs_filled(self) -> int:
        return sum(1 for c in self.legs if c.would_fill)

    @property
    def all_fill(self) -> bool:
        return self.complete and self.legs_filled == len(self.legs)

    @property
    def slippage(self) -> Optional[float]:
        """Total slippage; None when a leg has no usable quote (never a partial total presented as complete)."""
        return sum(c.slippage for c in self.legs) if self.complete else None


def check_leg(leg: LegToCheck, bid: Optional[float], ask: Optional[float], market_data_type: Optional[int],
              require_live: bool = True) -> LegCheck:
    problem = None
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        problem = f"no two-sided quote (bid {bid}, ask {ask})"
    elif require_live and market_data_type != LIVE:
        problem = f"quote not live (market data type {market_data_type})"
    return LegCheck(leg, bid, ask, market_data_type, problem)


def fill_check(checks: Sequence[LegCheck]) -> FillCheck:
    return FillCheck(list(checks))
