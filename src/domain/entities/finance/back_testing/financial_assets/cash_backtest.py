"""
Cash backtest class extending SecurityBackTest with cash-specific functionality.
Provides cash flow management, interest calculations, and liquidity features.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from domain.entities.finance.back_testing.enums import SecurityType
from domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class InterestPayment:
    """Value object for interest payments."""
    amount: Decimal
    payment_date: datetime
    interest_rate: Decimal
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Interest amount cannot be negative")
        if self.interest_rate < 0:
            raise ValueError("Interest rate cannot be negative")


class CashBackTest(SecurityBackTest):
    """
    Cash class extending SecurityBackTest with cash-specific functionality.
    Provides cash flow management, interest calculations, and liquidity features.
    """
    
    def __init__(self, id: int, currency: str, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            value=currency.upper(),
            security_type=SecurityType.BASE  # Cash as base security type
        )
        
        super().__init__(symbol)
        
        # Cash-specific attributes
        self.id = id
        self.currency = currency.upper()
        self.start_date = start_date
        self.end_date = end_date
        
        # Cash-specific features
        self._interest_rate = Decimal('0.0')  # Annual interest rate
        self._interest_payments: List[InterestPayment] = []
        self._is_liquid = True  # Cash is always liquid
        
    @property
    def currency_code(self) -> str:
        """Get currency code."""
        return self.currency
        
    @property
    def interest_rate(self) -> Decimal:
        """Get current interest rate."""
        return self._interest_rate
    
    @property
    def interest_payments(self) -> List[InterestPayment]:
        """Get interest payment history."""
        return self._interest_payments.copy()
    
    @property
    def is_liquid(self) -> bool:
        """Cash is always liquid."""
        return self._is_liquid
    
    def _post_process_data(self, data: MarketData) -> None:
        """Cash-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Calculate accrued interest if applicable
        self._calculate_accrued_interest(data.timestamp)
    
    def _calculate_accrued_interest(self, current_date: datetime) -> None:
        """Calculate accrued interest based on current holdings."""
        if self._interest_rate <= 0 or self.holdings.quantity <= 0:
            return
            
        # Simple daily interest calculation
        daily_rate = self._interest_rate / Decimal('365')
        daily_interest = self.holdings.quantity * daily_rate
        
        # This would typically be tracked separately in a real system
        
    def update_interest_rate(self, new_rate: Decimal) -> None:
        """Update the interest rate for cash holdings."""
        if new_rate < 0:
            raise ValueError("Interest rate cannot be negative")
        self._interest_rate = new_rate
    
    def add_interest_payment(self, payment: InterestPayment) -> None:
        """Add an interest payment to history."""
        self._interest_payments.append(payment)
        self._interest_payments.sort(key=lambda p: p.payment_date, reverse=True)
    
    def calculate_annual_yield(self) -> Decimal:
        """Calculate annual yield based on interest payments."""
        if self.holdings.quantity <= 0:
            return Decimal('0')
            
        annual_interest = sum(
            payment.amount for payment in self._interest_payments
            if (datetime.now() - payment.payment_date).days <= 365
        )
        
        return (annual_interest / self.holdings.quantity) * Decimal('100')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Cash typically has no margin requirement as it's fully liquid.
        """
        return Decimal('0')  # No margin required for cash
    
    def get_contract_multiplier(self) -> Decimal:
        """Cash has a contract multiplier of 1."""
        return Decimal('1')
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "Cash"
    
    def __str__(self) -> str:
        return f"Cash({self.currency}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Cash(id={self.id}, currency={self.currency}, "
                f"price={self.price}, interest_rate={self.interest_rate:.2%})")