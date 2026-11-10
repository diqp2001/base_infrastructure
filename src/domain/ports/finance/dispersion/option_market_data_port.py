"""Port of the dispersion screener's option market data. Every call takes the screening date; a source without
history for that date raises HistoricalDataUnavailable (no silent use of today's data for a past date)."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Optional, Sequence

from src.domain.ports.finance.dispersion.option_data import (
    OptionChain, OptionContractSpec, OptionQuote, Underlying, UnderlyingQuote,
)


class HistoricalDataUnavailable(RuntimeError):
    pass


class MarketDataUnavailable(RuntimeError):
    """The source did not answer (timeout, lost connection): no answer, never to be read as "not found"."""


class OptionMarketDataPort(ABC):

    @abstractmethod
    def resolve_underlyings(self, symbols: Sequence[str], screening_date: date) -> Dict[str, Optional[Underlying]]:
        """Each symbol as a tradeable US-listed share (None: not found / not tradeable)."""

    @abstractmethod
    def option_chains(self, underlying: Underlying, screening_date: date) -> List[OptionChain]:
        """The listed option trading classes of an underlying (empty: no listed options)."""

    @abstractmethod
    def listed_strikes(self, chain: OptionChain, expiry: date, right: str, screening_date: date) -> Sequence[float]:
        """Strikes actually listed for one expiry (a chain's strikes are the union over all its expiries)."""

    @abstractmethod
    def underlying_quotes(self, underlyings: Sequence[Underlying], screening_date: date) -> Dict[str, UnderlyingQuote]:
        """Quotes of the underlyings, by symbol."""

    @abstractmethod
    def option_quotes(self, contracts: Sequence[OptionContractSpec], screening_date: date) -> Dict[str, OptionQuote]:
        """Quotes + model greeks of option contracts, by OptionContractSpec.key."""
