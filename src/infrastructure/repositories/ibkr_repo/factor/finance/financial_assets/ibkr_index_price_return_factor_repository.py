"""
IBKR Index Price Return Factor Repository - Interactive Brokers implementation for IndexPriceReturnFactor entities.

This repository handles index price return factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.index_price_return_factor_port import IndexPriceReturnFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRIndexPriceReturnFactorRepository(BaseIBKRFactorRepository, IndexPriceReturnFactorPort):
    """
    IBKR implementation of IndexPriceReturnFactorPort.
    Handles index price return factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Index Price Return Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()

    @property
    def local_repo(self):
        """Get local index price return factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('index_price_return_factor')
        return None

    # IndexPriceReturnFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[IndexPriceReturnFactor]:
        """Get index price return factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[IndexPriceReturnFactor]:
        """Get index price return factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[IndexPriceReturnFactor]:
        """Get index price return factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[IndexPriceReturnFactor]:
        """Get index price return factors by subgroup (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[IndexPriceReturnFactor]:
        """Get all index price return factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: IndexPriceReturnFactor) -> Optional[IndexPriceReturnFactor]:
        """Add index price return factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[IndexPriceReturnFactor]:
        """Update index price return factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete index price return factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[IndexPriceReturnFactor]:
        """
        Get or create an index price return factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.LAST_PRICE)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            IndexPriceReturnFactor entity from database or newly created
        """
        try:
            # Get factor mapping configuration from IBKR tick type
            factor_mapping = IBKRTickFactorMapper.get_factor_mapping(tick_type)
            if not factor_mapping:
                print(f"No factor mapping found for tick type {tick_type}")
                return None
            
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(factor_mapping.factor_name)
                if existing_factor:
                    return existing_factor
            
            # Create new index price return factor from IBKR tick mapping
            new_factor = IndexPriceReturnFactor(
                name=factor_mapping.factor_name,
                group=factor_mapping.factor_group,
                subgroup=factor_mapping.factor_subgroup,
                data_type=factor_mapping.data_type,
                source="IBKR",
                definition=f"{factor_mapping.description} (IBKR Tick Type {tick_type.value})"
            )
            
            # Add additional metadata from contract data if available
            if contract_data:
                if 'symbol' in contract_data:
                    new_factor.definition += f" - Symbol: {contract_data['symbol']}"
                if 'exchange' in contract_data:
                    new_factor.definition += f" - Exchange: {contract_data['exchange']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new index price return factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create index price return factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def _create_or_get(self, name: str, **kwargs) -> Optional[IndexPriceReturnFactor]:
        """
        Get or create an index price return factor.
        
        Args:
            name: Factor name
            **kwargs: Additional parameters for factor creation
            
        Returns:
            IndexPriceReturnFactor entity from database or newly created
        """
        try:
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create index price return factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for index price return factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract index price return factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For index price return factors, calculate returns from price data
            if 'prevClose' in ibkr_data and 'lastPrice' in ibkr_data:
                prev_close = float(ibkr_data['prevClose'])
                current_price = float(ibkr_data['lastPrice'])
                if prev_close > 0:
                    return (current_price / prev_close) - 1
            elif 'close' in ibkr_data and 'prevClose' in ibkr_data:
                current_close = float(ibkr_data['close'])
                prev_close = float(ibkr_data['prevClose'])
                if prev_close > 0:
                    return (current_close / prev_close) - 1
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting index price return factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting index price return factor value: {e}")
            return None