"""
ETF Share backtest class extending ShareBackTest with ETF-specific functionality.
Provides NAV tracking, creation/redemption features, and basket composition.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from domain.entities.finance.back_testing.financial_assets.share_backtest import ShareBackTest
from domain.entities.finance.back_testing.financial_assets.symbol import Symbol
from domain.entities.finance.back_testing.enums import SecurityType


@dataclass
class NAVCalculation:
    """Value object for Net Asset Value calculations."""
    nav_per_share: Decimal
    total_net_assets: Decimal
    shares_outstanding: Decimal
    calculation_date: datetime
    
    def __post_init__(self):
        if self.nav_per_share < 0:
            raise ValueError("NAV per share cannot be negative")
        if self.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive")


@dataclass
class BasketHolding:
    """Value object for ETF basket holdings."""
    symbol: str
    quantity: Decimal
    market_value: Decimal
    weight_percentage: Decimal
    last_updated: datetime
    
    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.weight_percentage < 0 or self.weight_percentage > 100:
            raise ValueError("Weight percentage must be between 0 and 100")


@dataclass
class CreationRedemption:
    """Value object for creation/redemption events."""
    event_type: str  # "creation" or "redemption"
    shares_amount: Decimal
    nav_price: Decimal
    event_date: datetime
    authorized_participant: str
    
    def __post_init__(self):
        if self.event_type not in ["creation", "redemption"]:
            raise ValueError("Event type must be 'creation' or 'redemption'")
        if self.shares_amount <= 0:
            raise ValueError("Shares amount must be positive")


class ETFShareBackTest(ShareBackTest):
    """
    ETF Share class extending ShareBackTest with ETF-specific functionality.
    Provides NAV tracking, creation/redemption features, and basket composition.
    """
    
    def __init__(self, id: int, etf_ticker: str, fund_family: str, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            value=etf_ticker.upper(),
            security_type=SecurityType.EQUITY  # ETF shares trade as equity
        )
        
        # Initialize as Share with ETF-specific parameters
        super().__init__(id, "ETF", hash(fund_family), start_date, end_date)
        
        # Override symbol after initialization
        self._symbol = symbol
        
        # ETF-specific attributes
        self.etf_ticker = etf_ticker.upper()
        self.fund_family = fund_family
        
        # ETF-specific features
        self._nav_history: List[NAVCalculation] = []
        self._basket_holdings: List[BasketHolding] = []
        self._creation_redemption_history: List[CreationRedemption] = []
        self._expense_ratio: Optional[Decimal] = None
        self._tracking_index: Optional[str] = None
        self._premium_discount_history: List[Decimal] = []
        
    @property
    def ticker_symbol(self) -> str:
        """Get ETF ticker symbol."""
        return self.etf_ticker
        
    @property
    def current_nav(self) -> Optional[Decimal]:
        """Get most recent NAV per share."""
        return self._nav_history[-1].nav_per_share if self._nav_history else None
    
    @property
    def expense_ratio(self) -> Optional[Decimal]:
        """Get expense ratio."""
        return self._expense_ratio
    
    @property
    def tracking_index(self) -> Optional[str]:
        """Get tracking index."""
        return self._tracking_index
    
    @property
    def current_premium_discount(self) -> Optional[Decimal]:
        """Get current premium/discount to NAV."""
        return self._premium_discount_history[-1] if self._premium_discount_history else None
    
    @property
    def basket_holdings(self) -> List[BasketHolding]:
        """Get current basket holdings."""
        return self._basket_holdings.copy()
    
    def _post_process_data(self, data: "MarketData") -> None:
        """ETF-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Calculate premium/discount to NAV
        self._calculate_premium_discount()
        
        # Update expense ratio impact
        self._apply_expense_ratio_impact()
    
    def _calculate_premium_discount(self) -> None:
        """Calculate premium/discount to NAV."""
        current_nav = self.current_nav
        if current_nav and self.price > 0:
            premium_discount = ((self.price - current_nav) / current_nav) * Decimal('100')
            self._premium_discount_history.append(premium_discount)
            
            # Keep only last 100 calculations
            if len(self._premium_discount_history) > 100:
                self._premium_discount_history = self._premium_discount_history[-100:]
    
    def _apply_expense_ratio_impact(self) -> None:
        """Apply expense ratio impact to performance."""
        if self._expense_ratio and self.holdings.quantity > 0:
            # Daily expense impact = (expense ratio / 365) * market value
            daily_expense = (self._expense_ratio / Decimal('365')) * self.holdings.market_value
            # This would be tracked in portfolio performance
    
    def add_nav_calculation(self, nav_calc: NAVCalculation) -> None:
        """Add NAV calculation."""
        self._nav_history.append(nav_calc)
        self._nav_history.sort(key=lambda n: n.calculation_date, reverse=True)
        
        # Keep only last 100 NAV calculations
        if len(self._nav_history) > 100:
            self._nav_history = self._nav_history[:100]
    
    def update_basket_holdings(self, holdings: List[BasketHolding]) -> None:
        """Update basket holdings composition."""
        self._basket_holdings = holdings.copy()
        
        # Validate that weights sum to approximately 100%
        total_weight = sum(holding.weight_percentage for holding in self._basket_holdings)
        if abs(total_weight - Decimal('100')) > Decimal('1'):  # Allow 1% tolerance
            print(f"Warning: Basket weights sum to {total_weight}%, not 100%")
    
    def add_creation_redemption(self, event: CreationRedemption) -> None:
        """Add creation/redemption event."""
        self._creation_redemption_history.append(event)
        self._creation_redemption_history.sort(key=lambda e: e.event_date, reverse=True)
        
        # Keep only last 50 events
        if len(self._creation_redemption_history) > 50:
            self._creation_redemption_history = self._creation_redemption_history[:50]
    
    def set_fund_details(self, expense_ratio: Decimal, tracking_index: str) -> None:
        """Set fund expense ratio and tracking index."""
        if expense_ratio < 0:
            raise ValueError("Expense ratio cannot be negative")
        self._expense_ratio = expense_ratio
        self._tracking_index = tracking_index
    
    def get_holding_weight(self, symbol: str) -> Optional[Decimal]:
        """Get weight of specific holding in basket."""
        for holding in self._basket_holdings:
            if holding.symbol.upper() == symbol.upper():
                return holding.weight_percentage
        return None
    
    def calculate_tracking_error(self, index_returns: List[Decimal], etf_returns: List[Decimal]) -> Optional[Decimal]:
        """Calculate tracking error vs benchmark index."""
        if len(index_returns) != len(etf_returns) or len(index_returns) < 2:
            return None
            
        return_differences = [etf_ret - idx_ret for etf_ret, idx_ret in zip(etf_returns, index_returns)]
        
        if not return_differences:
            return None
            
        # Calculate standard deviation of return differences
        mean_diff = sum(return_differences) / len(return_differences)
        variance = sum((diff - mean_diff) ** 2 for diff in return_differences) / len(return_differences)
        tracking_error = variance ** Decimal('0.5')
        
        return tracking_error * Decimal('100')  # Convert to percentage
    
    def get_average_premium_discount(self, periods: int = 30) -> Optional[Decimal]:
        """Calculate average premium/discount over specified periods."""
        if not self._premium_discount_history:
            return None
            
        recent_data = self._premium_discount_history[-periods:] if len(self._premium_discount_history) >= periods else self._premium_discount_history
        return sum(recent_data) / len(recent_data) if recent_data else None
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for ETF position.
        Generally lower than individual stocks due to diversification.
        """
        position_value = abs(quantity * self.price)
        
        # ETFs typically have lower margin requirements
        margin_rate = Decimal('0.25')  # 25% for ETFs
        
        if quantity >= 0:  # Long position
            return position_value * margin_rate
        else:  # Short position
            return position_value * (margin_rate + Decimal('0.15'))
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "ETF"
    
    def __str__(self) -> str:
        return f"ETF({self.etf_ticker}, ${self.price}, NAV:{self.current_nav})"
    
    def __repr__(self) -> str:
        return (f"ETF(id={self.id}, ticker={self.etf_ticker}, "
                f"price={self.price}, nav={self.current_nav}, "
                f"expense_ratio={self.expense_ratio})")