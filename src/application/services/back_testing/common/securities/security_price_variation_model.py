"""
SecurityPriceVariationModel class for modeling price variations.
"""

from decimal import Decimal
from abc import ABC, abstractmethod
from dataclasses import dataclass


class SecurityPriceVariationModel(ABC):
    """
    Abstract base class for modeling price variations and minimum price movements.
    """
    
    @abstractmethod
    def get_minimum_price_variation(self, price: Decimal) -> Decimal:
        """
        Get the minimum price variation for the given price.
        
        Args:
            price: The current price
            
        Returns:
            The minimum price variation
        """
        pass


@dataclass
class FixedPriceVariationModel(SecurityPriceVariationModel):
    """
    Simple model with fixed price variation.
    """
    price_variation: Decimal = Decimal('0.01')
    
    def __post_init__(self):
        if not isinstance(self.price_variation, Decimal):
            self.price_variation = Decimal(str(self.price_variation))
    
    def get_minimum_price_variation(self, price: Decimal) -> Decimal:
        """Return the fixed price variation."""
        return self.price_variation


@dataclass
class TieredPriceVariationModel(SecurityPriceVariationModel):
    """
    Model with different price variations based on price tiers.
    """
    
    def get_minimum_price_variation(self, price: Decimal) -> Decimal:
        """
        Get minimum price variation based on price tiers.
        
        Typical US equity structure:
        - Under $1: $0.0001
        - $1 and above: $0.01
        """
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        
        if price < Decimal('1.00'):
            return Decimal('0.0001')
        else:
            return Decimal('0.01')


@dataclass
class ForexPriceVariationModel(SecurityPriceVariationModel):
    """
    Model for forex price variations (typically in pips).
    """
    
    def get_minimum_price_variation(self, price: Decimal) -> Decimal:
        """
        Get minimum price variation for forex.
        
        Most forex pairs have 4 decimal places (0.0001 pip)
        JPY pairs typically have 2 decimal places (0.01 pip)
        """
        return Decimal('0.0001')  # Standard pip for most pairs