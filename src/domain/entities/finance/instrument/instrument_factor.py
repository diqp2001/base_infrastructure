"""
src/domain/entities/finance/instrument/instrument_factor.py

InstrumentFactor domain entity - follows unified factor pattern for instruments.
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from src.domain.entities.factor.factor import Factor


class InstrumentFactor(Factor):
    """Domain entity representing an instrument-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        # Instrument-specific attributes
        instrument_id: Optional[int] = None,
        asset_type: Optional[str] = None,
        data_provider: Optional[str] = None,
        frequency: Optional[str] = None,
        currency: Optional[str] = None,
        last_updated: Optional[datetime] = None,
    ):
        """
        Initialize an InstrumentFactor.
        
        Args:
            name: Factor name (e.g., "Price", "Volume", "Volatility")
            group: Factor group (e.g., "Market", "Risk", "Fundamental")
            subgroup: Factor subgroup (e.g., "Technical", "Statistical")
            data_type: Data type (e.g., "float", "decimal", "percentage")
            source: Data source (e.g., "Bloomberg", "Reuters")
            definition: Factor definition/description
            factor_id: Unique factor ID
            instrument_id: Associated instrument ID
            asset_type: Type of underlying asset (e.g., "Stock", "Bond", "Commodity")
            data_provider: Specific data provider
            frequency: Data frequency (e.g., "daily", "hourly", "real-time")
            currency: Currency denomination
            last_updated: Last update timestamp
        """
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )
        self.instrument_id = instrument_id
        self.asset_type = asset_type
        self.data_provider = data_provider
        self.frequency = frequency
        self.currency = currency
        self.last_updated = last_updated

    def is_market_factor(self) -> bool:
        """Check if this is a market-related factor."""
        return self.group and self.group.lower() == "market"

    def is_risk_factor(self) -> bool:
        """Check if this is a risk-related factor."""
        return self.group and self.group.lower() == "risk"

    def is_fundamental_factor(self) -> bool:
        """Check if this is a fundamental analysis factor."""
        return self.group and self.group.lower() == "fundamental"

    def is_technical_factor(self) -> bool:
        """Check if this is a technical analysis factor."""
        return self.subgroup and self.subgroup.lower() == "technical"

    def validate_frequency(self) -> bool:
        """Validate that frequency is one of the accepted values."""
        valid_frequencies = ["real-time", "minute", "hourly", "daily", "weekly", "monthly", "quarterly", "annual"]
        return self.frequency is None or self.frequency.lower() in valid_frequencies

    def validate_currency(self) -> bool:
        """Validate that currency follows ISO 4217 standard."""
        return self.currency is None or (len(self.currency) == 3 and self.currency.isupper())

    def is_stale(self, threshold_hours: int = 24) -> bool:
        """Check if the factor data is stale based on last update time."""
        if self.last_updated is None:
            return True
        
        now = datetime.now()
        time_diff = now - self.last_updated
        return time_diff.total_seconds() > (threshold_hours * 3600)

    def __repr__(self):
        return (
            f"InstrumentFactor(id={self.id}, name={self.name}, group={self.group}, "
            f"instrument_id={self.instrument_id}, asset_type={self.asset_type})"
        )