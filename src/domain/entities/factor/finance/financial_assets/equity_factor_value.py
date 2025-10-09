"""
Domain entity for EquityFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.finance.financial_assets.security_factor_value import SecurityFactorValue


@dataclass
class EquityFactorValue(SecurityFactorValue):
    """
    Domain entity representing an equity-specific factor value.
    Extends SecurityFactorValue with equity-specific business logic.
    """
    equity_type: Optional[str] = None  # e.g., "common", "preferred", "reit"
    dividend_yield: Optional[Decimal] = None  # annual dividend yield as decimal
    pe_ratio: Optional[Decimal] = None  # price-to-earnings ratio
    market_cap: Optional[Decimal] = None  # market capitalization
    beta: Optional[Decimal] = None  # beta coefficient vs market
    
    def __post_init__(self):
        """Validate domain constraints including equity-specific ones."""
        super().__post_init__()
        
        # Convert to Decimal if needed
        for field in ['dividend_yield', 'pe_ratio', 'market_cap', 'beta']:
            value = getattr(self, field)
            if value is not None and not isinstance(value, Decimal):
                setattr(self, field, Decimal(str(value)))
        
        # Validate ranges
        if self.dividend_yield is not None and self.dividend_yield < 0:
            raise ValueError("dividend_yield cannot be negative")
        
        if self.pe_ratio is not None and self.pe_ratio < 0:
            raise ValueError("pe_ratio cannot be negative")

    def calculate_dividend_amount(self, shares: Decimal) -> Optional[Decimal]:
        """Calculate expected dividend amount based on yield."""
        if self.dividend_yield is None or shares <= 0:
            return None
        
        return self.value * shares * self.dividend_yield

    def calculate_earnings_per_share(self) -> Optional[Decimal]:
        """Calculate EPS from price and P/E ratio."""
        if self.pe_ratio is None or self.pe_ratio == 0:
            return None
        
        return self.value / self.pe_ratio

    def apply_dividend_adjustment(self, dividend_per_share: Decimal) -> 'EquityFactorValue':
        """Apply ex-dividend adjustment to price."""
        return EquityFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=self.value - dividend_per_share,  # Price drops by dividend amount
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
            beta=self.beta
        )

    def calculate_risk_adjusted_return(self, risk_free_rate: Decimal) -> Optional[Decimal]:
        """Calculate risk-adjusted return using beta."""
        if self.beta is None:
            return None
        
        # This is a simplified calculation - in practice, you'd need historical returns
        # For now, return a placeholder calculation
        return (self.value * self.beta) - risk_free_rate

    def get_market_cap_category(self) -> Optional[str]:
        """Categorize equity by market cap size."""
        if self.market_cap is None:
            return None
        
        # Convert to billions for comparison
        market_cap_billions = self.market_cap / Decimal('1000000000')
        
        if market_cap_billions >= Decimal('10'):
            return "large_cap"
        elif market_cap_billions >= Decimal('2'):
            return "mid_cap"
        elif market_cap_billions >= Decimal('0.3'):
            return "small_cap"
        else:
            return "micro_cap"

    def is_value_stock(self, market_pe_avg: Optional[Decimal] = None) -> bool:
        """Determine if this is a value stock based on P/E ratio."""
        if self.pe_ratio is None:
            return False
        
        # Use market average or a default threshold
        threshold = market_pe_avg or Decimal('15')
        return self.pe_ratio < threshold

    def __str__(self) -> str:
        return f"EquityFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, ticker_symbol={self.ticker_symbol}, equity_type={self.equity_type}, value={self.value}, market_cap={self.market_cap})"