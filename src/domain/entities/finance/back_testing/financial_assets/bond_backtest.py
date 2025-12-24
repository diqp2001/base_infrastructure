"""
Bond class extending SecurityBackTest following QuantConnect architecture.
Provides bond-specific functionality including yield calculations, duration, and coupon payments.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from domain.entities.finance.back_testing.enums import SecurityType, Market
from domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class CouponPayment:
    """Value object for bond coupon payments."""
    amount: Decimal
    payment_date: date
    rate: Decimal  # Coupon rate as decimal (e.g., 0.05 for 5%)
    ex_date: Optional[date] = None
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Coupon amount cannot be negative")
        if self.rate < 0:
            raise ValueError("Coupon rate cannot be negative")
        if self.ex_date and self.ex_date > self.payment_date:
            raise ValueError("Ex-date cannot be after payment date")


@dataclass
class CreditRatingChange:
    """Value object for credit rating changes."""
    new_rating: str
    old_rating: Optional[str]
    rating_agency: str
    change_date: datetime
    outlook: Optional[str] = None  # 'positive', 'negative', 'stable'
    
    def __post_init__(self):
        valid_outlooks = ['positive', 'negative', 'stable', None]
        if self.outlook not in valid_outlooks:
            raise ValueError(f"Outlook must be one of: {valid_outlooks}")


@dataclass
class CallProvision:
    """Value object for bond call provisions."""
    call_date: date
    call_price: Decimal
    call_type: str = "AMERICAN"  # AMERICAN, EUROPEAN, BERMUDAN
    
    def __post_init__(self):
        if self.call_price < 0:
            raise ValueError("Call price cannot be negative")
        valid_types = ["AMERICAN", "EUROPEAN", "BERMUDAN"]
        if self.call_type not in valid_types:
            raise ValueError(f"Call type must be one of: {valid_types}")


class BondType:
    """Constants for different bond types."""
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    MUNICIPAL = "municipal"
    TREASURY = "treasury"
    HIGH_YIELD = "high_yield"
    INVESTMENT_GRADE = "investment_grade"
    CONVERTIBLE = "convertible"
    ZERO_COUPON = "zero_coupon"


class BondBackTest(SecurityBackTest):
    """
    Bond class extending SecurityBackTest for fixed-income instruments.
    Handles bond-specific functionality like yield calculations, duration, and coupon payments.
    """
    
    def __init__(self, cusip: str, issuer: str, maturity_date: date,
                 coupon_rate: Decimal, par_value: Decimal = Decimal('1000'),
                 bond_type: str = BondType.CORPORATE, 
                 payment_frequency: int = 2,  # Semi-annual by default
                 issue_date: Optional[date] = None):
        # Create symbol for base SecurityBackTest class
        symbol = Symbol(
            value=cusip,  # Use CUSIP as symbol value for bonds
            security_type=SecurityType.BASE,  # Using BASE as BOND not in enum
            market=Market.USA
        )
        
        super().__init__(symbol)
        
        # Bond-specific attributes
        self.cusip = cusip
        self.issuer = issuer
        self.maturity_date = maturity_date
        self.coupon_rate = coupon_rate  # Annual coupon rate as decimal
        self.par_value = par_value  # Face value
        self.bond_type = bond_type
        self.payment_frequency = payment_frequency  # Payments per year
        self.issue_date = issue_date or date.today()
        
        # Bond metrics
        self._yield_to_maturity: Optional[Decimal] = None
        self._yield_to_call: Optional[Decimal] = None
        self._duration: Optional[Decimal] = None
        self._modified_duration: Optional[Decimal] = None
        self._convexity: Optional[Decimal] = None
        self._credit_rating: Optional[str] = None
        self._credit_spread: Optional[Decimal] = None
        
        # Collections
        self._coupon_history: List[CouponPayment] = []
        self._rating_history: List[CreditRatingChange] = []
        self._call_schedule: List[CallProvision] = []
        
        # Bond state
        self._accrued_interest: Decimal = Decimal('0')
        self._days_to_maturity: Optional[int] = None
        self._is_callable: bool = False
        self._is_defaulted: bool = False
        
        # Set initial price to par value if not set
        if self._price == 0:
            self._price = par_value
    
    @property
    def yield_to_maturity(self) -> Optional[Decimal]:
        """Get yield to maturity."""
        return self._yield_to_maturity
    
    @property
    def yield_to_call(self) -> Optional[Decimal]:
        """Get yield to call (if callable)."""
        return self._yield_to_call
    
    @property
    def duration(self) -> Optional[Decimal]:
        """Get Macaulay duration."""
        return self._duration
    
    @property
    def modified_duration(self) -> Optional[Decimal]:
        """Get modified duration."""
        return self._modified_duration
    
    @property
    def convexity(self) -> Optional[Decimal]:
        """Get convexity."""
        return self._convexity
    
    @property
    def credit_rating(self) -> Optional[str]:
        """Get current credit rating."""
        return self._credit_rating
    
    @property
    def credit_spread(self) -> Optional[Decimal]:
        """Get credit spread over benchmark."""
        return self._credit_spread
    
    @property
    def accrued_interest(self) -> Decimal:
        """Get current accrued interest."""
        return self._accrued_interest
    
    @property
    def coupon_history(self) -> List[CouponPayment]:
        """Get coupon payment history."""
        return self._coupon_history.copy()
    
    @property
    def rating_history(self) -> List[CreditRatingChange]:
        """Get credit rating change history."""
        return self._rating_history.copy()
    
    @property
    def call_schedule(self) -> List[CallProvision]:
        """Get call provisions schedule."""
        return self._call_schedule.copy()
    
    @property
    def days_to_maturity(self) -> Optional[int]:
        """Get days until maturity."""
        return self._days_to_maturity
    
    @property
    def is_callable(self) -> bool:
        """Check if bond has call provisions."""
        return self._is_callable and len(self._call_schedule) > 0
    
    @property
    def is_defaulted(self) -> bool:
        """Check if bond is in default."""
        return self._is_defaulted
    
    def _post_process_data(self, data: MarketData) -> None:
        """Bond-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update days to maturity
        self._days_to_maturity = (self.maturity_date - date.today()).days
        
        # Update accrued interest
        self._update_accrued_interest()
        
        # Recalculate yield to maturity when price changes
        self._calculate_yield_to_maturity()
        
        # Update duration based on new price and yield
        self._calculate_duration_metrics()
        
        # Update yield to call if applicable
        if self.is_callable:
            self._calculate_yield_to_call()
        
        # Check for maturity
        if self._days_to_maturity is not None and self._days_to_maturity <= 0:
            self._handle_maturity()
    
    def add_coupon_payment(self, payment: CouponPayment) -> None:
        """Add a coupon payment to history."""
        self._coupon_history.append(payment)
        self._coupon_history.sort(key=lambda c: c.payment_date, reverse=True)
    
    def add_credit_rating_change(self, rating_change: CreditRatingChange) -> None:
        """Add a credit rating change to history."""
        self._credit_rating = rating_change.new_rating
        self._rating_history.append(rating_change)
        self._rating_history.sort(key=lambda r: r.change_date, reverse=True)
        
        # Update credit spread based on rating
        self._update_credit_spread()
    
    def add_call_provision(self, call_provision: CallProvision) -> None:
        """Add a call provision to the schedule."""
        self._call_schedule.append(call_provision)
        self._call_schedule.sort(key=lambda c: c.call_date)
        self._is_callable = True
    
    def _update_accrued_interest(self) -> None:
        """Update accrued interest since last coupon payment."""
        settlement_date = date.today()
        
        # Find the last coupon payment date
        last_coupon_date = None
        for payment in self._coupon_history:
            if payment.payment_date <= settlement_date:
                last_coupon_date = payment.payment_date
                break
        
        if not last_coupon_date:
            # Use issue date if no payment history
            last_coupon_date = self.issue_date
        
        # Calculate days since last coupon
        days_since_coupon = (settlement_date - last_coupon_date).days
        
        # Assume 30/360 day count convention (could be parameterized)
        days_in_period = 360 // self.payment_frequency
        
        # Calculate accrued interest
        period_coupon = (self.coupon_rate * self.par_value) / Decimal(self.payment_frequency)
        self._accrued_interest = period_coupon * (Decimal(days_since_coupon) / Decimal(days_in_period))
    
    def _calculate_yield_to_maturity(self) -> None:
        """Calculate yield to maturity using approximation method."""
        if self.price <= 0 or not self._days_to_maturity or self._days_to_maturity <= 0:
            return
        
        years_to_maturity = Decimal(self._days_to_maturity) / Decimal('365.25')
        annual_coupon = self.coupon_rate * self.par_value
        
        # Approximation formula (simplified)
        numerator = annual_coupon + ((self.par_value - self.price) / years_to_maturity)
        denominator = (self.par_value + self.price) / Decimal('2')
        
        if denominator > 0:
            self._yield_to_maturity = (numerator / denominator) * Decimal('100')
    
    def _calculate_yield_to_call(self) -> None:
        """Calculate yield to call for the next call date."""
        if not self._call_schedule:
            return
        
        # Find next callable date
        today = date.today()
        next_call = None
        for call in self._call_schedule:
            if call.call_date > today:
                next_call = call
                break
        
        if not next_call:
            return
        
        days_to_call = (next_call.call_date - today).days
        if days_to_call <= 0:
            return
        
        years_to_call = Decimal(days_to_call) / Decimal('365.25')
        annual_coupon = self.coupon_rate * self.par_value
        
        # YTC calculation similar to YTM but using call price and call date
        numerator = annual_coupon + ((next_call.call_price - self.price) / years_to_call)
        denominator = (next_call.call_price + self.price) / Decimal('2')
        
        if denominator > 0:
            self._yield_to_call = (numerator / denominator) * Decimal('100')
    
    def _calculate_duration_metrics(self) -> None:
        """Calculate duration and convexity metrics."""
        if not self._yield_to_maturity or self._yield_to_maturity <= 0:
            return
        
        if not self._days_to_maturity or self._days_to_maturity <= 0:
            return
        
        years_to_maturity = Decimal(self._days_to_maturity) / Decimal('365.25')
        ytm_decimal = self._yield_to_maturity / Decimal('100')
        
        # Simplified Macaulay duration calculation
        # This is an approximation; real calculation requires cash flow weighting
        self._duration = years_to_maturity / (Decimal('1') + ytm_decimal / Decimal(self.payment_frequency))
        
        # Modified duration
        if self._duration:
            self._modified_duration = self._duration / (Decimal('1') + ytm_decimal / Decimal(self.payment_frequency))
        
        # Simplified convexity (approximation)
        if self._modified_duration:
            self._convexity = self._modified_duration ** 2
    
    def _update_credit_spread(self) -> None:
        """Update credit spread based on current rating."""
        if not self._credit_rating:
            return
        
        # Simplified credit spread mapping
        credit_spreads = {
            'AAA': Decimal('0.5'), 'AA+': Decimal('0.7'), 'AA': Decimal('1.0'), 'AA-': Decimal('1.3'),
            'A+': Decimal('1.6'), 'A': Decimal('2.0'), 'A-': Decimal('2.5'),
            'BBB+': Decimal('3.0'), 'BBB': Decimal('3.5'), 'BBB-': Decimal('4.0'),
            'BB+': Decimal('5.0'), 'BB': Decimal('6.0'), 'BB-': Decimal('7.0'),
            'B+': Decimal('8.0'), 'B': Decimal('10.0'), 'B-': Decimal('12.0'),
            'CCC': Decimal('15.0'), 'CC': Decimal('20.0'), 'C': Decimal('25.0'), 'D': Decimal('50.0')
        }
        
        self._credit_spread = credit_spreads.get(self._credit_rating, Decimal('5.0'))
    
    def _handle_maturity(self) -> None:
        """Handle bond reaching maturity."""
        # Set price to par value at maturity
        self._price = self.par_value
        self._yield_to_maturity = Decimal('0')
        self._duration = Decimal('0')
        self._modified_duration = Decimal('0')
        
        # Add final coupon payment if applicable
        if self.coupon_rate > 0:
            final_coupon = CouponPayment(
                amount=self.coupon_rate * self.par_value / Decimal(self.payment_frequency),
                payment_date=self.maturity_date,
                rate=self.coupon_rate
            )
            self.add_coupon_payment(final_coupon)
    
    def get_current_yield(self) -> Decimal:
        """Calculate current yield (annual coupon / current price)."""
        if self.price <= 0:
            return Decimal('0')
        
        annual_coupon = self.coupon_rate * self.par_value
        return (annual_coupon / self.price) * Decimal('100')
    
    def calculate_price_from_yield(self, target_yield: Decimal) -> Decimal:
        """Calculate theoretical bond price from given yield."""
        if not self._days_to_maturity or self._days_to_maturity <= 0:
            return self.par_value
        
        ytm_decimal = target_yield / Decimal('100')
        years_to_maturity = Decimal(self._days_to_maturity) / Decimal('365.25')
        
        # Present value of coupon payments
        annual_coupon = self.coupon_rate * self.par_value
        periods = int(years_to_maturity * self.payment_frequency)
        period_rate = ytm_decimal / Decimal(self.payment_frequency)
        period_coupon = annual_coupon / Decimal(self.payment_frequency)
        
        pv_coupons = Decimal('0')
        for period in range(1, periods + 1):
            if period_rate > 0:
                discount_factor = (Decimal('1') + period_rate) ** Decimal(period)
                pv_coupons += period_coupon / discount_factor
            else:
                pv_coupons += period_coupon
        
        # Present value of principal
        if period_rate > 0 and periods > 0:
            discount_factor = (Decimal('1') + period_rate) ** Decimal(periods)
            pv_principal = self.par_value / discount_factor
        else:
            pv_principal = self.par_value
        
        return pv_coupons + pv_principal
    
    def is_investment_grade(self) -> bool:
        """Check if bond is investment grade based on credit rating."""
        if not self._credit_rating:
            return False
        
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
            if self._credit_rating and self._credit_rating.startswith('AAA'):
                margin_rate = Decimal('0.05')  # 5% for AAA bonds
            else:
                margin_rate = Decimal('0.10')  # 10% for other investment grade
        else:
            margin_rate = Decimal('0.25')  # 25% for high yield/junk bonds
        
        return position_value * margin_rate
    
    def get_contract_multiplier(self) -> Decimal:
        """Bonds typically trade in par value units."""
        return self.par_value
    
    def get_bond_metrics(self) -> Dict[str, Any]:
        """Get comprehensive bond metrics."""
        return {
            'cusip': self.cusip,
            'issuer': self.issuer,
            'bond_type': self.bond_type,
            'maturity_date': self.maturity_date,
            'issue_date': self.issue_date,
            'days_to_maturity': self.days_to_maturity,
            'coupon_rate': self.coupon_rate * Decimal('100'),  # As percentage
            'payment_frequency': self.payment_frequency,
            'par_value': self.par_value,
            'current_price': self.price,
            'current_yield': self.get_current_yield(),
            'yield_to_maturity': self.yield_to_maturity,
            'yield_to_call': self.yield_to_call,
            'duration': self.duration,
            'modified_duration': self.modified_duration,
            'convexity': self.convexity,
            'credit_rating': self.credit_rating,
            'credit_spread': self.credit_spread,
            'is_investment_grade': self.is_investment_grade(),
            'is_callable': self.is_callable,
            'is_defaulted': self.is_defaulted,
            'accrued_interest': self.accrued_interest,
            'clean_price': self.price - self.accrued_interest,  # Price without accrued interest
            'volatility': self.calculate_volatility(),
        }
    
    def get_next_coupon_date(self) -> Optional[date]:
        """Get the next coupon payment date."""
        today = date.today()
        
        # Simple calculation assuming regular payment schedule
        # In practice, this would use the actual coupon schedule
        if self.maturity_date <= today:
            return None
        
        # Calculate next payment based on frequency
        months_between_payments = 12 // self.payment_frequency
        
        # Find next payment date (simplified)
        current_year = today.year
        current_month = today.month
        
        # This is a simplified calculation
        next_month = current_month + months_between_payments
        next_year = current_year
        
        if next_month > 12:
            next_month -= 12
            next_year += 1
        
        try:
            next_coupon = date(next_year, next_month, self.maturity_date.day)
            return next_coupon if next_coupon > today else None
        except ValueError:
            # Handle month/day combinations that don't exist
            return None
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Bond"
    
    def __str__(self) -> str:
        return f"BondBackTest({self.cusip}, ${self.price}, {self.coupon_rate * 100:.2f}%)"
    
    def __repr__(self) -> str:
        return (f"BondBackTest(cusip={self.cusip}, issuer={self.issuer}, "
                f"price=${self.price}, ytm={self.yield_to_maturity}%)")