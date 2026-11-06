"""
P.11 read-only paper validation: quote every leg of the best priced candidates again, some minutes after the screen,
and record whether the screened prices would still have filled. Market data only (OptionMarketDataPort: streaming
quotes, no snapshots); no order code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, List, Optional, Sequence

from src.application.services.dispersion.dispersion_screening_service import Candidate
from src.domain.entities.finance.dispersion.fill_check import FillCheck, LegToCheck, check_leg, fill_check
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
