"""
IBKR Factor Dependency Resolver - Integration with Enhanced Discriminator System

This resolver integrates the enhanced discriminator system with the IBKRFactorValueRepository
to address the bid/ask price discriminator uniqueness issue.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.domain.entities.factor.factor_dependency_system import (
    FactorDiscriminator, FactorReference, FactorDependencyGraph, 
    FactorRegistry, FactorType
)
from src.domain.entities.factor.factor_value import FactorValue
from src.domain.entities.factor.factor import Factor


class IBKRFactorDependencyResolver:
    """
    Resolver that handles both external IBKR factors and calculated factors
    using the enhanced discriminator system.
    """
    
    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.registry = FactorRegistry()
        self._initialize_ibkr_mappings()
        
    def _initialize_ibkr_mappings(self):
        """Initialize IBKR field mappings for external factors"""
        
        # Option price field mappings  
        self.registry.register_external_field_mapping(
            base_code="OPTION_PRICE",
            version="v1",
            source="IBKR",
            field_mappings={
                "bid": "bid",           # IBKR tick field name
                "ask": "ask",           # IBKR tick field name  
                "last": "last",         # IBKR tick field name
                "close": "close",       # IBKR historical field name
                "open": "open"          # IBKR historical field name
            }
        )
        
        # Underlying stock price field mappings
        self.registry.register_external_field_mapping(
            base_code="UNDERLYING_SPOT_PRICE", 
            version="v1",
            source="IBKR",
            field_mappings={
                "bid": "bid",
                "ask": "ask", 
                "last": "last",
                "close": "close",
                "open": "open"
            }
        )
        
        # Volatility field mappings
        self.registry.register_external_field_mapping(
            base_code="IMPLIED_VOLATILITY",
            version="v1", 
            source="IBKR",
            field_mappings={
                "implied_vol": "impliedVol",     # IBKR field name
                "historical_vol": "histVol"     # IBKR field name
            }
        )
    
    def resolve_dependencies_for_factor(self, 
                                       factor_entity: Factor, 
                                       financial_asset_entity,
                                       timestamp: datetime,
                                       **kwargs) -> Dict[str, Any]:
        """
        Resolve all dependencies for a factor using enhanced discriminator system.
        
        This method handles both:
        1. External factors (IBKR data) - resolved by discriminator.data_field  
        2. Calculated factors - dependencies resolved recursively
        
        Args:
            factor_entity: Factor requiring dependency resolution
            financial_asset_entity: Asset entity (for IBKR contracts)
            timestamp: Time for factor value resolution
            **kwargs: Additional resolution parameters
            
        Returns:
            Dict mapping dependency parameter names to resolved values
        """
        try:
            # Extract dependencies from factor class
            dependencies_data = self._get_factor_dependencies(factor_entity)
            if not dependencies_data:
                return {}
                
            dependency_graph = FactorDependencyGraph(dependencies_data)
            factor_references = dependency_graph.get_factor_references()
            
            resolved_dependencies = {}
            
            for param_name, factor_ref in factor_references.items():
                resolved_value = self._resolve_single_dependency(
                    param_name=param_name,
                    factor_ref=factor_ref,
                    financial_asset_entity=financial_asset_entity,
                    timestamp=timestamp,
                    **kwargs
                )
                
                if resolved_value is not None:
                    resolved_dependencies[param_name] = resolved_value
                else:
                    print(f"Warning: Could not resolve dependency {param_name} "
                          f"with discriminator {factor_ref.discriminator.to_key()}")
                    
            return resolved_dependencies
            
        except Exception as e:
            print(f"Error resolving dependencies for {factor_entity.name}: {e}")
            return {}
    
    def _resolve_single_dependency(self,
                                 param_name: str,
                                 factor_ref: FactorReference, 
                                 financial_asset_entity,
                                 timestamp: datetime,
                                 **kwargs) -> Optional[Any]:
        """
        Resolve a single dependency using discriminator-based lookup.
        
        Handles both external factors (IBKR data) and calculated factors.
        """
        try:
            discriminator = factor_ref.discriminator
            
            if factor_ref.factor_type == FactorType.EXTERNAL:
                # External factor - fetch from IBKR using data_field
                return self._resolve_external_factor(
                    discriminator=discriminator,
                    financial_asset_entity=financial_asset_entity,
                    timestamp=timestamp,
                    **kwargs
                )
            else:
                # Calculated factor - resolve recursively  
                return self._resolve_calculated_factor(
                    discriminator=discriminator,
                    financial_asset_entity=financial_asset_entity,
                    timestamp=timestamp,
                    **kwargs
                )
                
        except Exception as e:
            print(f"Error resolving dependency {param_name}: {e}")
            return None
    
    def _resolve_external_factor(self,
                               discriminator: FactorDiscriminator,
                               financial_asset_entity,
                               timestamp: datetime, 
                               **kwargs) -> Optional[Any]:
        """
        Resolve external factor from IBKR using discriminator.data_field.
        
        This solves the bid/ask uniqueness problem by using data_field
        to specify which IBKR field to extract.
        """
        try:
            if not discriminator.data_field:
                print(f"External factor {discriminator.code} missing data_field")
                return None
                
            # Get IBKR field mapping for this factor type
            field_mappings = self.registry.get_external_field_mapping(
                base_code=discriminator.code,
                version=discriminator.version,
                source=discriminator.source or "IBKR"
            )
            
            ibkr_field_name = field_mappings.get(discriminator.data_field)
            if not ibkr_field_name:
                print(f"No IBKR field mapping for {discriminator.code}:"
                      f"{discriminator.data_field}")
                return None
            
            # Fetch data from IBKR for the specific field
            contract = self._create_ibkr_contract(financial_asset_entity)
            if not contract:
                return None
                
            # Use different IBKR methods based on data type
            if discriminator.code in ["OPTION_PRICE", "UNDERLYING_SPOT_PRICE"]:
                # Price data - use historical or real-time
                return self._fetch_ibkr_price_data(
                    contract=contract,
                    field_name=ibkr_field_name,
                    timestamp=timestamp
                )
            elif discriminator.code == "IMPLIED_VOLATILITY":
                # Volatility data  
                return self._fetch_ibkr_volatility_data(
                    contract=contract,
                    field_name=ibkr_field_name,
                    timestamp=timestamp
                )
            else:
                print(f"Unknown external factor type: {discriminator.code}")
                return None
                
        except Exception as e:
            print(f"Error resolving external factor {discriminator.to_key()}: {e}")
            return None
    
    def _resolve_calculated_factor(self,
                                 discriminator: FactorDiscriminator,
                                 financial_asset_entity,
                                 timestamp: datetime,
                                 **kwargs) -> Optional[Any]:
        """
        Resolve calculated factor by recursive dependency resolution.
        
        This looks up the factor class by discriminator and resolves
        its dependencies recursively.
        """
        try:
            # Check if factor value already exists in database
            existing_value = self._check_existing_calculated_factor(
                discriminator=discriminator,
                financial_asset_entity=financial_asset_entity,
                timestamp=timestamp
            )
            if existing_value is not None:
                return float(existing_value.value)
            
            # Look up factor class by discriminator
            factor_class = self.registry.resolve_by_discriminator(discriminator)
            if not factor_class:
                print(f"Factor class not found for discriminator {discriminator.to_key()}")
                return None
            
            # Create factor instance
            factor_entity = factor_class(name=f"Dependency_{discriminator.code}")
            
            # Recursively resolve dependencies for this calculated factor
            sub_dependencies = self.resolve_dependencies_for_factor(
                factor_entity=factor_entity,
                financial_asset_entity=financial_asset_entity,
                timestamp=timestamp,
                **kwargs
            )
            
            # Call calculate method with resolved dependencies
            if hasattr(factor_entity, 'calculate'):
                calculated_value = factor_entity.calculate(**sub_dependencies)
                
                # Store calculated value in database
                self._store_calculated_factor_value(
                    discriminator=discriminator,
                    financial_asset_entity=financial_asset_entity,
                    timestamp=timestamp,
                    calculated_value=calculated_value
                )
                
                return calculated_value
            else:
                print(f"Calculated factor {discriminator.code} missing calculate method")
                return None
                
        except Exception as e:
            print(f"Error resolving calculated factor {discriminator.to_key()}: {e}")
            return None
    
    def _create_ibkr_contract(self, financial_asset_entity):
        """Create IBKR contract for asset entity"""
        try:
            from ibapi.contract import Contract
            
            contract = Contract()
            
            # Extract symbol
            symbol = (getattr(financial_asset_entity, 'symbol', None) or
                     getattr(financial_asset_entity, 'ticker', None) or  
                     getattr(financial_asset_entity, 'name', None))
            
            if not symbol:
                return None
                
            contract.symbol = symbol.upper()
            
            # Determine contract type based on entity type
            entity_class_name = financial_asset_entity.__class__.__name__
            if 'Option' in entity_class_name:
                contract.secType = "OPT"
                # Add option-specific fields as needed
            else:
                contract.secType = "STK"
                
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            return contract
            
        except Exception as e:
            print(f"Error creating IBKR contract: {e}")
            return None
    
    def _fetch_ibkr_price_data(self, 
                              contract, 
                              field_name: str, 
                              timestamp: datetime) -> Optional[float]:
        """Fetch price data from IBKR for specific field"""
        try:
            # This would integrate with actual IBKR API calls
            # For now, return mock data to demonstrate the pattern
            
            if self.factory and hasattr(self.factory, 'instrument_factor_ibkr_repo'):
                instrument_repo = self.factory.instrument_factor_ibkr_repo
                
                # Use the existing IBKR integration to get historical data
                historical_data = instrument_repo.get_or_create(
                    contract=contract,
                    what_to_show="TRADES",
                    duration_str="1 D", 
                    bar_size_setting="1 day"
                )
                
                if historical_data and len(historical_data) > 0:
                    # Extract the specific field value
                    latest_bar = historical_data[-1]  # Most recent data
                    return float(latest_bar.get(field_name, 0))
            
            return None
            
        except Exception as e:
            print(f"Error fetching IBKR price data for field {field_name}: {e}")
            return None
    
    def _fetch_ibkr_volatility_data(self, 
                                   contract,
                                   field_name: str,
                                   timestamp: datetime) -> Optional[float]:
        """Fetch volatility data from IBKR"""
        try:
            # Similar to price data but for volatility metrics
            # This would use IBKR's volatility data endpoints
            
            # Mock implementation
            if field_name == "impliedVol":
                return 0.25  # 25% implied volatility
            elif field_name == "histVol": 
                return 0.22  # 22% historical volatility
                
            return None
            
        except Exception as e:
            print(f"Error fetching IBKR volatility data for field {field_name}: {e}")
            return None
    
    def _get_factor_dependencies(self, factor_entity: Factor) -> Dict[str, Any]:
        """Extract dependencies from factor class (same logic as before)"""
        try:
            factor_class = factor_entity.__class__
            
            # Look for class-level dependencies attribute
            if hasattr(factor_class, 'dependencies'):
                deps = getattr(factor_class, 'dependencies')
                if isinstance(deps, dict):
                    return deps
                    
            return {}
            
        except Exception as e:
            print(f"Error extracting dependencies for {factor_entity.name}: {e}")
            return {}
    
    def _check_existing_calculated_factor(self,
                                        discriminator: FactorDiscriminator,
                                        financial_asset_entity,
                                        timestamp: datetime) -> Optional[FactorValue]:
        """Check if calculated factor value already exists in database"""
        try:
            if self.factory and hasattr(self.factory, 'factor_value_local_repo'):
                local_repo = self.factory.factor_value_local_repo
                
                # This would need to be enhanced to support discriminator-based lookup
                # For now, use existing method structure
                entity_id = getattr(financial_asset_entity, 'id', None)
                if entity_id:
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    # Would need to find factor_id by discriminator
                    # return local_repo.get_by_factor_entity_date(factor_id, entity_id, time_str)
                    
            return None
            
        except Exception as e:
            print(f"Error checking existing calculated factor: {e}")
            return None
    
    def _store_calculated_factor_value(self,
                                     discriminator: FactorDiscriminator, 
                                     financial_asset_entity,
                                     timestamp: datetime,
                                     calculated_value: Any):
        """Store calculated factor value in database"""
        try:
            if self.factory and hasattr(self.factory, 'factor_value_local_repo'):
                local_repo = self.factory.factor_value_local_repo
                
                # Create FactorValue entity
                factor_value = FactorValue(
                    id=None,
                    factor_id=None,  # Would need discriminator->factor_id mapping
                    entity_id=getattr(financial_asset_entity, 'id'),
                    date=timestamp,
                    value=str(calculated_value)
                )
                
                local_repo.add(factor_value)
                
        except Exception as e:
            print(f"Error storing calculated factor value: {e}")


# Integration with existing IBKRFactorValueRepository

class EnhancedIBKRFactorValueRepository:
    """
    Enhanced version of IBKRFactorValueRepository that uses the discriminator system
    to resolve the bid/ask price uniqueness issue.
    """
    
    def __init__(self, ibkr_client, factory=None):
        self.ibkr_client = ibkr_client
        self.factory = factory
        self.dependency_resolver = IBKRFactorDependencyResolver(ibkr_client, factory)
        
    def _create_or_get_with_discriminator(self,
                                        entity_symbol: str,
                                        factor_entity: Factor,
                                        financial_asset_entity,
                                        timestamp: datetime,
                                        **kwargs) -> Optional[FactorValue]:
        """
        Enhanced _create_or_get that uses discriminator-based dependency resolution.
        
        This method properly handles:
        1. External factors with data_field discriminators (bid/ask/last)  
        2. Calculated factors with recursive dependency resolution
        """
        try:
            # Check if factor value already exists
            entity_id = getattr(financial_asset_entity, 'id')
            factor_id = factor_entity.id
            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            existing = self._check_existing_factor_value(factor_id, entity_id, time_str)
            if existing:
                return existing
            
            # Resolve dependencies using enhanced discriminator system
            resolved_dependencies = self.dependency_resolver.resolve_dependencies_for_factor(
                factor_entity=factor_entity,
                financial_asset_entity=financial_asset_entity,
                timestamp=timestamp,
                **kwargs
            )
            
            if resolved_dependencies:
                # Factor has dependencies - call calculate method
                if hasattr(factor_entity, 'calculate'):
                    calculated_value = factor_entity.calculate(**resolved_dependencies)
                    
                    if calculated_value is not None:
                        # Create and store factor value
                        factor_value = FactorValue(
                            id=None,
                            factor_id=factor_id,
                            entity_id=entity_id, 
                            date=timestamp,
                            value=str(calculated_value)
                        )
                        
                        return self.factory.factor_value_local_repo.add(factor_value)
                else:
                    print(f"Factor {factor_entity.name} has dependencies but no calculate method")
            else:
                # No dependencies - fetch directly from IBKR (external factor)
                return self._fetch_external_factor_from_ibkr(
                    factor_entity=factor_entity,
                    financial_asset_entity=financial_asset_entity,
                    timestamp=timestamp,
                    **kwargs
                )
            
            return None
            
        except Exception as e:
            print(f"Error in _create_or_get_with_discriminator: {e}")
            return None
    
    def _fetch_external_factor_from_ibkr(self,
                                        factor_entity: Factor,
                                        financial_asset_entity,
                                        timestamp: datetime,
                                        **kwargs) -> Optional[FactorValue]:
        """Fetch external factor value directly from IBKR"""
        try:
            # Use existing IBKR integration methods
            # This would delegate to the existing _create_or_get method
            # or enhance it to support discriminator-based field extraction
            
            # For now, use placeholder implementation
            return None
            
        except Exception as e:
            print(f"Error fetching external factor from IBKR: {e}")
            return None
    
    def _check_existing_factor_value(self, factor_id: int, entity_id: int, time_str: str):
        """Check if factor value already exists (same as before)"""
        try:
            if self.factory and hasattr(self.factory, 'factor_value_local_repo'):
                return self.factory.factor_value_local_repo.get_by_factor_entity_date(
                    factor_id, entity_id, time_str
                )
            return None
        except Exception as e:
            print(f"Error checking existing factor value: {e}")
            return None