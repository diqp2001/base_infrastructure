"""
Enhanced Stock domain entity inheriting from Security base class.
Represents equity securities with stock-specific functionality.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from dataclasses import dataclass

from .security import Security, Symbol, SecurityType, MarketData


@dataclass(frozen=True)
class Dividend:
    """Value object for dividend payments."""
    amount: Decimal
    ex_date: datetime
    pay_date: datetime
    record_date: datetime
    currency: str = "USD"


@dataclass(frozen=True)
class StockSplit:
    """Value object for stock splits."""
    ratio: Decimal  # e.g., 2.0 for 2:1 split
    effective_date: datetime
    announcement_date: datetime


class Stock(Security):
    """
    Enhanced Stock domain entity following QuantConnect Equity pattern.
    Represents equity securities with stock-specific behavior.
    """
    
    def __init__(self,
                 id: int,
                 ticker: str,
                 exchange_id: int,
                 start_date: datetime,
                 end_date: Optional[datetime] = None,
                 sector: Optional[str] = None,
                 industry: Optional[str] = None,
                 market_cap: Optional[Decimal] = None,
                 shares_outstanding: Optional[int] = None,
                 leverage: Decimal = Decimal('1.0')):
        """
        Initialize a Stock entity.
        
        Args:
            id: Unique identifier
            ticker: Stock ticker symbol
            exchange_id: Exchange identifier
            start_date: Data start date
            end_date: Data end date (optional)
            sector: Business sector
            industry: Industry classification
            market_cap: Market capitalization
            shares_outstanding: Number of shares outstanding
            leverage: Trading leverage
        """
        # Create symbol object
        symbol = Symbol(ticker=ticker, security_id=str(id), exchange=str(exchange_id))
        
        # Initialize base Security
        super().__init__(
            id=id,
            symbol=symbol,
            security_type=SecurityType.EQUITY,
            start_date=start_date,
            end_date=end_date,
            leverage=leverage
        )
        
        # Stock-specific properties
        self.exchange_id = exchange_id
        self.sector = sector
        self.industry = industry
        self.market_cap = market_cap
        self.shares_outstanding = shares_outstanding
        
        # Corporate actions history
        self.dividend_history: List[Dividend] = []
        self.split_history: List[StockSplit] = []
    
    @property
    def asset_type(self) -> str:
        """Return asset type for compatibility."""
        return "STOCK"
    
    def _validate_security_specific_data(self, market_data: MarketData) -> None:
        """Stock-specific validation for market data."""
        if market_data.price and self.current_price:
            # Check for circuit breaker (20% price change)
            change_percent = abs(market_data.price - self.current_price) / self.current_price
            if change_percent > Decimal('0.20'):
                raise ValueError(f"Price change {change_percent:.2%} exceeds circuit breaker for {self.ticker}")
    
    def calculate_dividend_yield(self) -> Decimal:
        """Calculate current dividend yield based on last 12 months."""
        if not self.dividend_history or not self.current_price:
            return Decimal('0')
        
        # Get last 12 months of dividends
        now = datetime.now()
        one_year_ago = datetime(now.year - 1, now.month, now.day)
        
        annual_dividends = sum(
            div.amount for div in self.dividend_history 
            if div.ex_date >= one_year_ago
        )
        
        return (annual_dividends / self.current_price) * 100 if annual_dividends > 0 else Decimal('0')
    
    def add_dividend(self, dividend: Dividend) -> None:
        """Add a dividend payment to history."""
        if dividend.amount <= 0:
            raise ValueError("Dividend amount must be positive")
        
        self.dividend_history.append(dividend)
        # Keep sorted by ex_date
        self.dividend_history.sort(key=lambda d: d.ex_date, reverse=True)
    
    def apply_stock_split(self, split: StockSplit) -> None:
        """Apply stock split adjustments."""
        if split.ratio <= 0:
            raise ValueError("Split ratio must be positive")
        
        # Adjust shares outstanding
        if self.shares_outstanding:
            self.shares_outstanding = int(self.shares_outstanding * split.ratio)
        
        # Add to split history
        self.split_history.append(split)
        self.split_history.sort(key=lambda s: s.effective_date, reverse=True)
    
    def calculate_market_cap(self) -> Optional[Decimal]:
        """Calculate current market capitalization."""
        if self.current_price and self.shares_outstanding:
            return self.current_price * Decimal(self.shares_outstanding)
        return self.market_cap
    
    def get_pe_ratio(self, earnings_per_share: Decimal) -> Optional[Decimal]:
        """Calculate price-to-earnings ratio."""
        if earnings_per_share <= 0 or not self.current_price:
            return None
        return self.current_price / earnings_per_share
    
    def is_dividend_paying(self) -> bool:
        """Check if stock pays dividends."""
        return len(self.dividend_history) > 0
    
    def get_latest_dividend(self) -> Optional[Dividend]:
        """Get the most recent dividend payment."""
        return self.dividend_history[0] if self.dividend_history else None
    
    def calculate_dividend(self) -> Decimal:
        """Legacy method for backward compatibility."""
        return self.calculate_dividend_yield()
    
    def __repr__(self) -> str:
        return f"<Stock({self.ticker}, {self.sector or 'Unknown'})>"
  