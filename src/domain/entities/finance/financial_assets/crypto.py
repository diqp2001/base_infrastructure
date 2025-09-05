"""
Crypto class for cryptocurrency securities.
Extends Security with crypto-specific functionality and characteristics.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from .security import Security, Symbol, SecurityType, MarketData


class Crypto(Security):
    """
    Crypto class extending Security for cryptocurrency assets.
    Handles crypto-specific functionality like staking, mining rewards, and volatility.
    """
    
    def __init__(self, symbol_code: str, base_currency: str = "USD", 
                 blockchain: Optional[str] = None, 
                 consensus_mechanism: Optional[str] = None):
        # Create symbol for base Security class
        symbol = Symbol(
            ticker=symbol_code,
            exchange="CRYPTO",
            security_type=SecurityType.CRYPTO
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
        
        # Crypto-specific volatility is typically higher
        self._high_volatility_threshold = Decimal('0.2')  # 20% daily moves
        
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
    
    def _validate_market_data(self, data: MarketData) -> bool:
        """Enhanced validation for crypto with higher volatility tolerance."""
        if data.price <= 0:
            print(f"Invalid price {data.price} for {self.symbol}")
            return False
        
        # Higher volatility circuit breaker for crypto - reject price changes > 50%
        if self._price > 0:
            price_change = abs(data.price - self._price) / self._price
            if price_change > Decimal('0.5'):  # 50% change threshold for crypto
                print(f"Circuit breaker triggered for {self.symbol}: {price_change:.2%} change")
                return False
        
        return True
    
    def _post_process_data(self, data: MarketData) -> None:
        """Crypto-specific post-processing of market data."""
        super()._post_process_data(data)
        
        # Update market cap if supply data available
        if self._circulating_supply:
            self._market_cap = data.price * self._circulating_supply
        
        # Check for high volatility events
        if self._price > 0:
            price_change = abs(data.price - self._price) / self._price
            if price_change > self._high_volatility_threshold:
                print(f"High volatility detected for {self.symbol}: {price_change:.2%}")
    
    def update_supply_metrics(self, circulating_supply: Decimal, 
                            max_supply: Optional[Decimal] = None) -> None:
        """Update supply metrics and recalculate market cap."""
        self._circulating_supply = circulating_supply
        if max_supply is not None:
            self._max_supply = max_supply
        
        # Update market cap
        if self.price > 0:
            self._market_cap = self.price * circulating_supply
    
    def update_staking_info(self, staking_apy: Decimal) -> None:
        """Update staking annual percentage yield."""
        if staking_apy < 0:
            raise ValueError("Staking APY cannot be negative")
        self._staking_apy = staking_apy
    
    def update_network_metrics(self, hash_rate: Optional[Decimal] = None) -> None:
        """Update network-specific metrics."""
        if hash_rate is not None:
            if hash_rate < 0:
                raise ValueError("Hash rate cannot be negative")
            self._network_hash_rate = hash_rate
    
    def calculate_staking_rewards(self, quantity: Decimal, 
                                days: int = 365) -> Decimal:
        """Calculate expected staking rewards for given quantity and period."""
        if not self._staking_apy or quantity <= 0:
            return Decimal('0')
        
        # Simple compound interest calculation
        daily_rate = self._staking_apy / Decimal('365') / Decimal('100')
        rewards = quantity * daily_rate * Decimal(str(days))
        
        return rewards
    
    def get_supply_inflation_rate(self) -> Optional[Decimal]:
        """Calculate supply inflation rate if max supply is known."""
        if not self._circulating_supply or not self._max_supply or self._max_supply <= 0:
            return None
        
        remaining_supply = self._max_supply - self._circulating_supply
        if remaining_supply <= 0:
            return Decimal('0')  # Fully inflated
        
        # Calculate as percentage of remaining supply
        return (remaining_supply / self._circulating_supply) * Decimal('100')
    
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
        }
    
    @property
    def asset_type(self) -> str:
        """Asset type for backwards compatibility."""
        return "Crypto"
    
    def __str__(self) -> str:
        return f"Crypto({self.symbol_code}, ${self.price})"
    
    def __repr__(self) -> str:
        blockchain_info = f", blockchain={self.blockchain}" if self.blockchain else ""
        return (f"Crypto(symbol={self.symbol_code}, price=${self.price}, "
                f"market_cap=${self.market_cap}{blockchain_info})")