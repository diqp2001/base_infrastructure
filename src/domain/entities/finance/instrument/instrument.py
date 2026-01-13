"""
src/domain/entities/finance/instrument/instrument.py

Instrument domain entity - represents a financial instrument that references a FinancialAsset.
"""

from typing import Optional
from datetime import datetime
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Instrument:
    """Domain entity representing a financial instrument."""

    def __init__(
        self,
        id: Optional[int],
        asset: FinancialAsset,
        source: str,
        date: datetime
    ):
        """
        Initialize an Instrument entity.
        
        Args:
            id: Unique identifier for the instrument
            asset: The underlying FinancialAsset
            source: Data source for the instrument (e.g., 'Bloomberg', 'Reuters', 'Yahoo')
            date: Date when the instrument data was recorded
        """
        self.id = id
        self.asset = asset
        self.source = source
        self.date = date

    @property
    def asset_id(self) -> Optional[int]:
        """Get the ID of the underlying asset."""
        return self.asset.id if self.asset else None

    @property
    def asset_type(self) -> str:
        """Get the type of the underlying asset."""
        return self.asset.asset_type if self.asset else "Unknown"

    def is_valid(self) -> bool:
        """Validate that the instrument has required data."""
        return (
            self.asset is not None and
            self.source is not None and
            len(self.source.strip()) > 0 and
            self.date is not None
        )

    def __repr__(self):
        return (
            f"Instrument(id={self.id}, asset_type={self.asset_type}, "
            f"source={self.source}, date={self.date})"
        )

    def __eq__(self, other):
        if not isinstance(other, Instrument):
            return False
        return (
            self.id == other.id and
            self.asset == other.asset and
            self.source == other.source and
            self.date == other.date
        )

    def __hash__(self):
        return hash((self.id, self.asset_id, self.source, self.date))