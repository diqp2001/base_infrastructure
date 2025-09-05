"""
ETFShare class for Exchange-Traded Fund shares.
Extends Share with ETF-specific functionality and characteristics.
"""

from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
from .share import Share, FundamentalData, MarketData
from .security import Symbol, SecurityType


class ETFShare(Share):
    """
    ETFShare extends Share to provide ETF-specific functionality.
    Handles basket composition, tracking error, and ETF-specific metrics.
    """
    
    def __init__(self, id: int, ticker: str, exchange_id: int, 
                 start_date: datetime, underlying_index: Optional[str] = None,
                 expense_ratio: Optional[Decimal] = None, end_date: Optional[datetime] = None):
        super().__init__(id, ticker, exchange_id, start_date, end_date)
        
        # ETF-specific attributes
        self.underlying_index = underlying_index
        self.expense_ratio = expense_ratio or Decimal('0.0')
        self._nav: Optional[Decimal] = None  # Net Asset Value
        self._premium_discount: Optional[Decimal] = None
        self._creation_units: int = 50000  # Standard creation unit size
        self._holdings_basket: List[Dict] = []  # Underlying holdings
        
    @property
    def nav(self) -> Optional[Decimal]:
        """Get Net Asset Value."""
        return self._nav
    
    @property
    def premium_discount(self) -> Optional[Decimal]:
        """Get premium/discount to NAV as percentage."""
        return self._premium_discount
    
    @property
    def creation_units(self) -> int:
        """Get creation unit size."""
        return self._creation_units
    
    @property
    def holdings_basket(self) -> List[Dict]:
        """Get underlying holdings basket."""
        return self._holdings_basket.copy()
    
    def update_nav(self, nav: Decimal) -> None:
        """Update Net Asset Value and calculate premium/discount."""
        self._nav = nav
        
        if self.price > 0 and nav > 0:
            self._premium_discount = ((self.price - nav) / nav) * Decimal('100')
    
    def _post_process_data(self, data: MarketData) -> None:
        """ETF-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Calculate premium/discount if NAV is available
        if self._nav:
            self._premium_discount = ((data.price - self._nav) / self._nav) * Decimal('100')
        
        # ETF-specific processing could include:
        # - Tracking error calculation
        # - Liquidity metrics update
        # - Arbitrage opportunity detection
    
    def update_holdings_basket(self, holdings: List[Dict]) -> None:
        """Update the underlying holdings basket."""
        self._holdings_basket = holdings.copy()
    
    def calculate_tracking_error(self, index_returns: List[Decimal], 
                               periods: int = 30) -> Optional[Decimal]:
        """Calculate tracking error against underlying index."""
        if len(self._price_history) < periods or len(index_returns) < periods:
            return None
        
        # Calculate ETF returns
        recent_prices = [data.price for data in self._price_history[-periods:]]
        if len(recent_prices) < 2:
            return None
        
        etf_returns = []
        for i in range(1, len(recent_prices)):
            ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            etf_returns.append(ret)
        
        if len(etf_returns) != len(index_returns[-len(etf_returns):]):
            return None
        
        # Calculate tracking differences
        tracking_diffs = []
        for i in range(len(etf_returns)):
            diff = etf_returns[i] - index_returns[-(len(etf_returns)-i)]
            tracking_diffs.append(diff)
        
        # Calculate standard deviation of tracking differences
        if len(tracking_diffs) < 2:
            return None
        
        mean_diff = sum(tracking_diffs) / len(tracking_diffs)
        variance = sum((diff - mean_diff) ** 2 for diff in tracking_diffs) / len(tracking_diffs)
        tracking_error = variance ** Decimal('0.5')
        
        return tracking_error * Decimal('100')  # Convert to percentage
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for ETF position.
        Similar to equities: 50% for long, 150% for short.
        """
        position_value = abs(quantity * self.price)
        
        if quantity >= 0:  # Long position
            return position_value * Decimal('0.5')  # 50% margin
        else:  # Short position  
            return position_value * Decimal('1.5')  # 150% margin
    
    def get_etf_metrics(self) -> dict:
        """Get ETF-specific metrics."""
        metrics = {
            'ticker': self.ticker,
            'underlying_index': self.underlying_index,
            'expense_ratio': self.expense_ratio,
            'nav': self.nav,
            'premium_discount': self.premium_discount,
            'current_price': self.price,
            'creation_units': self.creation_units,
            'holdings_count': len(self._holdings_basket),
            'sector': self.sector,
            'industry': self.industry,
        }
        
        return metrics
    
    def is_in_premium(self) -> bool:
        """Check if ETF is trading at a premium to NAV."""
        return self._premium_discount is not None and self._premium_discount > 0
    
    def is_in_discount(self) -> bool:
        """Check if ETF is trading at a discount to NAV."""
        return self._premium_discount is not None and self._premium_discount < 0
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "ETFShare"
    
    def __str__(self) -> str:
        return f"ETFShare({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        nav_info = f", NAV=${self.nav}" if self.nav else ""
        premium_info = f", P/D={self.premium_discount:.2f}%" if self.premium_discount else ""
        
        return (f"ETFShare(id={self.id}, ticker={self.ticker}, "
                f"price=${self.price}{nav_info}{premium_info})")