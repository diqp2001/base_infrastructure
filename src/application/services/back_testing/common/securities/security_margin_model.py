"""
SecurityMarginModel class for calculating margin requirements.
"""

from decimal import Decimal
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .security import Security


class SecurityMarginModel(ABC):
    """
    Abstract base class for calculating margin requirements.
    """
    
    @abstractmethod
    def get_initial_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """
        Get the initial margin requirement for a position.
        
        Args:
            security: The security being traded
            quantity: The quantity to trade
            
        Returns:
            The initial margin requirement
        """
        pass
    
    @abstractmethod
    def get_maintenance_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """
        Get the maintenance margin requirement for a position.
        
        Args:
            security: The security being traded
            quantity: The quantity held
            
        Returns:
            The maintenance margin requirement
        """
        pass


@dataclass
class DefaultMarginModel(SecurityMarginModel):
    """
    Default margin model with fixed margin requirements.
    """
    initial_margin_requirement: Decimal = Decimal('0.25')  # 25%
    maintenance_margin_requirement: Decimal = Decimal('0.25')  # 25%
    
    def __post_init__(self):
        if not isinstance(self.initial_margin_requirement, Decimal):
            self.initial_margin_requirement = Decimal(str(self.initial_margin_requirement))
        if not isinstance(self.maintenance_margin_requirement, Decimal):
            self.maintenance_margin_requirement = Decimal(str(self.maintenance_margin_requirement))
    
    def get_initial_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """Calculate initial margin requirement."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        
        notional_value = abs(quantity) * security.market_price
        return notional_value * self.initial_margin_requirement
    
    def get_maintenance_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """Calculate maintenance margin requirement."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        
        notional_value = abs(quantity) * security.market_price
        return notional_value * self.maintenance_margin_requirement


@dataclass
class RegTMarginModel(SecurityMarginModel):
    """
    Regulation T margin model for US equities.
    """
    
    def get_initial_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """
        Regulation T requires 50% initial margin for long positions.
        Short positions require 150% (100% + 50%).
        """
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        
        notional_value = abs(quantity) * security.market_price
        
        if quantity > 0:  # Long position
            return notional_value * Decimal('0.50')
        else:  # Short position
            return notional_value * Decimal('1.50')
    
    def get_maintenance_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """
        Regulation T requires 25% maintenance margin for long positions.
        Short positions require 30%.
        """
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        
        notional_value = abs(quantity) * security.market_price
        
        if quantity > 0:  # Long position
            return notional_value * Decimal('0.25')
        else:  # Short position
            return notional_value * Decimal('0.30')


@dataclass
class ForexMarginModel(SecurityMarginModel):
    """
    Forex margin model with high leverage.
    """
    leverage: Decimal = Decimal('100')  # 100:1 leverage
    
    def __post_init__(self):
        if not isinstance(self.leverage, Decimal):
            self.leverage = Decimal(str(self.leverage))
    
    def get_initial_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """Calculate forex initial margin requirement."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        
        notional_value = abs(quantity) * security.market_price
        return notional_value / self.leverage
    
    def get_maintenance_margin_requirement(self, security: Security, quantity: Decimal) -> Decimal:
        """Calculate forex maintenance margin requirement."""
        # For forex, maintenance margin is typically the same as initial margin
        return self.get_initial_margin_requirement(security, quantity)