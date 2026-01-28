"""
IBKR Continent Factor Repository - Interactive Brokers implementation for ContinentFactor entities.

This repository handles continent factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.continent_factor_port import ContinentFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.continent_factor import ContinentFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRContinentFactorRepository(BaseIBKRFactorRepository, ContinentFactorPort):
    """
    IBKR implementation of ContinentFactorPort.
    Handles continent factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Continent Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        # The local repo will be set when accessed via property
        
    @property
    def entity_class(self):
        return ContinentFactor

    @property
    def local_repo(self):
        """Get local continent factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('continent_factor')
        return None

    # ContinentFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[ContinentFactor]:
        """Get continent factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[ContinentFactor]:
        """Get continent factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[ContinentFactor]:
        """Get continent factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[ContinentFactor]:
        """Get continent factors by subgroup (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[ContinentFactor]:
        """Get all continent factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: ContinentFactor) -> Optional[ContinentFactor]:
        """Add continent factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[ContinentFactor]:
        """Update continent factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete continent factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def _create_or_get(self, name: str, group: str = "geographic", subgroup: str = "continent") -> Optional[ContinentFactor]:
        """
        Get or create a continent factor from IBKR data.
        
        Args:
            name: Factor name
            group: Factor group (default: "geographic")
            subgroup: Factor subgroup (default: "continent")
            
        Returns:
            ContinentFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new continent factor
            new_factor = ContinentFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="categorical",
                source="IBKR",
                definition=f"Continent factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new continent factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create continent factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for continent factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract continent factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For continent factors, extract geographic information if available
            if 'region' in ibkr_data:
                return ibkr_data['region']
            elif 'continent' in ibkr_data:
                return ibkr_data['continent']
            elif 'country' in ibkr_data and isinstance(ibkr_data['country'], str):
                # Map country to continent - basic mapping
                country_continent_map = {
                    'US': 'North America',
                    'CA': 'North America',
                    'GB': 'Europe',
                    'DE': 'Europe',
                    'FR': 'Europe',
                    'JP': 'Asia',
                    'CN': 'Asia',
                    'AU': 'Oceania',
                }
                return country_continent_map.get(ibkr_data['country'], 'Unknown')
            
            return None
            
        except Exception as e:
            print(f"Error extracting continent factor value: {e}")
            return None