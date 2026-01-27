"""
IBKR Country Factor Repository - Interactive Brokers implementation for CountryFactor entities.

This repository handles country factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.country_factor_port import CountryFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.country_factor import CountryFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRCountryFactorRepository(BaseIBKRFactorRepository, CountryFactorPort):
    """
    IBKR implementation of CountryFactorPort.
    Handles country factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Country Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return CountryFactor

    @property
    def local_repo(self):
        """Get local country factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('country_factor')
        return None

    # CountryFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[CountryFactor]:
        """Get country factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[CountryFactor]:
        """Get country factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[CountryFactor]:
        """Get country factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[CountryFactor]:
        """Get country factors by subgroup (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[CountryFactor]:
        """Get all country factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: CountryFactor) -> Optional[CountryFactor]:
        """Add country factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[CountryFactor]:
        """Update country factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete country factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create(self, name: str, group: str = "geographic", subgroup: str = "country") -> Optional[CountryFactor]:
        """
        Get or create a country factor from IBKR data.
        
        Args:
            name: Factor name
            group: Factor group (default: "geographic")
            subgroup: Factor subgroup (default: "country")
            
        Returns:
            CountryFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new country factor
            new_factor = CountryFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="categorical",
                source="IBKR",
                definition=f"Country factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new country factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create country factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for country factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract country factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For country factors, extract country information from IBKR data
            if 'country' in ibkr_data:
                return ibkr_data['country']
            elif 'primaryExchange' in ibkr_data:
                # Map exchange to country - basic mapping
                exchange_country_map = {
                    'NYSE': 'US',
                    'NASDAQ': 'US',
                    'SMART': 'US',
                    'TSE': 'CA',
                    'LSE': 'GB',
                    'XETRA': 'DE',
                    'EURONEXT': 'FR',
                    'TSE.JPN': 'JP',
                    'SSE': 'CN',
                    'ASX': 'AU',
                }
                return exchange_country_map.get(ibkr_data['primaryExchange'], 'Unknown')
            elif 'currency' in ibkr_data:
                # Map currency to country - basic mapping
                currency_country_map = {
                    'USD': 'US',
                    'CAD': 'CA',
                    'GBP': 'GB',
                    'EUR': 'DE',  # Default EUR to Germany
                    'JPY': 'JP',
                    'CNY': 'CN',
                    'AUD': 'AU',
                }
                return currency_country_map.get(ibkr_data['currency'], 'Unknown')
            
            return None
            
        except Exception as e:
            print(f"Error extracting country factor value: {e}")
            return None