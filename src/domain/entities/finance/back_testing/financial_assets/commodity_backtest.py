"""
Commodity backtest class extending SecurityBackTest with commodity-specific functionality.
Provides storage costs, seasonal patterns, and commodity futures features.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from src.domain.entities.finance.back_testing.enums import SecurityType
from src.domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from src.domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class StorageCost:
    """Value object for commodity storage costs."""
    cost_per_unit: Decimal
    period_start: datetime
    period_end: datetime
    storage_type: str  # e.g., "warehouse", "tank", "silo"
    
    def __post_init__(self):
        if self.cost_per_unit < 0:
            raise ValueError("Storage cost cannot be negative")
        if self.period_end <= self.period_start:
            raise ValueError("Period end must be after period start")


@dataclass
class SeasonalPattern:
    """Value object for commodity seasonal price patterns."""
    month: int
    seasonal_multiplier: Decimal
    confidence_level: Decimal
    
    def __post_init__(self):
        if not 1 <= self.month <= 12:
            raise ValueError("Month must be between 1 and 12")
        if self.seasonal_multiplier <= 0:
            raise ValueError("Seasonal multiplier must be positive")


class CommodityBackTest(SecurityBackTest):
    """
    Commodity class extending SecurityBackTest with commodity-specific functionality.
    Provides storage costs, seasonal patterns, and commodity futures features.
    """
    
    def __init__(self, id: int, commodity_name: str, exchange_id: int, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            value=commodity_name.upper(),
            security_type=SecurityType.COMMODITY
        )
        
        super().__init__(symbol)
        
        # Commodity-specific attributes
        self.id = id
        self.commodity_name = commodity_name
        self.exchange_id = exchange_id
        self.start_date = start_date
        self.end_date = end_date
        
        # Commodity-specific features
        self._storage_costs: List[StorageCost] = []
        self._seasonal_patterns: List[SeasonalPattern] = []
        self._contract_unit = "metric_ton"  # Default unit
        self._delivery_months: List[int] = []  # Months when delivery is possible
        self._quality_grade: Optional[str] = None
        
    @property
    def commodity_type(self) -> str:
        """Get commodity name."""
        return self.commodity_name
        
    @property
    def storage_costs(self) -> List[StorageCost]:
        """Get storage cost history."""
        return self._storage_costs.copy()
    
    @property
    def seasonal_patterns(self) -> List[SeasonalPattern]:
        """Get seasonal pattern data."""
        return self._seasonal_patterns.copy()
    
    @property
    def contract_unit(self) -> str:
        """Get contract unit."""
        return self._contract_unit
    
    @property
    def delivery_months(self) -> List[int]:
        """Get delivery months."""
        return self._delivery_months.copy()
    
    def _post_process_data(self, data: MarketData) -> None:
        """Commodity-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Apply seasonal adjustments
        self._apply_seasonal_adjustment(data.timestamp)
        
        # Calculate storage costs if holding inventory
        self._calculate_storage_costs(data.timestamp)
    
    def _apply_seasonal_adjustment(self, current_date: datetime) -> None:
        """Apply seasonal price adjustments based on patterns."""
        current_month = current_date.month
        
        for pattern in self._seasonal_patterns:
            if pattern.month == current_month:
                # This would affect price forecasting in a real system
                seasonal_effect = pattern.seasonal_multiplier
                break
    
    def _calculate_storage_costs(self, current_date: datetime) -> None:
        """Calculate storage costs for current holdings."""
        if self.holdings.quantity <= 0:
            return
            
        # Calculate applicable storage costs
        for storage in self._storage_costs:
            if storage.period_start <= current_date <= storage.period_end:
                daily_storage_cost = storage.cost_per_unit * self.holdings.quantity
                # This would be tracked in portfolio costs
    
    def add_storage_cost(self, storage: StorageCost) -> None:
        """Add storage cost information."""
        self._storage_costs.append(storage)
        self._storage_costs.sort(key=lambda s: s.period_start)
    
    def add_seasonal_pattern(self, pattern: SeasonalPattern) -> None:
        """Add seasonal price pattern."""
        # Remove existing pattern for same month
        self._seasonal_patterns = [p for p in self._seasonal_patterns if p.month != pattern.month]
        self._seasonal_patterns.append(pattern)
        self._seasonal_patterns.sort(key=lambda p: p.month)
    
    def set_contract_specifications(self, unit: str, delivery_months: List[int], quality_grade: str = None) -> None:
        """Set contract specifications."""
        self._contract_unit = unit
        self._delivery_months = delivery_months
        self._quality_grade = quality_grade
    
    def get_seasonal_multiplier(self, month: int) -> Decimal:
        """Get seasonal multiplier for a specific month."""
        for pattern in self._seasonal_patterns:
            if pattern.month == month:
                return pattern.seasonal_multiplier
        return Decimal('1.0')  # No seasonal effect
    
    def calculate_total_storage_cost(self, quantity: Decimal, days: int) -> Decimal:
        """Calculate total storage cost for given quantity and period."""
        if not self._storage_costs:
            return Decimal('0')
            
        # Use most recent storage cost rate
        latest_storage = self._storage_costs[-1] if self._storage_costs else None
        if not latest_storage:
            return Decimal('0')
            
        return latest_storage.cost_per_unit * quantity * Decimal(str(days))
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for commodity position.
        Typically higher than stocks due to volatility.
        """
        position_value = abs(quantity * self.price)
        
        # Commodities typically require 5-20% margin
        margin_rate = Decimal('0.10')  # 10% default
        return position_value * margin_rate
    
    def get_contract_multiplier(self) -> Decimal:
        """Get contract multiplier based on commodity type."""
        # This would vary by commodity type
        commodity_multipliers = {
            "GOLD": Decimal('100'),    # 100 oz
            "SILVER": Decimal('5000'), # 5000 oz
            "OIL": Decimal('1000'),    # 1000 barrels
            "WHEAT": Decimal('5000'),  # 5000 bushels
        }
        
        return commodity_multipliers.get(self.commodity_name.upper(), Decimal('1'))
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "Commodity"
    
    def __str__(self) -> str:
        return f"Commodity({self.commodity_name}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Commodity(id={self.id}, name={self.commodity_name}, "
                f"price={self.price}, unit={self.contract_unit})")