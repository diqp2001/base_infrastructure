"""
IBKR Index Price Return Factor Repository - Interactive Brokers implementation for IndexPriceReturnFactor entities.

This repository handles index price return factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from infrastructure.repositories.mappers.factor.finance.financial_assets.derivatives.option.future.index_future_option_price_return_factor_mapper import IndexFutureOptionPriceReturnFactorMapper
from src.domain.ports.factor.company_share_price_return_factor_port import CompanySharePriceReturnFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanySharePriceReturnFactorRepository(BaseIBKRFactorRepository, CompanySharePriceReturnFactorPort):
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
        self.mapper = IndexFutureOptionPriceReturnFactorMapper()
        
    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()

    @property
    def local_repo(self):
        """Get local index price return factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('company_share_price_return_factor')
        return None

    # IndexPriceReturnFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int):
        """Get index price return factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str):
        """Get index price return factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str):
        """Get index price return factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str):
        """Get index price return factors by subgroup (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self):
        """Get all index price return factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity):
        """Add index price return factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs):
        """Update index price return factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete index price return factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    

    def _create_or_get(self, name: str, **kwargs):
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