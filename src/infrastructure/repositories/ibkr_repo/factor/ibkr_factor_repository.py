"""
IBKR Factor Repository - Interactive Brokers implementation for Factor entities.

This repository handles factor-related data acquisition from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime

from src.domain.ports.factor.factor_port import FactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.factor import Factor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRFactorRepository(BaseIBKRFactorRepository, FactorPort):
    """
    IBKR implementation of FactorPort.
    Handles factor metadata acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_repo: Local repository implementing FactorPort for persistence
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        self.local_repo = self.factory.factor_local_repo
    # FactorPort interface implementation (delegate to local repository)

    def get_by_id(self, entity_id: int) -> Optional[Factor]:
        """Get factor by ID (delegates to local repository)."""
        return self.local_repo.get_by_id(entity_id)

    def get_by_name(self, name: str) -> Optional[Factor]:
        """Get factor by name (delegates to local repository)."""
        return self.local_repo.get_by_name(name)

    def get_by_group(self, group: str) -> List[Factor]:
        """Get factors by group (delegates to local repository)."""
        return self.local_repo.get_by_group(group)

    def get_by_subgroup(self, subgroup: str) -> List[Factor]:
        """Get factors by subgroup (delegates to local repository)."""
        return self.local_repo.get_by_subgroup(subgroup)

    def get_by_data_type(self, data_type: str) -> List[Factor]:
        """Get factors by data type (delegates to local repository)."""
        return self.local_repo.get_by_data_type(data_type)

    def get_all_groups(self) -> List[str]:
        """Get all unique groups (delegates to local repository)."""
        return self.local_repo.get_all_groups()

    def get_all_subgroups(self) -> List[str]:
        """Get all unique subgroups (delegates to local repository)."""
        return self.local_repo.get_all_subgroups()

    def get_factors_by_group_and_subgroup(self, group: str, subgroup: str) -> List[Factor]:
        """Get factors by group and subgroup (delegates to local repository)."""
        return self.local_repo.get_factors_by_group_and_subgroup(group, subgroup)

    def search_factors(self, search_term: str) -> List[Factor]:
        """Search factors by name or description (delegates to local repository)."""
        return self.local_repo.search_factors(search_term)

    def get_all(self) -> List[Factor]:
        """Get all factors (delegates to local repository)."""
        return self.local_repo.get_all()

    def add(self, entity: Factor) -> Optional[Factor]:
        """Add factor entity (delegates to local repository)."""
        return self.local_repo.add(entity)

    def update(self, entity_id: int, **kwargs) -> Optional[Factor]:
        """Update factor entity (delegates to local repository)."""
        return self.local_repo.update(entity_id, **kwargs)

    def delete(self, entity_id: int) -> bool:
        """Delete factor entity (delegates to local repository)."""
        return self.local_repo.delete(entity_id)

    def get_or_create(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[Factor]:
        """
        Get or create a factor from IBKR tick type.
        
        This method creates factors based on IBKR tick types (e.g., Volume, Last Price)
        using the IBKR tick mapping system. For example, if IBKR contract returns
        volume data, this creates a 'Volume' factor in the local database.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.VOLUME)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            Factor entity from database or newly created
        """
        try:
            # Get factor mapping configuration from IBKR tick type
            factor_mapping = IBKRTickFactorMapper.get_factor_mapping(tick_type)
            if not factor_mapping:
                print(f"No factor mapping found for tick type {tick_type}")
                return None
            
            # Check if factor already exists by name
            existing_factor = self.local_repo.get_by_name(factor_mapping.factor_name)
            if existing_factor:
                return existing_factor
            
            # Create new factor from IBKR tick mapping
            new_factor = Factor(
                name=factor_mapping.factor_name,
                group=factor_mapping.factor_group,
                subgroup=factor_mapping.factor_subgroup,
                data_type=factor_mapping.data_type,
                source="IBKR",
                definition=f"{factor_mapping.description} (IBKR Tick Type {tick_type.value})"
            )
            
            # Add additional metadata from contract data if available
            if contract_data:
                # Enhance factor definition with contract-specific information
                if 'symbol' in contract_data:
                    new_factor.definition += f" - Symbol: {contract_data['symbol']}"
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
            
            # Persist to local database
            created_factor = self.local_repo.add(new_factor)
            if created_factor:
                print(f"Created new factor: {created_factor.name} (ID: {created_factor.id})")
                return created_factor
            else:
                print(f"Failed to create factor: {factor_mapping.factor_name}")
                return None
                
        except Exception as e:
            print(f"Error in get_or_create for tick type {tick_type}: {e}")
            return None
    
    def create_factor_from_volume_data(self, symbol: str, volume_value: int) -> Optional[Factor]:
        """
        Convenience method to create Volume factor from IBKR volume data.
        
        Args:
            symbol: Stock symbol
            volume_value: Volume value from IBKR
            
        Returns:
            Volume Factor entity
        """
        contract_data = {'symbol': symbol, 'volume': volume_value}
        return self.get_or_create(IBKRTickType.VOLUME, contract_data)
    
    def create_factor_from_price_data(self, symbol: str, price_type: str = "LAST") -> Optional[Factor]:
        """
        Convenience method to create Price factors from IBKR price data.
        
        Args:
            symbol: Stock symbol
            price_type: Type of price (LAST, BID, ASK, CLOSE, etc.)
            
        Returns:
            Price Factor entity
        """
        tick_type_map = {
            "LAST": IBKRTickType.LAST_PRICE,
            "BID": IBKRTickType.BID_PRICE,
            "ASK": IBKRTickType.ASK_PRICE,
            "CLOSE": IBKRTickType.CLOSE_PRICE,
            "HIGH": IBKRTickType.HIGH,
            "LOW": IBKRTickType.LOW,
            "OPEN": IBKRTickType.OPEN_TICK
        }
        
        tick_type = tick_type_map.get(price_type.upper())
        if not tick_type:
            print(f"Unsupported price type: {price_type}")
            return None
            
        contract_data = {'symbol': symbol, 'price_type': price_type}
        return self.get_or_create(tick_type, contract_data)

    def _extract_value_for_factor(self, factor_id: int, ibkr_data) -> Optional[str]:
        """
        Extract factor value from IBKR data.
        
        For Factor entities, this is typically metadata about the factor
        rather than time-series values.
        """
        # Factors are typically static metadata, so IBKR extraction
        # is less relevant here compared to FactorValue
        return None