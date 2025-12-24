"""
Index class extending SecurityBackTest following QuantConnect architecture.
Provides index-specific functionality including constituent tracking and index methodology.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from domain.entities.finance.back_testing.enums import SecurityType, Market
from domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class Constituent:
    """Value object for index constituents."""
    ticker: str
    weight: Decimal
    sector: Optional[str] = None
    market_cap: Optional[Decimal] = None
    added_date: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.weight < 0:
            raise ValueError("Constituent weight cannot be negative")
        if self.weight > Decimal('100'):
            raise ValueError("Constituent weight cannot exceed 100%")


@dataclass
class IndexRebalance:
    """Value object for index rebalancing events."""
    rebalance_date: datetime
    constituents_changed: List[Dict[str, Any]]
    methodology_change: Optional[str] = None
    
    def __post_init__(self):
        if not self.constituents_changed:
            raise ValueError("Rebalance must include constituent changes")


class IndexBackTest(SecurityBackTest):
    """
    Index class extending SecurityBackTest for market indices.
    Handles index-specific functionality like constituent tracking and index methodology.
    """
    
    def __init__(self, index_symbol: str, index_name: str, 
                 methodology: str = "MARKET_CAP_WEIGHTED",
                 base_value: Decimal = Decimal('100'),
                 base_date: Optional[datetime] = None):
        # Create symbol for base SecurityBackTest class
        symbol = Symbol(
            value=index_symbol,
            security_type=SecurityType.INDEX,
            market=Market.USA
        )
        
        super().__init__(symbol)
        
        # Index-specific attributes
        self.index_symbol = index_symbol
        self.index_name = index_name
        self.methodology = methodology  # MARKET_CAP_WEIGHTED, EQUAL_WEIGHTED, PRICE_WEIGHTED
        self.base_value = base_value
        self.base_date = base_date or datetime.now()
        
        # Index composition and metrics
        self._constituents: List[Constituent] = []
        self._sector_weights: Dict[str, Decimal] = {}
        self._market_cap: Optional[Decimal] = None
        self._divisor: Decimal = Decimal('1')  # Index divisor for adjustments
        self._rebalance_history: List[IndexRebalance] = []
        
        # Set initial price to base value if not set
        if self._price == 0:
            self._price = base_value
    
    @property
    def constituents(self) -> List[Constituent]:
        """Get index constituents."""
        return self._constituents.copy()
    
    @property
    def sector_weights(self) -> Dict[str, Decimal]:
        """Get sector weight breakdown."""
        return self._sector_weights.copy()
    
    @property
    def market_cap(self) -> Optional[Decimal]:
        """Get total market capitalization of index."""
        return self._market_cap
    
    @property
    def divisor(self) -> Decimal:
        """Get index divisor."""
        return self._divisor
    
    @property
    def constituent_count(self) -> int:
        """Get number of constituents."""
        return len(self._constituents)
    
    @property
    def rebalance_history(self) -> List[IndexRebalance]:
        """Get rebalancing history."""
        return self._rebalance_history.copy()
    
    def _post_process_data(self, data: MarketData) -> None:
        """Index-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Calculate index performance metrics
        self._update_performance_metrics()
        
        # Check for scheduled rebalancing
        self._check_rebalancing_schedule(data.timestamp)
        
        # Update constituent market values if available
        self._update_constituent_values()
    
    def add_constituent(self, constituent: Constituent) -> None:
        """Add a constituent to the index."""
        # Check if constituent already exists
        for existing in self._constituents:
            if existing.ticker == constituent.ticker:
                raise ValueError(f"Constituent {constituent.ticker} already exists")
        
        self._constituents.append(constituent)
        
        # Update sector weights
        if constituent.sector:
            if constituent.sector in self._sector_weights:
                self._sector_weights[constituent.sector] += constituent.weight
            else:
                self._sector_weights[constituent.sector] = constituent.weight
        
        # Recalculate total market cap
        self._update_market_cap()
    
    def remove_constituent(self, ticker: str) -> bool:
        """Remove a constituent from the index."""
        for i, constituent in enumerate(self._constituents):
            if constituent.ticker == ticker:
                # Update sector weights
                if constituent.sector and constituent.sector in self._sector_weights:
                    self._sector_weights[constituent.sector] -= constituent.weight
                    if self._sector_weights[constituent.sector] <= 0:
                        del self._sector_weights[constituent.sector]
                
                # Remove constituent
                self._constituents.pop(i)
                
                # Recalculate total market cap
                self._update_market_cap()
                return True
        
        return False
    
    def update_constituent_weight(self, ticker: str, new_weight: Decimal) -> bool:
        """Update the weight of a constituent."""
        for constituent in self._constituents:
            if constituent.ticker == ticker:
                old_weight = constituent.weight
                sector = constituent.sector
                
                # Update constituent weight
                constituent.weight = new_weight
                
                # Update sector weight
                if sector and sector in self._sector_weights:
                    self._sector_weights[sector] = (
                        self._sector_weights[sector] - old_weight + new_weight
                    )
                
                return True
        
        return False
    
    def rebalance(self, new_constituents: List[Constituent]) -> None:
        """Rebalance the index with new constituent list."""
        changes = []
        
        # Track changes for history
        old_tickers = {c.ticker for c in self._constituents}
        new_tickers = {c.ticker for c in new_constituents}
        
        # Record additions and removals
        added = new_tickers - old_tickers
        removed = old_tickers - new_tickers
        
        for ticker in added:
            changes.append({"action": "added", "ticker": ticker})
        for ticker in removed:
            changes.append({"action": "removed", "ticker": ticker})
        
        # Clear current constituents and sector weights
        self._constituents.clear()
        self._sector_weights.clear()
        
        # Add new constituents
        for constituent in new_constituents:
            self.add_constituent(constituent)
        
        # Record rebalance event
        rebalance_event = IndexRebalance(
            rebalance_date=datetime.now(),
            constituents_changed=changes
        )
        self._rebalance_history.append(rebalance_event)
    
    def _update_market_cap(self) -> None:
        """Update total market capitalization of the index."""
        total_market_cap = Decimal('0')
        for constituent in self._constituents:
            if constituent.market_cap:
                total_market_cap += constituent.market_cap
        
        self._market_cap = total_market_cap if total_market_cap > 0 else None
    
    def _update_performance_metrics(self) -> None:
        """Update index performance metrics."""
        # Calculate volatility from constituent volatilities
        if len(self._constituents) > 1:
            # Simplified portfolio volatility calculation
            self._update_index_volatility()
    
    def _update_index_volatility(self) -> None:
        """Update index volatility based on constituents."""
        # This would require individual constituent price data
        # For now, use the base security volatility calculation
        pass
    
    def _check_rebalancing_schedule(self, current_time: datetime) -> None:
        """Check if rebalancing is due based on methodology."""
        # This would implement scheduled rebalancing logic
        # e.g., quarterly for many indices
        pass
    
    def _update_constituent_values(self) -> None:
        """Update constituent market values if data available."""
        # This would update individual constituent prices and market caps
        # In a real implementation, this would fetch current market data
        pass
    
    def calculate_return_since_base(self) -> Decimal:
        """Calculate total return since base date."""
        if self.base_value <= 0:
            return Decimal('0')
        
        return ((self.price - self.base_value) / self.base_value) * Decimal('100')
    
    def get_top_constituents(self, n: int = 10) -> List[Constituent]:
        """Get top N constituents by weight."""
        return sorted(self._constituents, key=lambda x: x.weight, reverse=True)[:n]
    
    def get_sector_allocation(self) -> Dict[str, Decimal]:
        """Get current sector allocation as percentages."""
        total_weight = sum(self._sector_weights.values())
        if total_weight == 0:
            return {}
        
        return {
            sector: (weight / total_weight) * Decimal('100')
            for sector, weight in self._sector_weights.items()
        }
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for index position.
        Indices typically cannot be traded directly, but for derivatives:
        Lower margin due to diversification: 10-15%.
        """
        position_value = abs(quantity * self.price)
        return position_value * Decimal('0.15')  # 15% margin
    
    def get_contract_multiplier(self) -> Decimal:
        """Index contracts typically have specific multipliers."""
        # This would vary by index (e.g., S&P 500 has $250 multiplier)
        return Decimal('250')  # Default multiplier
    
    def get_index_metrics(self) -> Dict[str, Any]:
        """Get index-specific metrics."""
        return {
            'index_symbol': self.index_symbol,
            'index_name': self.index_name,
            'methodology': self.methodology,
            'current_level': self.price,
            'base_value': self.base_value,
            'base_date': self.base_date,
            'total_return': self.calculate_return_since_base(),
            'constituent_count': self.constituent_count,
            'market_cap': self.market_cap,
            'divisor': self.divisor,
            'sector_count': len(self._sector_weights),
            'volatility': self.calculate_volatility(),
        }
    
    def is_diversified(self) -> bool:
        """Check if index is properly diversified (no single constituent > 10%)."""
        for constituent in self._constituents:
            if constituent.weight > Decimal('10'):  # 10%
                return False
        return True
    
    def get_performance_attribution(self) -> Dict[str, Decimal]:
        """Calculate performance attribution by sector."""
        # Simplified sector attribution calculation
        sector_returns = {}
        for sector, weight in self._sector_weights.items():
            # This would require individual sector performance data
            # For now, return equal attribution
            sector_returns[sector] = weight
        
        return sector_returns
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Index"
    
    def __str__(self) -> str:
        return f"IndexBackTest({self.index_symbol}, {self.price})"
    
    def __repr__(self) -> str:
        return (f"IndexBackTest(symbol={self.index_symbol}, name='{self.index_name}', "
                f"level={self.price}, constituents={self.constituent_count})")