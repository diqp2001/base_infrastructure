"""Ports of the dispersion screener's ETF data. Every call takes the screening date (historical screens: an
adapter answers with what was known on that date, or nothing)."""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.ports.finance.dispersion.etf_holdings import EtfHoldingsSnapshot, EtfListing


class EtfUniversePort(ABC):

    @abstractmethod
    def list_etfs(self, screening_date: date) -> List[EtfListing]:
        """Every ETF the source lists (no filtering beyond 'is an ETF')."""


class EtfHoldingsPort(ABC):

    @abstractmethod
    def get_holdings(self, listing: EtfListing, screening_date: date) -> Optional[EtfHoldingsSnapshot]:
        """The latest holdings dated on or before screening_date; None when the source has none."""
