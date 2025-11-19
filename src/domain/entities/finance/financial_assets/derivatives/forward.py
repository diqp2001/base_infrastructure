"""
Forward Contract classes for forward agreements.
Includes generic Forward Contract and specialized types for different underlying assets.
"""

from typing import Optional
from datetime import date
from decimal import Decimal
from enum import Enum
from .derivative import Derivative, UnderlyingAsset
from ..security import Symbol, SecurityType


class SettlementType(Enum):
    """Settlement types for forward contracts."""
    PHYSICAL = "physical"
    CASH = "cash"


class Forward(Derivative):
    """
    Forward Contract class extending Derivative.
    Handles forward-specific functionality like forward pricing and settlement.
    """
    
    def __init__(self, underlying_asset: UnderlyingAsset, forward_price: Decimal,
                 delivery_date: date, contract_size: Decimal = Decimal('1'),
                 settlement_type: SettlementType = SettlementType.CASH):
        # Create symbol for forward
        symbol = Symbol(
            ticker=f"{underlying_asset.symbol}_FWD_{delivery_date.strftime('%Y%m%d')}",
            exchange="FORWARDS",
            security_type=SecurityType.FORWARD
        )
        
        super().__init__(symbol, underlying_asset, delivery_date, contract_size)
        
        # Forward-specific attributes
        self.forward_price = forward_price
        self.settlement_type = settlement_type
        self.delivery_date = delivery_date  # Same as expiration_date
        
        # Forward metrics
        self._theoretical_forward_price: Optional[Decimal] = None
        self._basis: Optional[Decimal] = None
        
        # Set initial price to zero (forwards have zero initial value)
        self._price = Decimal('0')
    
    @property
    def theoretical_forward_price(self) -> Optional[Decimal]:
        """Get theoretical forward price."""
        return self._theoretical_forward_price
    
    @property
    def basis(self) -> Optional[Decimal]:
        """Get basis (spot price - forward price)."""
        return self._basis
    
    def _calculate_intrinsic_value(self) -> None:
        """Calculate intrinsic value of the forward contract."""
        if self.underlying_asset.current_price is not None:
            # Forward value = (S - K) for long position
            # Where S = current spot price, K = forward price
            self._intrinsic_value = (self.underlying_asset.current_price - 
                                   self.forward_price)
        else:
            self._intrinsic_value = None
        
        # Update basis
        if self.underlying_asset.current_price is not None:
            self._basis = self.underlying_asset.current_price - self.forward_price
    
    def calculate_theoretical_forward_price(self, risk_free_rate: Decimal,
                                          dividend_yield: Optional[Decimal] = None,
                                          storage_cost: Optional[Decimal] = None,
                                          convenience_yield: Optional[Decimal] = None) -> None:
        """Calculate theoretical forward price using cost of carry model."""
        if not self.underlying_asset.current_price or not self.days_to_expiry:
            return
        
        spot_price = self.underlying_asset.current_price
        time_to_delivery = Decimal(self.days_to_expiry) / Decimal('365')
        
        # Cost of carry components
        carry_rate = risk_free_rate
        
        if dividend_yield:
            carry_rate -= dividend_yield
        
        if storage_cost:
            carry_rate += storage_cost
        
        if convenience_yield:
            carry_rate -= convenience_yield
        
        # F = S * e^(r*T) - simplified as F = S * (1 + r*T)
        carry_factor = Decimal('1') + (carry_rate * time_to_delivery)
        self._theoretical_forward_price = spot_price * carry_factor
    
    def calculate_mark_to_market_value(self, current_forward_price: Optional[Decimal] = None) -> Decimal:
        """Calculate mark-to-market value of the forward contract."""
        if not current_forward_price:
            current_forward_price = self._theoretical_forward_price
        
        if not current_forward_price:
            return self._intrinsic_value or Decimal('0')
        
        # MTM value = (current forward price - contracted forward price)
        # Discounted to present value
        price_diff = current_forward_price - self.forward_price
        
        if self.days_to_expiry and self.days_to_expiry > 0:
            # Simple present value calculation (would use proper discounting in practice)
            discount_factor = Decimal('1') - (Decimal(self.days_to_expiry) * Decimal('0.0001'))
            return price_diff * discount_factor
        
        return price_diff
    
    def is_physical_settlement(self) -> bool:
        """Check if contract settles physically."""
        return self.settlement_type == SettlementType.PHYSICAL
    
    def is_cash_settlement(self) -> bool:
        """Check if contract settles in cash."""
        return self.settlement_type == SettlementType.CASH
    
    def calculate_settlement_amount(self) -> Decimal:
        """Calculate settlement amount at delivery."""
        if self.is_expired() and self.underlying_asset.current_price is not None:
            settlement = (self.underlying_asset.current_price - 
                         self.forward_price) * self.contract_size
            return settlement
        
        return Decimal('0')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for forward position.
        Forwards typically require margin based on notional value.
        """
        notional_value = abs(quantity * self.forward_price * self.contract_size)
        return notional_value * Decimal('0.1')  # 10% of notional
    
    def get_forward_metrics(self) -> dict:
        """Get forward-specific metrics."""
        base_metrics = self.get_derivative_metrics()
        base_metrics.update({
            'forward_price': self.forward_price,
            'theoretical_forward_price': self.theoretical_forward_price,
            'basis': self.basis,
            'delivery_date': self.delivery_date,
            'settlement_type': self.settlement_type.value,
            'mark_to_market_value': self.calculate_mark_to_market_value(),
            'settlement_amount': self.calculate_settlement_amount(),
        })
        
        return base_metrics
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "ForwardContract"
    
    def __str__(self) -> str:
        return (f"Forward({self.underlying_asset.symbol}, "
                f"K=${self.forward_price}, delivery:{self.delivery_date})")
    
    def __repr__(self) -> str:
        return (f"ForwardContract(underlying={self.underlying_asset.symbol}, "
                f"forward_price={self.forward_price}, "
                f"delivery_date={self.delivery_date})")


class CommodityForward(Forward):
    """
    Forward contract on commodities with storage and convenience yield considerations.
    """
    
    def __init__(self, commodity_type: str, underlying_asset: UnderlyingAsset,
                 forward_price: Decimal, delivery_date: date,
                 contract_size: Decimal = Decimal('1'),
                 storage_cost: Optional[Decimal] = None,
                 convenience_yield: Optional[Decimal] = None):
        
        super().__init__(underlying_asset, forward_price, delivery_date,
                        contract_size, SettlementType.PHYSICAL)
        
        self.commodity_type = commodity_type
        self.storage_cost = storage_cost or Decimal('0')
        self.convenience_yield = convenience_yield or Decimal('0')
    
    def calculate_theoretical_price_with_costs(self, risk_free_rate: Decimal) -> None:
        """Calculate theoretical forward price including commodity-specific costs."""
        self.calculate_theoretical_forward_price(
            risk_free_rate=risk_free_rate,
            storage_cost=self.storage_cost,
            convenience_yield=self.convenience_yield
        )
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "CommodityForward"


class CurrencyForward(Forward):
    """
    Forward contract on currency pairs with interest rate differential pricing.
    """
    
    def __init__(self, base_currency: str, quote_currency: str,
                 underlying_asset: UnderlyingAsset, forward_rate: Decimal,
                 delivery_date: date, contract_size: Decimal = Decimal('100000')):
        
        super().__init__(underlying_asset, forward_rate, delivery_date,
                        contract_size, SettlementType.CASH)
        
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.forward_rate = forward_rate  # Same as forward_price
    
    def calculate_theoretical_rate(self, domestic_rate: Decimal,
                                 foreign_rate: Decimal) -> None:
        """Calculate theoretical forward rate using interest rate parity."""
        if not self.underlying_asset.current_price or not self.days_to_expiry:
            return
        
        spot_rate = self.underlying_asset.current_price
        time_to_delivery = Decimal(self.days_to_expiry) / Decimal('365')
        
        # Forward rate = Spot * (1 + r_domestic * T) / (1 + r_foreign * T)
        domestic_factor = Decimal('1') + (domestic_rate * time_to_delivery)
        foreign_factor = Decimal('1') + (foreign_rate * time_to_delivery)
        
        self._theoretical_forward_price = spot_rate * (domestic_factor / foreign_factor)
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "CurrencyForward"


# Legacy compatibility
from ..financial_asset import FinancialAsset

class ForwardLegacy(FinancialAsset):
    """Legacy Forward class for backwards compatibility."""
    def __init__(self, ticker: str, name: str, market: str, price: float, 
                 delivery_date: str, forward_price: float):
        super().__init__(ticker, name, market)
        self.price = price
        self.delivery_date = delivery_date
        self.forward_price = forward_price

    def __repr__(self):
        return f"Forward({self.ticker}, {self.name}, {self.price}, {self.delivery_date}, {self.forward_price})"