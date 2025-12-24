"""
Crypto class extending SecurityBackTest following QuantConnect architecture.
Provides crypto-specific functionality including staking, mining rewards, and volatility.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from domain.entities.finance.back_testing.enums import SecurityType, Market
from domain.entities.finance.back_testing.financial_assets.security_backtest import MarketData, SecurityBackTest
from domain.entities.finance.back_testing.financial_assets.symbol import Symbol


@dataclass
class StakingReward:
    """Value object for staking rewards."""
    amount: Decimal
    reward_date: datetime
    apy: Decimal  # Annual percentage yield at time of reward
    validator: Optional[str] = None
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Staking reward amount cannot be negative")
        if self.apy < 0:
            raise ValueError("Staking APY cannot be negative")


@dataclass
class NetworkEvent:
    """Value object for blockchain network events."""
    event_type: str  # 'upgrade', 'fork', 'halving', 'burn'
    event_date: datetime
    description: str
    impact_on_supply: Optional[Decimal] = None
    
    def __post_init__(self):
        valid_types = ['upgrade', 'fork', 'halving', 'burn', 'mint', 'airdrop']
        if self.event_type not in valid_types:
            raise ValueError(f"Event type must be one of: {valid_types}")


class CryptoBackTest(SecurityBackTest):
    """
    Crypto class extending SecurityBackTest for cryptocurrency assets.
    Handles crypto-specific functionality like staking, mining rewards, and volatility.
    """
    
    def __init__(self, symbol_code: str, base_currency: str = "USD", 
                 blockchain: Optional[str] = None, 
                 consensus_mechanism: Optional[str] = None,
                 market: Market = Market.BINANCE):
        # Create symbol for base SecurityBackTest class
        symbol = Symbol(
            value=f"{symbol_code}{base_currency}",
            security_type=SecurityType.CRYPTO,
            market=market
        )
        
        super().__init__(symbol)
        
        # Crypto-specific attributes
        self.symbol_code = symbol_code
        self.base_currency = base_currency
        self.blockchain = blockchain
        self.consensus_mechanism = consensus_mechanism
        
        # Crypto metrics
        self._market_cap: Optional[Decimal] = None
        self._circulating_supply: Optional[Decimal] = None
        self._max_supply: Optional[Decimal] = None
        self._staking_apy: Optional[Decimal] = None
        self._network_hash_rate: Optional[Decimal] = None
        
        # Crypto-specific collections
        self._staking_rewards: List[StakingReward] = []
        self._network_events: List[NetworkEvent] = []
        
        # Crypto-specific volatility is typically higher
        self._high_volatility_threshold = Decimal('0.2')  # 20% daily moves
        self._extreme_volatility_threshold = Decimal('0.5')  # 50% daily moves
        
        # Mining/staking info
        self._is_stakeable: bool = False
        self._is_mineable: bool = False
        self._total_staked: Optional[Decimal] = None
    
    @property
    def market_cap(self) -> Optional[Decimal]:
        """Get cryptocurrency market capitalization."""
        return self._market_cap
    
    @property
    def circulating_supply(self) -> Optional[Decimal]:
        """Get circulating supply of coins/tokens."""
        return self._circulating_supply
    
    @property
    def max_supply(self) -> Optional[Decimal]:
        """Get maximum possible supply of coins/tokens."""
        return self._max_supply
    
    @property
    def staking_apy(self) -> Optional[Decimal]:
        """Get staking annual percentage yield."""
        return self._staking_apy
    
    @property
    def network_hash_rate(self) -> Optional[Decimal]:
        """Get network hash rate (for PoW cryptocurrencies)."""
        return self._network_hash_rate
    
    @property
    def staking_rewards(self) -> List[StakingReward]:
        """Get staking rewards history."""
        return self._staking_rewards.copy()
    
    @property
    def network_events(self) -> List[NetworkEvent]:
        """Get blockchain network events history."""
        return self._network_events.copy()
    
    @property
    def is_stakeable(self) -> bool:
        """Whether this crypto can be staked."""
        return self._is_stakeable
    
    @property
    def is_mineable(self) -> bool:
        """Whether this crypto can be mined."""
        return self._is_mineable
    
    @property
    def total_staked(self) -> Optional[Decimal]:
        """Total amount staked across network."""
        return self._total_staked
    
    def _validate_market_data(self, data: MarketData) -> bool:
        """Enhanced validation for crypto with higher volatility tolerance."""
        if data.price <= 0:
            print(f"Invalid price {data.price} for {self.symbol}")
            return False
        
        # Higher volatility circuit breaker for crypto - reject price changes > 50%
        if self._price > 0:
            price_change = abs(data.price - self._price) / self._price
            if price_change > self._extreme_volatility_threshold:
                print(f"Extreme volatility circuit breaker triggered for {self.symbol}: {price_change:.2%} change")
                return False
        
        return True
    
    def _post_process_data(self, data: MarketData) -> None:
        """Crypto-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update market cap if supply data available
        if self._circulating_supply:
            self._market_cap = data.price * self._circulating_supply
        
        # Check for high volatility events
        self._check_volatility_events(data)
        
        # Process any network events for this timestamp
        self._process_network_events(data.timestamp)
        
        # Update staking metrics if applicable
        if self._is_stakeable:
            self._update_staking_metrics()
    
    def _check_volatility_events(self, data: MarketData) -> None:
        """Check for volatility events and log them."""
        if self._price > 0:
            price_change = abs(data.price - self._price) / self._price
            if price_change > self._high_volatility_threshold:
                print(f"High volatility detected for {self.symbol}: {price_change:.2%}")
                
                # Could trigger additional processing for high volatility
                self._handle_high_volatility_event(data, price_change)
    
    def _handle_high_volatility_event(self, data: MarketData, change_pct: Decimal) -> None:
        """Handle high volatility events."""
        # This could implement additional logic like:
        # - Adjusting position sizes
        # - Triggering alerts
        # - Updating risk metrics
        pass
    
    def _process_network_events(self, timestamp: datetime) -> None:
        """Process network events that occurred at this timestamp."""
        for event in self._network_events:
            if event.event_date.date() == timestamp.date():
                self._apply_network_event(event)
    
    def _apply_network_event(self, event: NetworkEvent) -> None:
        """Apply effects of network events."""
        if event.event_type == 'halving' and event.impact_on_supply:
            # Reduce mining rewards/inflation
            pass
        elif event.event_type == 'burn' and event.impact_on_supply:
            # Reduce circulating supply
            if self._circulating_supply:
                self._circulating_supply -= event.impact_on_supply
        elif event.event_type == 'airdrop' and event.impact_on_supply:
            # Increase circulating supply
            if self._circulating_supply:
                self._circulating_supply += event.impact_on_supply
    
    def _update_staking_metrics(self) -> None:
        """Update staking-related metrics."""
        if self._staking_rewards:
            # Calculate average APY from recent rewards
            recent_rewards = [r for r in self._staking_rewards 
                            if (datetime.now() - r.reward_date).days <= 30]
            if recent_rewards:
                avg_apy = sum(r.apy for r in recent_rewards) / len(recent_rewards)
                self._staking_apy = avg_apy
    
    def update_supply_metrics(self, circulating_supply: Decimal, 
                            max_supply: Optional[Decimal] = None) -> None:
        """Update supply metrics and recalculate market cap."""
        if circulating_supply < 0:
            raise ValueError("Circulating supply cannot be negative")
        
        self._circulating_supply = circulating_supply
        if max_supply is not None:
            if max_supply < circulating_supply:
                raise ValueError("Max supply cannot be less than circulating supply")
            self._max_supply = max_supply
        
        # Update market cap
        if self.price > 0:
            self._market_cap = self.price * circulating_supply
    
    def update_staking_info(self, staking_apy: Decimal, 
                          is_stakeable: bool = True,
                          total_staked: Optional[Decimal] = None) -> None:
        """Update staking information."""
        if staking_apy < 0:
            raise ValueError("Staking APY cannot be negative")
        
        self._staking_apy = staking_apy
        self._is_stakeable = is_stakeable
        
        if total_staked is not None:
            if total_staked < 0:
                raise ValueError("Total staked cannot be negative")
            self._total_staked = total_staked
    
    def update_network_metrics(self, hash_rate: Optional[Decimal] = None,
                             is_mineable: bool = False) -> None:
        """Update network-specific metrics."""
        if hash_rate is not None:
            if hash_rate < 0:
                raise ValueError("Hash rate cannot be negative")
            self._network_hash_rate = hash_rate
        
        self._is_mineable = is_mineable
    
    def add_staking_reward(self, reward: StakingReward) -> None:
        """Add a staking reward to history."""
        self._staking_rewards.append(reward)
        self._staking_rewards.sort(key=lambda r: r.reward_date, reverse=True)
        
        # Update current APY based on recent rewards
        self._update_staking_metrics()
    
    def add_network_event(self, event: NetworkEvent) -> None:
        """Add a network event to history."""
        self._network_events.append(event)
        self._network_events.sort(key=lambda e: e.event_date, reverse=True)
    
    def calculate_staking_rewards(self, quantity: Decimal, 
                                days: int = 365) -> Decimal:
        """Calculate expected staking rewards for given quantity and period."""
        if not self._staking_apy or quantity <= 0 or not self._is_stakeable:
            return Decimal('0')
        
        # Simple compound interest calculation
        daily_rate = self._staking_apy / Decimal('365') / Decimal('100')
        
        # Compound daily for more accurate calculation
        compound_factor = (Decimal('1') + daily_rate) ** Decimal(str(days))
        final_value = quantity * compound_factor
        
        return final_value - quantity
    
    def get_supply_inflation_rate(self) -> Optional[Decimal]:
        """Calculate supply inflation rate if max supply is known."""
        if not self._circulating_supply or not self._max_supply or self._max_supply <= 0:
            return None
        
        remaining_supply = self._max_supply - self._circulating_supply
        if remaining_supply <= 0:
            return Decimal('0')  # Fully inflated
        
        # Calculate as percentage of remaining supply
        return (remaining_supply / self._circulating_supply) * Decimal('100')
    
    def get_staking_participation_rate(self) -> Optional[Decimal]:
        """Calculate staking participation rate."""
        if not self._total_staked or not self._circulating_supply or self._circulating_supply <= 0:
            return None
        
        return (self._total_staked / self._circulating_supply) * Decimal('100')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """
        Calculate margin requirement for crypto position.
        Higher margin due to volatility: 100% for long, 200% for short.
        """
        position_value = abs(quantity * self.price)
        
        if quantity >= 0:  # Long position
            return position_value * Decimal('1.0')  # 100% margin
        else:  # Short position  
            return position_value * Decimal('2.0')  # 200% margin
    
    def get_contract_multiplier(self) -> Decimal:
        """Crypto assets have a contract multiplier of 1."""
        return Decimal('1')
    
    def get_crypto_metrics(self) -> Dict[str, Any]:
        """Get crypto-specific metrics."""
        return {
            'symbol_code': self.symbol_code,
            'base_currency': self.base_currency,
            'blockchain': self.blockchain,
            'consensus_mechanism': self.consensus_mechanism,
            'current_price': self.price,
            'market_cap': self.market_cap,
            'circulating_supply': self.circulating_supply,
            'max_supply': self.max_supply,
            'staking_apy': self.staking_apy,
            'network_hash_rate': self.network_hash_rate,
            'supply_inflation_rate': self.get_supply_inflation_rate(),
            'staking_participation_rate': self.get_staking_participation_rate(),
            'is_stakeable': self.is_stakeable,
            'is_mineable': self.is_mineable,
            'total_staked': self.total_staked,
            'volatility': self.calculate_volatility(),
            'recent_rewards_count': len([r for r in self._staking_rewards 
                                       if (datetime.now() - r.reward_date).days <= 30]),
            'network_events_count': len(self._network_events),
        }
    
    def get_recent_network_activity(self, days: int = 30) -> Dict[str, Any]:
        """Get recent network activity summary."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_events = [e for e in self._network_events if e.event_date >= cutoff_date]
        recent_rewards = [r for r in self._staking_rewards if r.reward_date >= cutoff_date]
        
        return {
            'period_days': days,
            'network_events': len(recent_events),
            'staking_rewards': len(recent_rewards),
            'total_rewards_earned': sum(r.amount for r in recent_rewards),
            'avg_apy': sum(r.apy for r in recent_rewards) / len(recent_rewards) if recent_rewards else None,
            'event_types': list(set(e.event_type for e in recent_events)),
        }
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Crypto"
    
    def __str__(self) -> str:
        return f"CryptoBackTest({self.symbol_code}, ${self.price})"
    
    def __repr__(self) -> str:
        blockchain_info = f", blockchain={self.blockchain}" if self.blockchain else ""
        return (f"CryptoBackTest(symbol={self.symbol_code}, price=${self.price}, "
                f"market_cap=${self.market_cap}{blockchain_info})")