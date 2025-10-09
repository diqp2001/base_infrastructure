"""
Domain entity for ShareFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.finance.financial_assets.equity_factor_value import EquityFactorValue


@dataclass
class ShareFactorValue(EquityFactorValue):
    """
    Domain entity representing a share-specific factor value.
    Extends EquityFactorValue with share-specific business logic.
    """
    share_class: Optional[str] = None  # e.g., "A", "B", "C"
    shares_outstanding: Optional[Decimal] = None  # number of shares outstanding
    float_shares: Optional[Decimal] = None  # number of publicly traded shares
    voting_rights_per_share: Optional[int] = None  # voting power per share
    par_value: Optional[Decimal] = None  # par value of the share
    
    def __post_init__(self):
        """Validate domain constraints including share-specific ones."""
        super().__post_init__()
        
        # Convert to Decimal if needed
        for field in ['shares_outstanding', 'float_shares', 'par_value']:
            value = getattr(self, field)
            if value is not None and not isinstance(value, Decimal):
                setattr(self, field, Decimal(str(value)))
        
        # Validate share counts
        if self.shares_outstanding is not None and self.shares_outstanding < 0:
            raise ValueError("shares_outstanding cannot be negative")
        
        if self.float_shares is not None and self.float_shares < 0:
            raise ValueError("float_shares cannot be negative")
        
        if (self.shares_outstanding is not None and self.float_shares is not None and 
            self.float_shares > self.shares_outstanding):
            raise ValueError("float_shares cannot exceed shares_outstanding")

    def calculate_total_market_value(self) -> Optional[Decimal]:
        """Calculate total market value of all outstanding shares."""
        if self.shares_outstanding is None:
            return None
        
        return self.value * self.shares_outstanding

    def calculate_float_market_value(self) -> Optional[Decimal]:
        """Calculate market value of publicly traded shares."""
        if self.float_shares is None:
            return None
        
        return self.value * self.float_shares

    def calculate_ownership_percentage(self, shares_held: Decimal) -> Optional[Decimal]:
        """Calculate ownership percentage for given number of shares."""
        if self.shares_outstanding is None or self.shares_outstanding == 0:
            return None
        
        return (shares_held / self.shares_outstanding) * Decimal('100')

    def calculate_voting_power(self, shares_held: Decimal) -> Optional[int]:
        """Calculate total voting power for given number of shares."""
        if self.voting_rights_per_share is None:
            return None
        
        return int(shares_held * Decimal(str(self.voting_rights_per_share)))

    def apply_share_buyback(self, shares_bought: Decimal) -> 'ShareFactorValue':
        """Apply share buyback effect (reduces outstanding shares)."""
        if self.shares_outstanding is None:
            raise ValueError("Cannot apply buyback without shares_outstanding data")
        
        if shares_bought > self.shares_outstanding:
            raise ValueError("Cannot buy back more shares than outstanding")
        
        new_outstanding = self.shares_outstanding - shares_bought
        new_float = (self.float_shares - min(shares_bought, self.float_shares) 
                    if self.float_shares else None)
        
        # Share price typically increases due to reduced supply
        buyback_ratio = self.shares_outstanding / new_outstanding if new_outstanding > 0 else Decimal('1')
        
        return ShareFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=self.value * buyback_ratio,
            asset_class=self.asset_class,
            market_value=self.market_value,
            currency=self.currency,
            is_adjusted=True,
            security_type=self.security_type,
            ticker_symbol=self.ticker_symbol,
            exchange=self.exchange,
            volume=self.volume,
            equity_type=self.equity_type,
            dividend_yield=self.dividend_yield,
            pe_ratio=self.pe_ratio,
            market_cap=self.market_cap,
            beta=self.beta,
            share_class=self.share_class,
            shares_outstanding=new_outstanding,
            float_shares=new_float,
            voting_rights_per_share=self.voting_rights_per_share,
            par_value=self.par_value
        )

    def calculate_book_value_per_share(self, total_book_value: Decimal) -> Optional[Decimal]:
        """Calculate book value per share."""
        if self.shares_outstanding is None or self.shares_outstanding == 0:
            return None
        
        return total_book_value / self.shares_outstanding

    def get_liquidity_ratio(self) -> Optional[Decimal]:
        """Get ratio of float shares to total outstanding shares."""
        if self.shares_outstanding is None or self.float_shares is None:
            return None
        
        if self.shares_outstanding == 0:
            return Decimal('0')
        
        return self.float_shares / self.shares_outstanding

    def is_penny_stock(self, threshold: Decimal = Decimal('5.00')) -> bool:
        """Check if this is considered a penny stock."""
        return self.value < threshold

    def __str__(self) -> str:
        return f"ShareFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, ticker_symbol={self.ticker_symbol}, share_class={self.share_class}, value={self.value}, shares_outstanding={self.shares_outstanding})"