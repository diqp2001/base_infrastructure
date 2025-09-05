"""
Index class for market index securities.
Extends Security with index-specific functionality and characteristics.
"""

from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from .security import Security, Symbol, SecurityType, MarketData


class Index(Security):
    """
    Index class extending Security for market indices.
    Handles index-specific functionality like constituent tracking and index methodology.
    """
    
    def __init__(self, index_symbol: str, index_name: str, 
                 methodology: str = "MARKET_CAP_WEIGHTED",
                 base_value: Decimal = Decimal('100'),
                 base_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            ticker=index_symbol,
            exchange="INDEX",
            security_type=SecurityType.INDEX
        )
        
        super().__init__(symbol)
        
        # Index-specific attributes
        self.index_symbol = index_symbol
        self.index_name = index_name
        self.methodology = methodology  # MARKET_CAP_WEIGHTED, EQUAL_WEIGHTED, PRICE_WEIGHTED
        self.base_value = base_value
        self.base_date = base_date or datetime.now()
        
        # Index composition and metrics
        self._constituents: List[Dict] = []  # List of constituent securities
        self._sector_weights: Dict[str, Decimal] = {}
        self._market_cap: Optional[Decimal] = None
        self._divisor: Decimal = Decimal('1')  # Index divisor for adjustments
        
        # Set initial price to base value if not set
        if self._price == 0:
            self._price = base_value
    
    @property
    def constituents(self) -> List[Dict]:
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
    
    def _post_process_data(self, data: MarketData) -> None:
        """Index-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Calculate index performance metrics
        self._update_performance_metrics()
        
        # Index-specific processing could include:
        # - Rebalancing alerts
        # - Constituent weight updates
        # - Sector allocation changes
    
    def add_constituent(self, ticker: str, weight: Decimal, 
                       sector: Optional[str] = None, 
                       market_cap: Optional[Decimal] = None) -> None:
        """Add a constituent to the index."""
        constituent = {
            'ticker': ticker,
            'weight': weight,
            'sector': sector,
            'market_cap': market_cap,
            'added_date': datetime.now()
        }
        
        self._constituents.append(constituent)
        
        # Update sector weights
        if sector:
            if sector in self._sector_weights:
                self._sector_weights[sector] += weight
            else:
                self._sector_weights[sector] = weight
        
        # Recalculate total market cap
        self._update_market_cap()
    
    def remove_constituent(self, ticker: str) -> None:
        """Remove a constituent from the index."""
        for i, constituent in enumerate(self._constituents):
            if constituent['ticker'] == ticker:
                # Update sector weights
                sector = constituent.get('sector')
                if sector and sector in self._sector_weights:
                    self._sector_weights[sector] -= constituent['weight']
                    if self._sector_weights[sector] <= 0:
                        del self._sector_weights[sector]
                
                # Remove constituent
                self._constituents.pop(i)
                break
        
        # Recalculate total market cap
        self._update_market_cap()
    
    def update_constituent_weight(self, ticker: str, new_weight: Decimal) -> None:
        """Update the weight of a constituent."""
        for constituent in self._constituents:
            if constituent['ticker'] == ticker:
                old_weight = constituent['weight']
                sector = constituent.get('sector')
                
                # Update constituent weight
                constituent['weight'] = new_weight
                
                # Update sector weight
                if sector and sector in self._sector_weights:
                    self._sector_weights[sector] = (
                        self._sector_weights[sector] - old_weight + new_weight
                    )
                
                break
    
    def rebalance(self, new_weights: Dict[str, Decimal]) -> None:
        """Rebalance the index with new constituent weights."""
        # Update constituent weights
        for constituent in self._constituents:
            ticker = constituent['ticker']
            if ticker in new_weights:
                old_weight = constituent['weight']
                new_weight = new_weights[ticker]
                
                constituent['weight'] = new_weight
                
                # Update sector weights
                sector = constituent.get('sector')
                if sector and sector in self._sector_weights:
                    self._sector_weights[sector] = (
                        self._sector_weights[sector] - old_weight + new_weight
                    )
    
    def _update_market_cap(self) -> None:
        """Update total market capitalization of the index."""
        total_market_cap = Decimal('0')
        for constituent in self._constituents:
            market_cap = constituent.get('market_cap')
            if market_cap:
                total_market_cap += market_cap
        
        self._market_cap = total_market_cap if total_market_cap > 0 else None
    
    def _update_performance_metrics(self) -> None:
        """Update index performance metrics."""
        # This could include calculating:
        # - Index return since base date
        # - Volatility metrics
        # - Sector performance attribution
        pass
    
    def calculate_return_since_base(self) -> Decimal:
        """Calculate total return since base date."""
        if self.base_value <= 0:
            return Decimal('0')
        
        return ((self.price - self.base_value) / self.base_value) * Decimal('100')
    
    def get_top_constituents(self, n: int = 10) -> List[Dict]:
        """Get top N constituents by weight."""
        sorted_constituents = sorted(
            self._constituents, 
            key=lambda x: x['weight'], 
            reverse=True
        )
        return sorted_constituents[:n]
    
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
    
    def get_index_metrics(self) -> dict:
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
        }
    
    def is_diversified(self) -> bool:
        """Check if index is properly diversified (no single constituent > 10%)."""
        for constituent in self._constituents:
            if constituent['weight'] > Decimal('10'):  # 10%
                return False
        return True
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Index"
    
    def __str__(self) -> str:
        return f"Index({self.index_symbol}, {self.price})"
    
    def __repr__(self) -> str:
        return (f"Index(symbol={self.index_symbol}, name='{self.index_name}', "
                f"level={self.price}, constituents={self.constituent_count})")


# Legacy compatibility
from .financial_asset import FinancialAsset

class IndexLegacy(FinancialAsset):
    """Legacy Index class for backwards compatibility."""
    def __init__(self, ticker: str, name: str, market: str, level: float):
        super().__init__(ticker, name, market)
        self.level = level  # Index level (e.g., S&P 500)

    def __repr__(self):
        return f"Index({self.ticker}, {self.name}, {self.level})"