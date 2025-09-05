"""
Option classes for options contracts.
Includes base Option class and specialized types for different option strategies.
"""

from typing import Optional
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
from .derivatives import Derivative, UnderlyingAsset
from .security import Symbol, SecurityType


class OptionType(Enum):
    """Option types."""
    CALL = "call"
    PUT = "put"


@dataclass
class Greeks:
    """Value object for option Greeks."""
    delta: Optional[Decimal] = None      # Price sensitivity to underlying
    gamma: Optional[Decimal] = None      # Delta sensitivity to underlying
    theta: Optional[Decimal] = None      # Time decay
    vega: Optional[Decimal] = None       # Volatility sensitivity
    rho: Optional[Decimal] = None        # Interest rate sensitivity
    
    def __str__(self) -> str:
        return (f"Greeks(Δ={self.delta}, Γ={self.gamma}, "
                f"Θ={self.theta}, ν={self.vega}, ρ={self.rho})")


class Option(Derivative):
    """
    Base Option class extending Derivative.
    Handles options-specific functionality like Greeks, moneyness, and exercise features.
    """
    
    def __init__(self, underlying_asset: UnderlyingAsset, strike_price: Decimal,
                 expiration_date: date, option_type: OptionType,
                 contract_size: Decimal = Decimal('100'),  # Standard option contract
                 exercise_style: str = "AMERICAN"):
        # Create symbol for option
        option_ticker = (f"{underlying_asset.symbol}_{strike_price}_"
                        f"{option_type.value.upper()}_{expiration_date.strftime('%Y%m%d')}")
        symbol = Symbol(
            ticker=option_ticker,
            exchange="OPTIONS",
            security_type=SecurityType.OPTION
        )
        
        super().__init__(symbol, underlying_asset, expiration_date, contract_size)
        
        # Option-specific attributes
        self.strike_price = strike_price
        self.option_type = option_type
        self.exercise_style = exercise_style  # "AMERICAN", "EUROPEAN"
        
        # Option metrics
        self._greeks: Optional[Greeks] = None
        self._implied_volatility: Optional[Decimal] = None
        self._moneyness: Optional[str] = None
        
    @property
    def greeks(self) -> Optional[Greeks]:
        """Get option Greeks."""
        return self._greeks
    
    @property
    def implied_volatility(self) -> Optional[Decimal]:
        """Get implied volatility."""
        return self._implied_volatility
    
    @property
    def moneyness(self) -> Optional[str]:
        """Get moneyness classification."""
        return self._moneyness
    
    def _calculate_intrinsic_value(self) -> None:
        """Calculate intrinsic value of the option."""
        if self.underlying_asset.current_price is None:
            self._intrinsic_value = None
            return
        
        underlying_price = self.underlying_asset.current_price
        
        if self.option_type == OptionType.CALL:
            # Call: max(S - K, 0)
            self._intrinsic_value = max(underlying_price - self.strike_price, Decimal('0'))
        else:  # PUT
            # Put: max(K - S, 0)
            self._intrinsic_value = max(self.strike_price - underlying_price, Decimal('0'))
        
        # Update moneyness
        self._update_moneyness()
    
    def _update_moneyness(self) -> None:
        """Update moneyness classification."""
        if self.underlying_asset.current_price is None:
            self._moneyness = None
            return
        
        underlying_price = self.underlying_asset.current_price
        
        if self.option_type == OptionType.CALL:
            if underlying_price > self.strike_price:
                self._moneyness = "ITM"  # In-the-money
            elif underlying_price == self.strike_price:
                self._moneyness = "ATM"  # At-the-money
            else:
                self._moneyness = "OTM"  # Out-of-the-money
        else:  # PUT
            if underlying_price < self.strike_price:
                self._moneyness = "ITM"
            elif underlying_price == self.strike_price:
                self._moneyness = "ATM"
            else:
                self._moneyness = "OTM"
    
    def get_moneyness(self) -> Optional[str]:
        """Get moneyness classification."""
        return self._moneyness
    
    def update_greeks(self, greeks: Greeks) -> None:
        """Update option Greeks."""
        self._greeks = greeks
    
    def update_implied_volatility(self, iv: Decimal) -> None:
        """Update implied volatility."""
        if iv < 0:
            raise ValueError("Implied volatility cannot be negative")
        self._implied_volatility = iv
    
    def calculate_simple_delta(self) -> Optional[Decimal]:
        """Calculate a simplified delta approximation."""
        if (not self.underlying_asset.current_price or 
            not self.days_to_expiry or self.days_to_expiry <= 0):
            return None
        
        # Very simplified delta calculation
        if self._moneyness == "ATM":
            return Decimal('0.5') if self.option_type == OptionType.CALL else Decimal('-0.5')
        elif self._moneyness == "ITM":
            return Decimal('0.8') if self.option_type == OptionType.CALL else Decimal('-0.8')
        else:  # OTM
            return Decimal('0.2') if self.option_type == OptionType.CALL else Decimal('-0.2')
    
    def calculate_simple_theta(self) -> Optional[Decimal]:
        """Calculate simplified theta (time decay)."""
        if not self.time_value or not self.days_to_expiry or self.days_to_expiry <= 0:
            return None
        
        # Very simplified theta: -time_value / days_to_expiry
        return -self.time_value / Decimal(str(self.days_to_expiry))
    
    def is_in_the_money(self) -> bool:
        """Check if option is in-the-money."""
        return self._moneyness == "ITM"
    
    def is_at_the_money(self) -> bool:
        """Check if option is at-the-money."""
        return self._moneyness == "ATM"
    
    def is_out_of_the_money(self) -> bool:
        """Check if option is out-of-the-money."""
        return self._moneyness == "OTM"
    
    def can_exercise(self) -> bool:
        """Check if option can be exercised."""
        if self.is_expired():
            return False
        
        # American options can be exercised anytime before expiry
        if self.exercise_style == "AMERICAN":
            return True
        
        # European options can only be exercised at expiry
        return self.days_to_expiry == 0
    
    def calculate_exercise_value(self) -> Decimal:
        """Calculate value if exercised immediately."""
        return self._intrinsic_value or Decimal('0')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for option position.
        Different rules for long vs short positions.
        """
        position_value = abs(quantity * self.price * self.contract_size)
        
        if quantity > 0:  # Long option
            # Long options require full premium payment
            return position_value
        else:  # Short option
            # Short options have complex margin requirements
            if not self.underlying_asset.current_price:
                return position_value * Decimal('0.2')  # 20% fallback
            
            underlying_value = abs(quantity) * self.underlying_asset.current_price * self.contract_size
            
            if self.option_type == OptionType.CALL:
                # Short call margin
                margin = Decimal('0.2') * underlying_value  # 20% of underlying
                margin = max(margin, position_value)  # At least premium received
            else:  # Short put
                # Short put margin  
                strike_value = abs(quantity) * self.strike_price * self.contract_size
                margin = Decimal('0.2') * strike_value  # 20% of strike value
                margin = max(margin, position_value)  # At least premium received
            
            return margin
    
    def get_option_metrics(self) -> dict:
        """Get option-specific metrics."""
        base_metrics = self.get_derivative_metrics()
        base_metrics.update({
            'strike_price': self.strike_price,
            'option_type': self.option_type.value,
            'exercise_style': self.exercise_style,
            'moneyness': self.moneyness,
            'implied_volatility': self.implied_volatility,
            'can_exercise': self.can_exercise(),
            'exercise_value': self.calculate_exercise_value(),
            'simple_delta': self.calculate_simple_delta(),
            'simple_theta': self.calculate_simple_theta(),
        })
        
        if self._greeks:
            base_metrics.update({
                'delta': self._greeks.delta,
                'gamma': self._greeks.gamma,
                'theta': self._greeks.theta,
                'vega': self._greeks.vega,
                'rho': self._greeks.rho,
            })
        
        return base_metrics
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Option"
    
    def __str__(self) -> str:
        return (f"Option({self.underlying_asset.symbol} {self.strike_price} "
                f"{self.option_type.value.upper()} {self.expiration_date}, ${self.price})")
    
    def __repr__(self) -> str:
        return (f"Option(underlying={self.underlying_asset.symbol}, "
                f"strike={self.strike_price}, type={self.option_type.value}, "
                f"expiry={self.expiration_date}, price=${self.price})")


# Legacy compatibility
from .financial_asset import FinancialAsset

class OptionLegacy(FinancialAsset):
    """Legacy Option class for backwards compatibility."""
    def __init__(self, ticker: str, name: str, market: str, price: float, 
                 expiration_date: str, strike_price: float, option_type: str):
        super().__init__(ticker, name, market)
        self.price = price
        self.expiration_date = expiration_date
        self.strike_price = strike_price
        self.option_type = option_type

    def __repr__(self):
        return f"Option({self.ticker}, {self.name}, {self.price}, {self.expiration_date}, {self.strike_price}, {self.option_type})"