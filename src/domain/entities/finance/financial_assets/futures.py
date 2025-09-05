"""
Future classes for futures contracts.
Includes base Future class and specialized types: FutureCommodity, BondFuture, IndexFuture.
"""

from typing import Optional
from datetime import date
from decimal import Decimal
from .derivatives import Derivative, UnderlyingAsset
from .security import Symbol, SecurityType


class Future(Derivative):
    """
    Base Future class extending Derivative.
    Handles futures-specific functionality like margin requirements and mark-to-market.
    """
    
    def __init__(self, symbol: Symbol, underlying_asset: UnderlyingAsset,
                 expiration_date: date, contract_size: Decimal = Decimal('1'),
                 tick_size: Decimal = Decimal('0.01'),
                 tick_value: Decimal = Decimal('1')):
        super().__init__(symbol, underlying_asset, expiration_date, contract_size)
        
        # Futures-specific attributes
        self.tick_size = tick_size  # Minimum price movement
        self.tick_value = tick_value  # Value of one tick
        
        # Futures metrics
        self._initial_margin: Optional[Decimal] = None
        self._maintenance_margin: Optional[Decimal] = None
        self._daily_settlement_price: Optional[Decimal] = None
        
    @property
    def initial_margin(self) -> Optional[Decimal]:
        """Get initial margin requirement."""
        return self._initial_margin
    
    @property
    def maintenance_margin(self) -> Optional[Decimal]:
        """Get maintenance margin requirement."""
        return self._maintenance_margin
    
    @property
    def daily_settlement_price(self) -> Optional[Decimal]:
        """Get daily settlement price for mark-to-market."""
        return self._daily_settlement_price
    
    def set_margin_requirements(self, initial_margin: Decimal, 
                              maintenance_margin: Decimal) -> None:
        """Set margin requirements for the futures contract."""
        if initial_margin < 0 or maintenance_margin < 0:
            raise ValueError("Margin requirements cannot be negative")
        if maintenance_margin > initial_margin:
            raise ValueError("Maintenance margin cannot exceed initial margin")
        
        self._initial_margin = initial_margin
        self._maintenance_margin = maintenance_margin
    
    def set_daily_settlement_price(self, settlement_price: Decimal) -> None:
        """Set daily settlement price for mark-to-market calculation."""
        self._daily_settlement_price = settlement_price
    
    def _calculate_intrinsic_value(self) -> None:
        """
        For futures, intrinsic value is the difference between underlying and forward price.
        Simplified calculation - in practice would use risk-free rate and dividends.
        """
        if self.underlying_asset.current_price is not None:
            # Simplified: intrinsic value approximates underlying price
            self._intrinsic_value = self.underlying_asset.current_price
        else:
            self._intrinsic_value = None
    
    def calculate_daily_pnl(self, previous_settlement: Decimal, 
                          position_quantity: Decimal) -> Decimal:
        """Calculate daily P&L based on settlement prices."""
        if not self._daily_settlement_price:
            return Decimal('0')
        
        price_change = self._daily_settlement_price - previous_settlement
        return price_change * position_quantity * self.contract_size
    
    def calculate_margin_call_threshold(self, position_quantity: Decimal) -> Optional[Decimal]:
        """Calculate price level that would trigger a margin call."""
        if not self._maintenance_margin or not self._daily_settlement_price:
            return None
        
        # Simplified calculation
        margin_per_contract = self._maintenance_margin / abs(position_quantity)
        
        if position_quantity > 0:  # Long position
            return self._daily_settlement_price - (margin_per_contract / self.contract_size)
        else:  # Short position
            return self._daily_settlement_price + (margin_per_contract / self.contract_size)
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement for futures position."""
        if self._initial_margin:
            return self._initial_margin * abs(quantity)
        else:
            # Default calculation based on contract value
            contract_value = self.price * self.contract_size
            return contract_value * Decimal('0.05') * abs(quantity)  # 5% default
    
    def get_tick_details(self) -> dict:
        """Get tick size and value information."""
        return {
            'tick_size': self.tick_size,
            'tick_value': self.tick_value,
            'minimum_price_change': self.tick_size,
            'value_per_tick': self.tick_value,
        }
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Future"


class FutureCommodity(Future):
    """
    Commodity futures contract.
    Handles commodity-specific features like storage costs and seasonality.
    """
    
    def __init__(self, commodity_type: str, underlying_asset: UnderlyingAsset,
                 expiration_date: date, contract_size: Decimal = Decimal('1'),
                 delivery_location: Optional[str] = None,
                 storage_cost: Optional[Decimal] = None):
        # Create symbol for futures
        symbol = Symbol(
            ticker=f"{commodity_type}_FUT",
            exchange="COMMODITY",
            security_type=SecurityType.FUTURE
        )
        
        super().__init__(symbol, underlying_asset, expiration_date, contract_size)
        
        # Commodity-specific attributes
        self.commodity_type = commodity_type  # "GOLD", "OIL", "WHEAT", etc.
        self.delivery_location = delivery_location
        self.storage_cost = storage_cost or Decimal('0')
        
    def calculate_storage_adjusted_price(self) -> Optional[Decimal]:
        """Calculate price adjusted for storage costs."""
        if not self.days_to_expiry or not self.storage_cost:
            return None
        
        # Annual storage cost adjusted for time to expiry
        storage_adjustment = (self.storage_cost * Decimal(self.days_to_expiry)) / Decimal('365')
        return self.price + storage_adjustment
    
    def is_deliverable(self) -> bool:
        """Check if contract allows for physical delivery."""
        return self.delivery_location is not None and not self.is_expired()
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "CommodityFuture"


class BondFuture(Future):
    """
    Bond futures contract.
    Handles bond-specific features like duration and yield sensitivity.
    """
    
    def __init__(self, bond_type: str, underlying_asset: UnderlyingAsset,
                 expiration_date: date, contract_size: Decimal = Decimal('100000'),
                 notional_bond_coupon: Optional[Decimal] = None):
        # Create symbol for bond futures
        symbol = Symbol(
            ticker=f"{bond_type}_BOND_FUT",
            exchange="BOND_FUTURES",
            security_type=SecurityType.FUTURE
        )
        
        super().__init__(symbol, underlying_asset, expiration_date, contract_size)
        
        # Bond futures specific attributes
        self.bond_type = bond_type  # "10Y_TREASURY", "30Y_TREASURY", etc.
        self.notional_bond_coupon = notional_bond_coupon or Decimal('0.06')  # 6% standard
        
        # Bond futures metrics
        self._conversion_factor: Optional[Decimal] = None
        self._cheapest_to_deliver: Optional[str] = None
        
    @property
    def conversion_factor(self) -> Optional[Decimal]:
        """Get conversion factor for the deliverable bond."""
        return self._conversion_factor
    
    @property
    def cheapest_to_deliver(self) -> Optional[str]:
        """Get the cheapest-to-deliver bond identifier."""
        return self._cheapest_to_deliver
    
    def set_conversion_factor(self, factor: Decimal) -> None:
        """Set conversion factor for deliverable bond."""
        if factor <= 0:
            raise ValueError("Conversion factor must be positive")
        self._conversion_factor = factor
    
    def set_cheapest_to_deliver(self, bond_identifier: str) -> None:
        """Set the cheapest-to-deliver bond."""
        self._cheapest_to_deliver = bond_identifier
    
    def calculate_adjusted_price(self) -> Optional[Decimal]:
        """Calculate price adjusted for conversion factor."""
        if self._conversion_factor:
            return self.price * self._conversion_factor
        return None
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "BondFuture"


class IndexFuture(Future):
    """
    Index futures contract.
    Handles index-specific features like multipliers and dividend adjustments.
    """
    
    def __init__(self, index_name: str, underlying_asset: UnderlyingAsset,
                 expiration_date: date, contract_size: Decimal = Decimal('250'),
                 index_multiplier: Decimal = Decimal('250')):
        # Create symbol for index futures
        symbol = Symbol(
            ticker=f"{index_name}_FUT",
            exchange="INDEX_FUTURES",
            security_type=SecurityType.FUTURE
        )
        
        super().__init__(symbol, underlying_asset, expiration_date, contract_size)
        
        # Index futures specific attributes
        self.index_name = index_name  # "SP500", "NASDAQ", "DOW", etc.
        self.index_multiplier = index_multiplier
        
        # Index futures metrics
        self._fair_value: Optional[Decimal] = None
        self._dividend_adjustment: Decimal = Decimal('0')
        
    @property
    def fair_value(self) -> Optional[Decimal]:
        """Get theoretical fair value of the futures contract."""
        return self._fair_value
    
    @property
    def dividend_adjustment(self) -> Decimal:
        """Get dividend adjustment amount."""
        return self._dividend_adjustment
    
    def calculate_fair_value(self, risk_free_rate: Decimal, 
                           dividend_yield: Decimal = Decimal('0')) -> None:
        """Calculate theoretical fair value using cost of carry model."""
        if not self.underlying_asset.current_price or not self.days_to_expiry:
            return
        
        # Time to expiry in years
        time_to_expiry = Decimal(self.days_to_expiry) / Decimal('365')
        
        # Cost of carry model: F = S * e^((r-q)*T)
        # Simplified calculation without exponential
        carry_cost = (risk_free_rate - dividend_yield) * time_to_expiry
        self._fair_value = self.underlying_asset.current_price * (Decimal('1') + carry_cost)
    
    def set_dividend_adjustment(self, adjustment: Decimal) -> None:
        """Set dividend adjustment for the contract."""
        self._dividend_adjustment = adjustment
    
    def calculate_basis(self) -> Optional[Decimal]:
        """Calculate basis (futures price - spot price)."""
        if self.underlying_asset.current_price:
            return self.price - self.underlying_asset.current_price
        return None
    
    def get_contract_multiplier(self) -> Decimal:
        """Override to return index-specific multiplier."""
        return self.index_multiplier
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "IndexFuture"