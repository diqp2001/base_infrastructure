"""
Bond class for fixed-income securities.
Extends Security with bond-specific functionality and characteristics.
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass
from .security import Security, Symbol, SecurityType, MarketData


@dataclass
class CouponPayment:
    """Value object for bond coupon payments."""
    amount: Decimal
    payment_date: date
    rate: Decimal  # Coupon rate as decimal (e.g., 0.05 for 5%)
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Coupon amount cannot be negative")
        if self.rate < 0:
            raise ValueError("Coupon rate cannot be negative")


class BondType:
    """Constants for different bond types."""
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    MUNICIPAL = "municipal"
    TREASURY = "treasury"
    HIGH_YIELD = "high_yield"
    INVESTMENT_GRADE = "investment_grade"


class Bond(Security):
    """
    Bond class extending Security for fixed-income instruments.
    Handles bond-specific functionality like yield calculations, duration, and coupon payments.
    """
    
    def __init__(self, cusip: str, issuer: str, maturity_date: date,
                 coupon_rate: Decimal, par_value: Decimal = Decimal('1000'),
                 bond_type: str = BondType.CORPORATE, 
                 payment_frequency: int = 2):  # Semi-annual by default
        # Create symbol for base Security class
        symbol = Symbol(
            ticker=cusip,  # Use CUSIP as ticker for bonds
            exchange="BOND",
            security_type=SecurityType.BOND
        )
        
        super().__init__(symbol)
        
        # Bond-specific attributes
        self.cusip = cusip
        self.issuer = issuer
        self.maturity_date = maturity_date
        self.coupon_rate = coupon_rate  # Annual coupon rate
        self.par_value = par_value  # Face value
        self.bond_type = bond_type
        self.payment_frequency = payment_frequency  # Payments per year
        
        # Bond metrics
        self._yield_to_maturity: Optional[Decimal] = None
        self._duration: Optional[Decimal] = None
        self._credit_rating: Optional[str] = None
        self._coupon_history: List[CouponPayment] = []
        
        # Set initial price to par value if not set
        if self._price == 0:
            self._price = par_value
    
    @property
    def yield_to_maturity(self) -> Optional[Decimal]:
        """Get yield to maturity."""
        return self._yield_to_maturity
    
    @property
    def duration(self) -> Optional[Decimal]:
        """Get modified duration."""
        return self._duration
    
    @property
    def credit_rating(self) -> Optional[str]:
        """Get credit rating (e.g., 'AAA', 'BBB+')."""
        return self._credit_rating
    
    @property
    def coupon_history(self) -> List[CouponPayment]:
        """Get coupon payment history."""
        return self._coupon_history.copy()
    
    def _post_process_data(self, data: MarketData) -> None:
        """Bond-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Recalculate yield to maturity when price changes
        self._calculate_yield_to_maturity()
        
        # Update duration based on new price
        self._calculate_duration()
    
    def add_coupon_payment(self, payment: CouponPayment) -> None:
        """Add a coupon payment to history."""
        self._coupon_history.append(payment)
        self._coupon_history.sort(key=lambda c: c.payment_date, reverse=True)
    
    def update_credit_rating(self, rating: str) -> None:
        """Update credit rating."""
        self._credit_rating = rating
    
    def calculate_accrued_interest(self, settlement_date: Optional[date] = None) -> Decimal:
        """Calculate accrued interest since last coupon payment."""
        if not settlement_date:
            settlement_date = date.today()
        
        # Find the last coupon payment date
        last_coupon_date = None
        for payment in self._coupon_history:
            if payment.payment_date <= settlement_date:
                last_coupon_date = payment.payment_date
                break
        
        if not last_coupon_date:
            # If no payment history, calculate from issue date (simplified)
            # This would need actual issue date in a real implementation
            return Decimal('0')
        
        # Calculate days since last coupon
        days_since_coupon = (settlement_date - last_coupon_date).days
        
        # Assume 30/360 day count convention (simplified)
        days_in_period = 360 // self.payment_frequency
        
        # Calculate accrued interest
        period_coupon = (self.coupon_rate * self.par_value) / Decimal(self.payment_frequency)
        accrued = period_coupon * (Decimal(days_since_coupon) / Decimal(days_in_period))
        
        return accrued
    
    def _calculate_yield_to_maturity(self) -> None:
        """Calculate yield to maturity using approximation method."""
        if self.price <= 0:
            return
        
        # Simplified YTM calculation (in practice, would use iterative method)
        years_to_maturity = (self.maturity_date - date.today()).days / 365.25
        
        if years_to_maturity <= 0:
            self._yield_to_maturity = Decimal('0')
            return
        
        annual_coupon = self.coupon_rate * self.par_value
        
        # Approximation formula
        numerator = annual_coupon + ((self.par_value - self.price) / Decimal(years_to_maturity))
        denominator = (self.par_value + self.price) / Decimal('2')
        
        self._yield_to_maturity = (numerator / denominator) * Decimal('100')
    
    def _calculate_duration(self) -> None:
        """Calculate modified duration."""
        if not self._yield_to_maturity or self._yield_to_maturity <= 0:
            return
        
        # Simplified duration calculation
        years_to_maturity = (self.maturity_date - date.today()).days / 365.25
        ytm_decimal = self._yield_to_maturity / Decimal('100')
        
        # Approximation for modified duration
        self._duration = Decimal(years_to_maturity) / (Decimal('1') + ytm_decimal)
    
    def get_current_yield(self) -> Decimal:
        """Calculate current yield (annual coupon / current price)."""
        if self.price <= 0:
            return Decimal('0')
        
        annual_coupon = self.coupon_rate * self.par_value
        return (annual_coupon / self.price) * Decimal('100')
    
    def calculate_price_from_yield(self, yield_to_maturity: Decimal) -> Decimal:
        """Calculate theoretical bond price from given yield."""
        ytm_decimal = yield_to_maturity / Decimal('100')
        years_to_maturity = (self.maturity_date - date.today()).days / 365.25
        
        if years_to_maturity <= 0:
            return self.par_value
        
        # Present value of coupon payments
        annual_coupon = self.coupon_rate * self.par_value
        pv_coupons = Decimal('0')
        
        for year in range(1, int(years_to_maturity) + 1):
            discount_factor = (Decimal('1') + ytm_decimal) ** Decimal(year)
            pv_coupons += annual_coupon / discount_factor
        
        # Present value of principal
        discount_factor = (Decimal('1') + ytm_decimal) ** Decimal(years_to_maturity)
        pv_principal = self.par_value / discount_factor
        
        return pv_coupons + pv_principal
    
    def is_callable(self) -> bool:
        """Check if bond has call provisions (simplified - would need call schedule)."""
        # This would need actual call provisions data
        return False
    
    def is_investment_grade(self) -> bool:
        """Check if bond is investment grade based on credit rating."""
        if not self._credit_rating:
            return False
        
        # Standard investment grade ratings
        investment_grades = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 
                           'BBB+', 'BBB', 'BBB-']
        return self._credit_rating in investment_grades
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for bond position.
        Typically lower than equities: 10-20% depending on credit quality.
        """
        position_value = abs(quantity * self.price)
        
        # Lower margin for investment grade bonds
        if self.is_investment_grade():
            margin_rate = Decimal('0.1')  # 10%
        else:
            margin_rate = Decimal('0.2')  # 20% for high yield
        
        return position_value * margin_rate
    
    def get_contract_multiplier(self) -> Decimal:
        """Bonds typically trade in $1000 par value units."""
        return self.par_value
    
    def get_bond_metrics(self) -> dict:
        """Get bond-specific metrics."""
        return {
            'cusip': self.cusip,
            'issuer': self.issuer,
            'bond_type': self.bond_type,
            'maturity_date': self.maturity_date,
            'coupon_rate': self.coupon_rate,
            'par_value': self.par_value,
            'current_price': self.price,
            'current_yield': self.get_current_yield(),
            'yield_to_maturity': self.yield_to_maturity,
            'duration': self.duration,
            'credit_rating': self.credit_rating,
            'is_investment_grade': self.is_investment_grade(),
            'accrued_interest': self.calculate_accrued_interest(),
        }
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Bond"
    
    def __str__(self) -> str:
        return f"Bond({self.cusip}, ${self.price}, {self.coupon_rate:.2f}%)"
    
    def __repr__(self) -> str:
        return (f"Bond(cusip={self.cusip}, issuer={self.issuer}, "
                f"price=${self.price}, ytm={self.yield_to_maturity}%)")


# Legacy compatibility
from .financial_asset import FinancialAsset

class BondLegacy(FinancialAsset):
    """Legacy Bond class for backwards compatibility."""
    def __init__(self, name, ticker, value, date, company_id):
        super().__init__(name, ticker, value, date)
        self.company_id = company_id

    def calculate_interest(self):
        pass