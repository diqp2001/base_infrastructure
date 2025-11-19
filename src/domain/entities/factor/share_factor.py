"""
src/domain/entities/factor/share_factor.py

ShareFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .equity_factor import EquityFactor


class ShareFactor(EquityFactor):
    """Domain entity representing a share-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        asset_class: Optional[str] = "equity",
        currency: Optional[str] = None,
        market: Optional[str] = None,
        security_type: Optional[str] = "stock",
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap_category: Optional[str] = None,
        ticker_symbol: Optional[str] = None,
        share_class: Optional[str] = None,
        exchange: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            asset_class=asset_class,
            currency=currency,
            market=market,
            security_type=security_type,
            isin=isin,
            cusip=cusip,
            sector=sector,
            industry=industry,
            market_cap_category=market_cap_category,
        )
        self.ticker_symbol = ticker_symbol  # e.g., "AAPL", "GOOGL", "TSLA"
        self.share_class = share_class  # e.g., "A", "B", "common", "preferred"
        self.exchange = exchange  # e.g., "NASDAQ", "NYSE", "LSE"

    def get_display_symbol(self) -> str:
        """Get the display symbol for this share."""
        if self.ticker_symbol and self.share_class and self.share_class.upper() not in ['COMMON', 'ORDINARY']:
            return f"{self.ticker_symbol}.{self.share_class}"
        return self.ticker_symbol or "N/A"

    def is_preferred_share(self) -> bool:
        """Check if this is a preferred share."""
        return self.share_class and "preferred" in self.share_class.lower()