"""
Swap classes for swap contracts.
Includes Interest Rate Swaps, Currency Swaps, and other swap instruments.
"""

from typing import Optional, List, Dict
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from .derivatives import Derivative, UnderlyingAsset
from .security import Symbol, SecurityType


class SwapType(Enum):
    """Types of swap contracts."""
    INTEREST_RATE = "interest_rate"
    CURRENCY = "currency"
    CREDIT_DEFAULT = "credit_default"
    COMMODITY = "commodity"
    EQUITY = "equity"


class PaymentFrequency(Enum):
    """Payment frequency for swap legs."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


@dataclass
class SwapLeg:
    """Value object representing one leg of a swap."""
    leg_type: str  # "FIXED", "FLOATING"
    rate: Optional[Decimal] = None  # Fixed rate or spread
    reference_rate: Optional[str] = None  # "LIBOR", "SOFR", etc. for floating
    payment_frequency: PaymentFrequency = PaymentFrequency.QUARTERLY
    notional_amount: Decimal = Decimal('1000000')
    
    def __post_init__(self):
        if self.notional_amount <= 0:
            raise ValueError("Notional amount must be positive")


class Swap(Derivative):
    """
    Base Swap class extending Derivative.
    Handles swap-specific functionality like payment calculations and valuation.
    """
    
    def __init__(self, swap_type: SwapType, pay_leg: SwapLeg, receive_leg: SwapLeg,
                 start_date: date, maturity_date: date,
                 underlying_asset: Optional[UnderlyingAsset] = None):
        # Create dummy underlying if not provided
        if not underlying_asset:
            underlying_asset = UnderlyingAsset(
                symbol="SWAP_UNDERLYING",
                asset_type="RATE",
                current_price=Decimal('0')
            )
        
        # Create symbol for swap
        symbol = Symbol(
            ticker=f"{swap_type.value.upper()}_SWAP",
            exchange="SWAPS",
            security_type=SecurityType.SWAP
        )
        
        super().__init__(symbol, underlying_asset, maturity_date, Decimal('1'))
        
        # Swap-specific attributes
        self.swap_type = swap_type
        self.pay_leg = pay_leg
        self.receive_leg = receive_leg
        self.start_date = start_date
        
        # Swap metrics
        self._present_value: Optional[Decimal] = None
        self._duration: Optional[Decimal] = None
        self._dv01: Optional[Decimal] = None  # Dollar value of 1 basis point
        
    @property
    def present_value(self) -> Optional[Decimal]:
        """Get present value of the swap."""
        return self._present_value
    
    @property
    def duration(self) -> Optional[Decimal]:
        """Get modified duration of the swap."""
        return self._duration
    
    @property
    def dv01(self) -> Optional[Decimal]:
        """Get dollar value of 1 basis point change."""
        return self._dv01
    
    def _calculate_intrinsic_value(self) -> None:
        """Calculate intrinsic value of the swap."""
        # For swaps, intrinsic value is typically the present value
        if self._present_value is not None:
            self._intrinsic_value = self._present_value
        else:
            self._intrinsic_value = Decimal('0')
    
    def calculate_payment_dates(self) -> List[date]:
        """Calculate payment dates for the swap."""
        payment_dates = []
        
        # Use the more frequent payment schedule
        pay_freq = self.pay_leg.payment_frequency
        receive_freq = self.receive_leg.payment_frequency
        
        # Convert enum to months
        freq_months = {
            PaymentFrequency.MONTHLY: 1,
            PaymentFrequency.QUARTERLY: 3,
            PaymentFrequency.SEMI_ANNUALLY: 6,
            PaymentFrequency.ANNUALLY: 12
        }
        
        # Use the more frequent schedule
        months_increment = min(freq_months[pay_freq], freq_months[receive_freq])
        
        current_date = self.start_date
        while current_date <= self.expiration_date:
            if current_date > self.start_date:  # Skip start date
                payment_dates.append(current_date)
            
            # Add months (simplified - doesn't handle month-end conventions)
            year = current_date.year
            month = current_date.month + months_increment
            day = current_date.day
            
            while month > 12:
                year += 1
                month -= 12
            
            try:
                current_date = date(year, month, day)
            except ValueError:
                # Handle end-of-month dates
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                current_date = date(year, month, min(day, last_day))
        
        return payment_dates
    
    def calculate_fixed_payment(self, notional: Decimal, rate: Decimal,
                              days_in_period: int) -> Decimal:
        """Calculate fixed leg payment for a period."""
        # Simplified calculation: (rate * notional * days) / 360
        return (rate * notional * Decimal(str(days_in_period))) / Decimal('360')
    
    def calculate_floating_payment(self, notional: Decimal, floating_rate: Decimal,
                                 days_in_period: int) -> Decimal:
        """Calculate floating leg payment for a period."""
        # Similar to fixed payment but with floating rate
        return (floating_rate * notional * Decimal(str(days_in_period))) / Decimal('360')
    
    def update_present_value(self, pv: Decimal) -> None:
        """Update present value of the swap."""
        self._present_value = pv
        self._price = pv  # Update base class price
        self._calculate_intrinsic_value()
    
    def update_risk_metrics(self, duration: Optional[Decimal] = None,
                          dv01: Optional[Decimal] = None) -> None:
        """Update risk metrics."""
        if duration is not None:
            self._duration = duration
        if dv01 is not None:
            self._dv01 = dv01
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement for swap position."""
        # Swaps typically have lower margin due to bilateral collateral
        notional_value = max(self.pay_leg.notional_amount, self.receive_leg.notional_amount)
        return notional_value * Decimal('0.02') * abs(quantity)  # 2% of notional
    
    def get_swap_metrics(self) -> dict:
        """Get swap-specific metrics."""
        base_metrics = self.get_derivative_metrics()
        base_metrics.update({
            'swap_type': self.swap_type.value,
            'start_date': self.start_date,
            'maturity_date': self.expiration_date,
            'pay_leg_type': self.pay_leg.leg_type,
            'pay_leg_rate': self.pay_leg.rate,
            'receive_leg_type': self.receive_leg.leg_type,
            'receive_leg_rate': self.receive_leg.rate,
            'pay_notional': self.pay_leg.notional_amount,
            'receive_notional': self.receive_leg.notional_amount,
            'present_value': self.present_value,
            'duration': self.duration,
            'dv01': self.dv01,
        })
        
        return base_metrics
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Swap"
    
    def __str__(self) -> str:
        return f"Swap({self.swap_type.value}, PV=${self.present_value})"
    
    def __repr__(self) -> str:
        return (f"Swap(type={self.swap_type.value}, "
                f"start={self.start_date}, maturity={self.expiration_date}, "
                f"pv=${self.present_value})")


class InterestRateSwap(Swap):
    """
    Interest Rate Swap - exchanges fixed for floating interest payments.
    """
    
    def __init__(self, fixed_rate: Decimal, floating_reference: str,
                 notional_amount: Decimal, start_date: date, maturity_date: date,
                 payment_frequency: PaymentFrequency = PaymentFrequency.QUARTERLY):
        
        # Create swap legs
        fixed_leg = SwapLeg(
            leg_type="FIXED",
            rate=fixed_rate,
            payment_frequency=payment_frequency,
            notional_amount=notional_amount
        )
        
        floating_leg = SwapLeg(
            leg_type="FLOATING",
            reference_rate=floating_reference,
            payment_frequency=payment_frequency,
            notional_amount=notional_amount
        )
        
        super().__init__(SwapType.INTEREST_RATE, fixed_leg, floating_leg,
                        start_date, maturity_date)
        
        self.fixed_rate = fixed_rate
        self.floating_reference = floating_reference
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "InterestRateSwap"


class CurrencySwap(Swap):
    """
    Currency Swap - exchanges principal and interest payments in different currencies.
    """
    
    def __init__(self, base_currency: str, quote_currency: str,
                 base_notional: Decimal, quote_notional: Decimal,
                 base_rate: Decimal, quote_rate: Decimal,
                 start_date: date, maturity_date: date,
                 exchange_rate: Decimal):
        
        # Create swap legs in different currencies
        base_leg = SwapLeg(
            leg_type="FIXED",
            rate=base_rate,
            notional_amount=base_notional
        )
        
        quote_leg = SwapLeg(
            leg_type="FIXED", 
            rate=quote_rate,
            notional_amount=quote_notional
        )
        
        super().__init__(SwapType.CURRENCY, base_leg, quote_leg,
                        start_date, maturity_date)
        
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.exchange_rate = exchange_rate
    
    def update_exchange_rate(self, new_rate: Decimal) -> None:
        """Update the exchange rate for valuation."""
        self.exchange_rate = new_rate
        # Would trigger revaluation in practice
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "CurrencySwap"