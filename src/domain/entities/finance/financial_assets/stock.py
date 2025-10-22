"""
Stock class extending Security following QuantConnect Equity architecture.
Provides equity-specific functionality including dividends and stock splits.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from .security import Security, Symbol, SecurityType, MarketData


@dataclass
class Dividend:
    """Value object for dividend payments."""
    amount: Decimal
    ex_date: datetime
    pay_date: Optional[datetime] = None
    record_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Dividend amount cannot be negative")


@dataclass 
class StockSplit:
    """Value object for stock split events."""
    split_ratio: Decimal  # e.g., 2.0 for 2-for-1 split
    ex_date: datetime
    
    def __post_init__(self):
        if self.split_ratio <= 0:
            raise ValueError("Split ratio must be positive")


# FundamentalData class removed - use factors instead


class Stock(Security):
    """
    Stock class extending Security with equity-specific functionality.
    Follows QuantConnect Equity architecture patterns.
    """
    
    def __init__(self, id: int, ticker: str, exchange_id: int, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            ticker=ticker,
            exchange=f"EXCHANGE_{exchange_id}",  # Could be enhanced to lookup actual exchange
            security_type=SecurityType.EQUITY
        )
        
        super().__init__(symbol)
        
        # Stock-specific attributes
        self.id = id
        self.exchange_id = exchange_id
        self.start_date = start_date
        self.end_date = end_date
        
        # fundamentals field removed - use factors instead
        self._dividend_history: List[Dividend] = []
        self._stock_splits: List[StockSplit] = []
        self._sector: Optional[str] = None
        self._industry: Optional[str] = None
        
    @property
    def ticker(self) -> str:
        """Get stock ticker symbol."""
        return self.symbol.ticker
        
    # fundamentals property removed - use factors instead
    
    @property
    def dividend_history(self) -> List[Dividend]:
        """Get dividend payment history."""
        return self._dividend_history.copy()
    
    @property
    def stock_splits(self) -> List[StockSplit]:
        """Get stock split history."""
        return self._stock_splits.copy()
    
    @property
    def sector(self) -> Optional[str]:
        """Get stock sector."""
        return self._sector
    
    @property
    def industry(self) -> Optional[str]:
        """Get stock industry."""
        return self._industry
    
    def _post_process_data(self, data: MarketData) -> None:
        """Stock-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update any dividend-related calculations
        self._update_dividend_metrics()
        
        # Check for corporate actions around this date
        self._check_corporate_actions(data.timestamp)
    
    def _update_dividend_metrics(self) -> None:
        """Update dividend-related metrics from recent data."""
        if not self._dividend_history:
            return
            
        # Calculate trailing dividend yield
        annual_dividends = sum(
            div.amount for div in self._dividend_history 
            if (datetime.now() - div.ex_date).days <= 365
        )
        
        if self.price > 0:
            dividend_yield = (annual_dividends / self.price) * Decimal('100')
            
            # Dividend yield calculation (fundamentals removed)
    
    def _check_corporate_actions(self, date: datetime) -> None:
        """Check if any corporate actions occurred on this date."""
        # Check for stock splits
        for split in self._stock_splits:
            if split.ex_date.date() == date.date():
                self._apply_stock_split(split)
    
    def _apply_stock_split(self, split: StockSplit) -> None:
        """Apply stock split adjustment to price and holdings."""
        # Adjust current price
        self._price = self._price / split.split_ratio
        
        # Adjust holdings if any
        if self.holdings.quantity != 0:
            new_quantity = self.holdings.quantity * split.split_ratio
            new_avg_cost = self.holdings.average_cost / split.split_ratio
            self.update_holdings(new_quantity, new_avg_cost)
    
    def add_dividend(self, dividend: Dividend) -> None:
        """Add a dividend payment to history."""
        self._dividend_history.append(dividend)
        self._dividend_history.sort(key=lambda d: d.ex_date, reverse=True)  # Most recent first
        
        # Update metrics
        self._update_dividend_metrics()
    
    def add_stock_split(self, split: StockSplit) -> None:
        """Add a stock split to history."""
        self._stock_splits.append(split)
        self._stock_splits.sort(key=lambda s: s.ex_date, reverse=True)  # Most recent first
    
    def update_sector_industry(self, sector: Optional[str], industry: Optional[str]) -> None:
        """Update sector and industry information."""
        self._sector = sector
        self._industry = industry
    
    def get_trailing_dividend_yield(self) -> Decimal:
        """Calculate trailing 12-month dividend yield."""
        if self.price <= 0:
            return Decimal('0')
            
        annual_dividends = sum(
            div.amount for div in self._dividend_history
            if (datetime.now() - div.ex_date).days <= 365
        )
        
        return (annual_dividends / self.price) * Decimal('100')
    
    # get_pe_ratio removed - use factors instead
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for stock position.
        Typically 50% for long stock positions, 150% for short.
        """
        position_value = abs(quantity * self.price)
        
        if quantity >= 0:  # Long position
            return position_value * Decimal('0.5')  # 50% margin
        else:  # Short position  
            return position_value * Decimal('1.5')  # 150% margin
    
    def get_contract_multiplier(self) -> Decimal:
        """Stocks have a contract multiplier of 1."""
        return Decimal('1')
    
    def calculate_dividend(self, shares: Optional[Decimal] = None) -> Decimal:
        """Calculate expected dividend payment for given shares."""
        if not shares:
            shares = self.holdings.quantity
            
        if shares <= 0 or not self._dividend_history:
            return Decimal('0')
            
        # Use most recent dividend amount
        latest_dividend = self._dividend_history[0] if self._dividend_history else None
        if not latest_dividend:
            return Decimal('0')
            
        return latest_dividend.amount * shares
    
    @property
    def asset_type(self) -> str:
        """Override from FinancialAsset for backwards compatibility."""
        return "Stock"
    
    def __str__(self) -> str:
        return f"Stock({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Stock(id={self.id}, ticker={self.ticker}, "
                f"price={self.price}, sector={self.sector})")


# Maintain backwards compatibility with existing FinancialAsset interface
from .financial_asset import FinancialAsset

class StockLegacy(FinancialAsset):
    """Legacy Stock class for backwards compatibility."""
    def __init__(self, id, ticker, exchange_id, start_date, end_date):
        super().__init__(id, start_date, end_date)
        self.ticker = ticker
        self.exchange_id = exchange_id

    def calculate_dividend(self):
        pass  # Legacy implementation
  