"""
Enhanced Factor Dependency System with Granular Discriminators
Addresses the issue of discriminator uniqueness for external factors.

This system handles both:
1. External factors (IBKR data) - same class, different data fields
2. Calculated factors - unique classes with calculate() methods
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
from enum import Enum


class FactorType(Enum):
    """Factor type classification"""
    EXTERNAL = "external"  # Fetched from external sources (IBKR, etc)
    CALCULATED = "calculated"  # Computed using calculate() method


@dataclass
class FactorDiscriminator:
    """
    Enhanced discriminator that uniquely identifies factors.
    
    For external factors: includes data_field to distinguish bid/ask/etc
    For calculated factors: relies on unique code/version
    """
    code: str  # Stable identifier
    version: str  # Version for backward compatibility
    data_field: Optional[str] = None  # For external factors: "bid", "ask", "last", etc
    source: Optional[str] = None  # "IBKR", "model", etc
    
    def to_key(self) -> str:
        """Convert to unique string key for lookups"""
        key_parts = [self.code, self.version]
        if self.data_field:
            key_parts.append(self.data_field)
        if self.source:
            key_parts.append(self.source)
        return ":".join(key_parts)


@dataclass
class FactorReference:
    """Complete factor reference with discriminator and metadata hints"""
    discriminator: FactorDiscriminator
    name: str  # Human-readable name (hint only)
    group: str  # Factor group (hint only)
    subgroup: Optional[str] = None  # Factor subgroup (hint only)
    source: Optional[str] = None  # Data source (hint only)
    factor_type: FactorType = FactorType.CALCULATED  # Default to calculated


@dataclass
class FactorDependencyEntry:
    """Single dependency entry mapping parameter to factor"""
    factor: FactorReference
    required: bool = True
    description: Optional[str] = None


class FactorDependencyGraph:
    """
    Factor dependency graph supporting the exact format from your specification.
    
    Example usage:
    dependencies = {
        "spot_price": {
            "factor": {
                "discriminator": {
                    "code": "OPTION_PRICE",
                    "version": "v1", 
                    "data_field": "bid",  # This distinguishes bid from ask
                    "source": "IBKR"
                },
                "name": "Option Bid Price",
                "group": "Market Price",
                "subgroup": "Options",
                "source": "IBKR",
            },
            "required": True,
        },
        "ask_price": {
            "factor": {
                "discriminator": {
                    "code": "OPTION_PRICE", 
                    "version": "v1",
                    "data_field": "ask",  # Different data_field = different factor
                    "source": "IBKR"
                },
                "name": "Option Ask Price", 
                "group": "Market Price",
                "subgroup": "Options",
                "source": "IBKR",
            },
            "required": True,
        }
    }
    """
    
    def __init__(self, dependencies: Dict[str, Dict[str, Any]]):
        self.dependencies = dependencies
        
    def get_dependency_discriminators(self) -> Dict[str, FactorDiscriminator]:
        """Extract all discriminators from dependency graph"""
        discriminators = {}
        
        for param_name, dep_info in self.dependencies.items():
            factor_info = dep_info.get("factor", {})
            discriminator_data = factor_info.get("discriminator", {})
            
            discriminator = FactorDiscriminator(
                code=discriminator_data.get("code"),
                version=discriminator_data.get("version"),
                data_field=discriminator_data.get("data_field"),
                source=discriminator_data.get("source")
            )
            
            discriminators[param_name] = discriminator
            
        return discriminators
    
    def get_factor_references(self) -> Dict[str, FactorReference]:
        """Convert dependency graph to FactorReference objects"""
        references = {}
        
        for param_name, dep_info in self.dependencies.items():
            factor_info = dep_info.get("factor", {})
            discriminator_data = factor_info.get("discriminator", {})
            
            discriminator = FactorDiscriminator(
                code=discriminator_data.get("code"),
                version=discriminator_data.get("version"),
                data_field=discriminator_data.get("data_field"),
                source=discriminator_data.get("source")
            )
            
            # Determine factor type based on presence of data_field
            factor_type = (FactorType.EXTERNAL if discriminator.data_field 
                          else FactorType.CALCULATED)
            
            reference = FactorReference(
                discriminator=discriminator,
                name=factor_info.get("name", ""),
                group=factor_info.get("group", ""),
                subgroup=factor_info.get("subgroup"),
                source=factor_info.get("source"),
                factor_type=factor_type
            )
            
            references[param_name] = reference
            
        return references


class FactorRegistry:
    """Registry for factor lookup by discriminator"""
    
    def __init__(self):
        self._factors = {}  # discriminator_key -> factor_entity
        self._external_field_mapping = {}  # For IBKR field mappings
        
    def register_factor(self, discriminator: FactorDiscriminator, factor_entity):
        """Register a factor with its discriminator"""
        key = discriminator.to_key()
        self._factors[key] = factor_entity
        
    def resolve_by_discriminator(self, discriminator: FactorDiscriminator):
        """Resolve factor by discriminator"""
        key = discriminator.to_key()
        return self._factors.get(key)
    
    def register_external_field_mapping(self, 
                                      base_code: str, 
                                      version: str,
                                      source: str,
                                      field_mappings: Dict[str, str]):
        """
        Register field mappings for external factors.
        
        Example:
        registry.register_external_field_mapping(
            base_code="OPTION_PRICE",
            version="v1", 
            source="IBKR",
            field_mappings={
                "bid": "bid_price_field_name",
                "ask": "ask_price_field_name", 
                "last": "last_price_field_name"
            }
        )
        """
        mapping_key = f"{base_code}:{version}:{source}"
        self._external_field_mapping[mapping_key] = field_mappings
        
    def get_external_field_mapping(self, 
                                 base_code: str, 
                                 version: str, 
                                 source: str) -> Dict[str, str]:
        """Get field mappings for external factor"""
        mapping_key = f"{base_code}:{version}:{source}"
        return self._external_field_mapping.get(mapping_key, {})


# Example factor classes demonstrating the discriminator approach

class ExternalOptionPriceFactor:
    """
    External factor class for IBKR option prices.
    Uses data_field discriminator to distinguish bid/ask/last.
    """
    
    # Class-level dependencies not needed - this is an external factor
    # Individual instances are identified by discriminator.data_field
    
    def __init__(self, name: str, data_field: str, source: str = "IBKR"):
        self.name = name
        self.data_field = data_field  # "bid", "ask", "last", etc
        self.source = source
        
    @property
    def discriminator(self) -> FactorDiscriminator:
        return FactorDiscriminator(
            code="OPTION_PRICE",
            version="v1",
            data_field=self.data_field,
            source=self.source
        )
    
    # No calculate() method - value fetched directly from IBKR


class CalculatedOptionDeltaFactor:
    """
    Calculated factor requiring dependencies and calculate() method.
    Uses unique code discriminator without data_field.
    """
    
    # Class-level dependencies using the exact format from your specification
    dependencies = {
        "spot_price": {
            "factor": {
                "discriminator": {
                    "code": "OPTION_PRICE",
                    "version": "v1", 
                    "data_field": "last",  # Use last price for delta calculation
                    "source": "IBKR"
                },
                "name": "Option Last Price",
                "group": "Market Price", 
                "subgroup": "Options",
                "source": "IBKR",
            },
            "required": True,
        },
        "underlying_price": {
            "factor": {
                "discriminator": {
                    "code": "UNDERLYING_SPOT_PRICE",
                    "version": "v1",
                    "data_field": "last", 
                    "source": "IBKR"
                },
                "name": "Underlying Spot Price",
                "group": "Market Price",
                "subgroup": "Spot",
                "source": "IBKR",
            },
            "required": True,
        },
        "volatility": {
            "factor": {
                "discriminator": {
                    "code": "IMPLIED_VOLATILITY", 
                    "version": "v1",
                    "source": "model"
                },
                "name": "Implied Volatility",
                "group": "Volatility",
                "subgroup": "Options",
                "source": "model",
            },
            "required": True,
        }
    }
    
    def __init__(self, name: str):
        self.name = name
        
    @property  
    def discriminator(self) -> FactorDiscriminator:
        return FactorDiscriminator(
            code="OPTION_DELTA",
            version="v1",
            source="model"
        )
    
    def calculate(self, spot_price: float, underlying_price: float, 
                 volatility: float, **kwargs) -> float:
        """Calculate option delta using Black-Scholes"""
        # Delta calculation logic here
        # This method receives resolved dependency values as parameters
        pass


# Usage example demonstrating the solution

def demonstrate_discriminator_uniqueness():
    """Example showing how discriminators solve the bid/ask uniqueness problem"""
    
    registry = FactorRegistry()
    
    # Register external factors - same class, different discriminators
    bid_factor = ExternalOptionPriceFactor("Option Bid Price", "bid")
    ask_factor = ExternalOptionPriceFactor("Option Ask Price", "ask") 
    last_factor = ExternalOptionPriceFactor("Option Last Price", "last")
    
    registry.register_factor(bid_factor.discriminator, bid_factor)
    registry.register_factor(ask_factor.discriminator, ask_factor)
    registry.register_factor(last_factor.discriminator, last_factor)
    
    # Register calculated factor - unique discriminator  
    delta_factor = CalculatedOptionDeltaFactor("Option Delta")
    registry.register_factor(delta_factor.discriminator, delta_factor)
    
    # Test discriminator uniqueness
    bid_discriminator = FactorDiscriminator("OPTION_PRICE", "v1", "bid", "IBKR")
    ask_discriminator = FactorDiscriminator("OPTION_PRICE", "v1", "ask", "IBKR") 
    delta_discriminator = FactorDiscriminator("OPTION_DELTA", "v1", None, "model")
    
    # These should resolve to different factors despite bid/ask using same class
    resolved_bid = registry.resolve_by_discriminator(bid_discriminator)
    resolved_ask = registry.resolve_by_discriminator(ask_discriminator)
    resolved_delta = registry.resolve_by_discriminator(delta_discriminator)
    
    print(f"Bid discriminator key: {bid_discriminator.to_key()}")      # OPTION_PRICE:v1:bid:IBKR
    print(f"Ask discriminator key: {ask_discriminator.to_key()}")      # OPTION_PRICE:v1:ask:IBKR  
    print(f"Delta discriminator key: {delta_discriminator.to_key()}")  # OPTION_DELTA:v1:model
    
    # All three are uniquely resolvable despite bid/ask sharing the same class
    assert resolved_bid != resolved_ask
    assert resolved_bid != resolved_delta
    assert resolved_ask != resolved_delta


if __name__ == "__main__":
    demonstrate_discriminator_uniqueness()