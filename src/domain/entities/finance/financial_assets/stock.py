from .financial_asset import FinancialAsset
from .security import Security, Symbol, MarketData, Dividend, StockSplit
from decimal import Decimal
from datetime import datetime
from typing import Optional, List

"""Represents a core business concept, typically with behavior and attributes."""
class Stock(FinancialAsset, Security):
    """
    Stock class extending both FinancialAsset (for compatibility) and Security (QuantConnect pattern).
    Represents equity securities with dividend tracking and corporate actions.
    """
    
    def __init__(self, id, ticker, exchange_id, start_date, end_date, 
                 exchange_name: str = "UNKNOWN", market: str = "USA"):
        # Initialize FinancialAsset for backward compatibility
        FinancialAsset.__init__(self, id, start_date, end_date)
        
        # Create Symbol for Security initialization
        symbol = Symbol(
            ticker=ticker,
            exchange=exchange_name,
            security_type="EQUITY",
            market=market
        )
        Security.__init__(self, symbol, id)
        
        # Stock-specific attributes
        self.ticker = ticker
        self.exchange_id = exchange_id
        self._dividends: List[Dividend] = []
        self._stock_splits: List[StockSplit] = []
        self._sector: Optional[str] = None
        self._market_cap: Optional[Decimal] = None
        self._pe_ratio: Optional[Decimal] = None
        
    @property
    def security_type(self) -> str:
        return "EQUITY"
    
    @property
    def asset_type(self):
        """Override from FinancialAsset for backward compatibility"""
        return "Stock"
    
    @property
    def sector(self) -> Optional[str]:
        return self._sector
    
    def set_sector(self, sector: str) -> None:
        """Set the sector for this stock"""
        self._sector = sector
    
    @property
    def market_cap(self) -> Optional[Decimal]:
        return self._market_cap
    
    def set_market_cap(self, market_cap: Decimal) -> None:
        """Set market capitalization"""
        if market_cap < 0:
            raise ValueError("Market cap cannot be negative")
        self._market_cap = market_cap
    
    @property
    def pe_ratio(self) -> Optional[Decimal]:
        return self._pe_ratio
    
    def set_pe_ratio(self, pe_ratio: Decimal) -> None:
        """Set P/E ratio"""
        if pe_ratio < 0:
            raise ValueError("P/E ratio cannot be negative")
        self._pe_ratio = pe_ratio
    
    def add_dividend(self, dividend: Dividend) -> None:
        """Add a dividend to this stock"""
        self._dividends.append(dividend)
        # Sort dividends by ex-date (most recent first)
        self._dividends.sort(key=lambda d: d.ex_date, reverse=True)
    
    def add_stock_split(self, stock_split: StockSplit) -> None:
        """Add a stock split to this stock"""
        self._stock_splits.append(stock_split)
        # Sort splits by ex-date (most recent first)
        self._stock_splits.sort(key=lambda s: s.ex_date, reverse=True)
    
    def get_dividends(self, count: int = 10) -> List[Dividend]:
        """Get recent dividends"""
        return self._dividends[:count]
    
    def get_stock_splits(self, count: int = 10) -> List[StockSplit]:
        """Get recent stock splits"""
        return self._stock_splits[:count]
    
    def calculate_dividend_yield(self) -> Decimal:
        """Calculate annual dividend yield based on current price and recent dividends"""
        if self.current_price == 0 or not self._dividends:
            return Decimal('0.0')
        
        # Calculate annual dividends from last 4 quarters
        annual_dividends = Decimal('0.0')
        current_year = datetime.now().year
        
        for dividend in self._dividends:
            if dividend.ex_date.year >= current_year - 1:
                annual_dividends += dividend.amount
        
        return (annual_dividends / self.current_price) * Decimal('100.0')
    
    def calculate_dividend(self):
        """Legacy method for backward compatibility"""
        return self.calculate_dividend_yield()
    
    def _on_price_update(self, market_data: MarketData) -> None:
        """Handle stock-specific price update logic"""
        # Update market cap if we have shares outstanding
        if self._market_cap and hasattr(self, '_shares_outstanding'):
            self._market_cap = market_data.price * getattr(self, '_shares_outstanding')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement for equity position"""
        # Standard equity margin is 50% for most stocks
        position_value = abs(quantity) * self.current_price
        return position_value * Decimal('0.50')
    
    def __repr__(self):
        return f"Stock({self.ticker}, price={self.current_price}, sector={self._sector})"
  