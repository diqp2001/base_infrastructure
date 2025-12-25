"""
Currency backtest class extending SecurityBackTest with forex-specific functionality.
Provides exchange rates, carry trade features, and central bank policy tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from src.domain.entities.finance.back_testing.enums import SecurityType
from src.domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from src.domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class InterestRateDifferential:
    """Value object for interest rate differentials between currencies."""
    base_currency_rate: Decimal
    quote_currency_rate: Decimal
    effective_date: datetime
    
    @property
    def differential(self) -> Decimal:
        """Calculate interest rate differential."""
        return self.base_currency_rate - self.quote_currency_rate
    
    def __post_init__(self):
        if self.base_currency_rate < 0 or self.quote_currency_rate < 0:
            raise ValueError("Interest rates cannot be negative")


@dataclass
class CentralBankEvent:
    """Value object for central bank policy events."""
    event_type: str  # e.g., "rate_decision", "policy_announcement"
    impact_level: str  # e.g., "high", "medium", "low"
    event_date: datetime
    description: str
    expected_volatility: Optional[Decimal] = None


class CurrencyBackTest(SecurityBackTest):
    """
    Currency class extending SecurityBackTest with forex-specific functionality.
    Provides exchange rates, carry trade features, and central bank policy tracking.
    """
    
    def __init__(self, id: int, base_currency: str, quote_currency: str, start_date: datetime, end_date: Optional[datetime] = None):
        # Create symbol for base Security class
        pair_symbol = f"{base_currency.upper()}{quote_currency.upper()}"
        symbol = Symbol(
            value=pair_symbol,
            security_type=SecurityType.FOREX
        )
        
        super().__init__(symbol)
        
        # Currency-specific attributes
        self.id = id
        self.base_currency = base_currency.upper()
        self.quote_currency = quote_currency.upper()
        self.start_date = start_date
        self.end_date = end_date
        
        # Forex-specific features
        self._interest_rate_differentials: List[InterestRateDifferential] = []
        self._central_bank_events: List[CentralBankEvent] = []
        self._pip_value = Decimal('0.0001')  # Default pip value
        self._lot_size = Decimal('100000')   # Standard lot size
        self._spread_history: List[Decimal] = []
        
    @property
    def currency_pair(self) -> str:
        """Get currency pair string."""
        return f"{self.base_currency}/{self.quote_currency}"
        
    @property
    def pip_value(self) -> Decimal:
        """Get pip value for this currency pair."""
        return self._pip_value
    
    @property
    def lot_size(self) -> Decimal:
        """Get standard lot size."""
        return self._lot_size
    
    @property
    def current_spread(self) -> Decimal:
        """Get current bid-ask spread."""
        return self._spread_history[-1] if self._spread_history else Decimal('0')
    
    @property
    def interest_rate_differentials(self) -> List[InterestRateDifferential]:
        """Get interest rate differential history."""
        return self._interest_rate_differentials.copy()
    
    def _post_process_data(self, data: MarketData) -> None:
        """Currency-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Track spread if bid/ask available
        if data.bid and data.ask:
            spread = data.ask - data.bid
            self._spread_history.append(spread)
            
            # Keep only last 100 spreads
            if len(self._spread_history) > 100:
                self._spread_history = self._spread_history[-100:]
        
        # Calculate carry trade potential
        self._calculate_carry_trade_return()
    
    def _calculate_carry_trade_return(self) -> None:
        """Calculate potential carry trade returns."""
        if not self._interest_rate_differentials:
            return
            
        latest_diff = self._interest_rate_differentials[-1] if self._interest_rate_differentials else None
        if latest_diff and self.holdings.quantity != 0:
            # Daily carry = (interest differential / 365) * position size
            daily_carry = (latest_diff.differential / Decimal('365')) * abs(self.holdings.quantity)
            # This would be tracked in portfolio performance
    
    def add_interest_rate_differential(self, differential: InterestRateDifferential) -> None:
        """Add interest rate differential data."""
        self._interest_rate_differentials.append(differential)
        self._interest_rate_differentials.sort(key=lambda d: d.effective_date, reverse=True)
        
        # Keep only last 100 entries
        if len(self._interest_rate_differentials) > 100:
            self._interest_rate_differentials = self._interest_rate_differentials[:100]
    
    def add_central_bank_event(self, event: CentralBankEvent) -> None:
        """Add central bank event."""
        self._central_bank_events.append(event)
        self._central_bank_events.sort(key=lambda e: e.event_date, reverse=True)
    
    def set_pip_specifications(self, pip_value: Decimal, lot_size: Decimal) -> None:
        """Set pip value and lot size for this currency pair."""
        self._pip_value = pip_value
        self._lot_size = lot_size
    
    def calculate_pip_value_usd(self, position_size: Decimal) -> Decimal:
        """Calculate pip value in USD for given position size."""
        # Simplified calculation - would need actual exchange rates
        if self.quote_currency == "USD":
            return self._pip_value * position_size
        else:
            # Would need USD exchange rate for quote currency
            return self._pip_value * position_size  # Simplified
    
    def get_current_interest_differential(self) -> Optional[Decimal]:
        """Get current interest rate differential."""
        if self._interest_rate_differentials:
            return self._interest_rate_differentials[0].differential
        return None
    
    def calculate_average_spread(self, periods: int = 20) -> Decimal:
        """Calculate average spread over specified periods."""
        if not self._spread_history:
            return Decimal('0')
            
        recent_spreads = self._spread_history[-periods:] if len(self._spread_history) >= periods else self._spread_history
        return sum(recent_spreads) / len(recent_spreads) if recent_spreads else Decimal('0')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for forex position.
        Typically 1-5% for major currency pairs.
        """
        position_value = abs(quantity * self.price)
        
        # Major pairs typically have lower margin requirements
        major_pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
        pair_code = f"{self.base_currency}{self.quote_currency}"
        
        if pair_code in major_pairs:
            margin_rate = Decimal('0.02')  # 2% for major pairs
        else:
            margin_rate = Decimal('0.05')  # 5% for exotic pairs
            
        return position_value * margin_rate
    
    def get_contract_multiplier(self) -> Decimal:
        """Get contract multiplier (lot size) for forex."""
        return self._lot_size
    
    @property
    def asset_type(self) -> str:
        """Override for backwards compatibility."""
        return "Currency"
    
    def __str__(self) -> str:
        return f"Currency({self.currency_pair}, {self.price})"
    
    def __repr__(self) -> str:
        return (f"Currency(id={self.id}, pair={self.currency_pair}, "
                f"price={self.price}, spread={self.current_spread})")