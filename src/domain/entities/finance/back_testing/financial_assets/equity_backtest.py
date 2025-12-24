"""
Equity backtest class extending SecurityBackTest with equity-specific functionality.
Provides market cap calculations, beta analysis, and equity trading features.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from domain.entities.finance.back_testing.enums import SecurityType
from domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class MarketCapData:
    """Value object for market capitalization data."""
    shares_outstanding: Decimal
    market_cap: Decimal
    calculation_date: datetime
    
    def __post_init__(self):
        if self.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive")
        if self.market_cap < 0:
            raise ValueError("Market cap cannot be negative")


@dataclass
class BetaCalculation:
    """Value object for beta calculation data."""
    beta_value: Decimal
    correlation_coefficient: Decimal
    calculation_period_days: int
    benchmark_symbol: str
    calculation_date: datetime


class EquityBackTest(SecurityBackTest):
    """
    Equity class extending SecurityBackTest with equity-specific functionality.
    Provides market cap calculations, beta analysis, and equity trading features.
    """
    
    def __init__(self, id: int, ticker: str, exchange_id: int, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            value=ticker.upper(),
            security_type=SecurityType.EQUITY
        )
        
        super().__init__(symbol)
        
        # Equity-specific attributes
        self.id = id
        self.ticker = ticker.upper()
        self.exchange_id = exchange_id
        self.start_date = start_date
        self.end_date = end_date
        
        # Equity-specific features
        self._market_cap_history: List[MarketCapData] = []
        self._beta_calculations: List[BetaCalculation] = []
        self._shares_outstanding: Optional[Decimal] = None
        self._sector: Optional[str] = None
        self._industry: Optional[str] = None
        self._market_cap_category: Optional[str] = None  # "large", "mid", "small"
        
    @property
    def equity_ticker(self) -> str:
        """Get equity ticker symbol."""
        return self.ticker
        
    @property
    def shares_outstanding(self) -> Optional[Decimal]:
        """Get current shares outstanding."""
        return self._shares_outstanding
    
    @property
    def current_market_cap(self) -> Optional[Decimal]:
        """Calculate current market capitalization."""
        if self._shares_outstanding and self.price > 0:
            return self._shares_outstanding * self.price
        return None
    
    @property
    def market_cap_category(self) -> Optional[str]:
        """Get market cap category (large/mid/small cap)."""
        return self._market_cap_category
    
    @property
    def sector(self) -> Optional[str]:
        """Get sector classification."""
        return self._sector
    
    @property
    def industry(self) -> Optional[str]:
        """Get industry classification."""
        return self._industry
    
    def _post_process_data(self, data: MarketData) -> None:
        """Equity-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update market cap if shares outstanding is known
        self._update_market_cap(data.timestamp)
        
        # Update market cap category classification
        self._update_market_cap_category()
    
    def _update_market_cap(self, current_date: datetime) -> None:
        """Update market capitalization calculation."""
        if self._shares_outstanding and self.price > 0:
            market_cap = self._shares_outstanding * self.price
            
            cap_data = MarketCapData(
                shares_outstanding=self._shares_outstanding,
                market_cap=market_cap,
                calculation_date=current_date
            )
            
            self._market_cap_history.append(cap_data)
            
            # Keep only last 100 entries
            if len(self._market_cap_history) > 100:
                self._market_cap_history = self._market_cap_history[-100:]
    
    def _update_market_cap_category(self) -> None:
        """Update market cap category based on current market cap."""
        current_cap = self.current_market_cap
        if current_cap is None:
            return
            
        # Standard market cap categories (in millions)
        if current_cap >= Decimal('10000000000'):  # $10B+
            self._market_cap_category = "large"
        elif current_cap >= Decimal('2000000000'):  # $2B - $10B
            self._market_cap_category = "mid"
        else:  # < $2B
            self._market_cap_category = "small"
    
    def update_shares_outstanding(self, shares: Decimal) -> None:
        """Update shares outstanding."""
        if shares <= 0:
            raise ValueError("Shares outstanding must be positive")
        self._shares_outstanding = shares
    
    def update_sector_industry(self, sector: Optional[str], industry: Optional[str]) -> None:
        """Update sector and industry classification."""
        self._sector = sector
        self._industry = industry
    
    def add_beta_calculation(self, beta: BetaCalculation) -> None:
        """Add beta calculation result."""
        self._beta_calculations.append(beta)
        self._beta_calculations.sort(key=lambda b: b.calculation_date, reverse=True)
        
        # Keep only last 20 calculations
        if len(self._beta_calculations) > 20:
            self._beta_calculations = self._beta_calculations[:20]
    
    def get_current_beta(self, benchmark: str = "SPY") -> Optional[Decimal]:
        """Get most recent beta calculation for specified benchmark."""
        for beta_calc in self._beta_calculations:
            if beta_calc.benchmark_symbol.upper() == benchmark.upper():
                return beta_calc.beta_value
        return None
    
    def calculate_book_to_market(self, book_value_per_share: Decimal) -> Optional[Decimal]:
        """Calculate book-to-market ratio."""
        if self.price <= 0:
            return None
        return book_value_per_share / self.price
    
    def calculate_price_to_book(self, book_value_per_share: Decimal) -> Optional[Decimal]:
        """Calculate price-to-book ratio."""
        if book_value_per_share <= 0:
            return None
        return self.price / book_value_per_share
    
    def get_market_cap_percentile(self, comparison_universe: List[Decimal]) -> Optional[Decimal]:
        """Calculate market cap percentile within comparison universe."""
        current_cap = self.current_market_cap
        if current_cap is None or not comparison_universe:
            return None
            
        sorted_caps = sorted(comparison_universe)
        rank = sum(1 for cap in sorted_caps if cap <= current_cap)
        return Decimal(str(rank)) / Decimal(str(len(sorted_caps))) * Decimal('100')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for equity position.
        Varies by market cap and volatility.
        """
        position_value = abs(quantity * self.price)
        
        # Higher margin for smaller cap stocks
        if self._market_cap_category == "large":
            margin_rate = Decimal('0.25')  # 25% for large cap
        elif self._market_cap_category == "mid":
            margin_rate = Decimal('0.30')  # 30% for mid cap
        else:
            margin_rate = Decimal('0.50')  # 50% for small cap
        
        if quantity >= 0:  # Long position
            return position_value * margin_rate
        else:  # Short position (higher requirement)
            return position_value * (margin_rate + Decimal('0.25'))
    
    def get_contract_multiplier(self) -> Decimal:
        """Equity has a contract multiplier of 1."""
        return Decimal('1')
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "Equity"
    
    def __str__(self) -> str:
        return f"Equity({self.ticker}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Equity(id={self.id}, ticker={self.ticker}, "
                f"price={self.price}, market_cap={self.current_market_cap}, "
                f"sector={self.sector})")