"""Port of the daily closes the realized-payoff history reads (split-adjusted, not dividend-adjusted: option strikes
follow splits, not ordinary dividends). A source that does not answer raises MarketDataUnavailable; a symbol without
data returns an empty mapping (never zeros)."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict

from src.domain.entities.finance.dispersion.option_data import Underlying


class PriceHistoryPort(ABC):

    @abstractmethod
    def daily_closes(self, underlying: Underlying, start: date, end: date) -> Dict[date, float]:
        """Trading day -> close, for start <= day <= end."""
