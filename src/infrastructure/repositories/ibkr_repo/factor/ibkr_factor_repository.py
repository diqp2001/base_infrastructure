"""
IBKR Factor Repository - Interactive Brokers implementation for Factor entities.

This repository handles factor-related data acquisition from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List
from datetime import date

from src.domain.ports.factor.factor_port import FactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.factor import Factor


class IBKRFactorRepository(BaseIBKRFactorRepository, FactorPort):
    """
    IBKR implementation of FactorPort.
    Handles factor metadata acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, local_factor_repo: FactorPort):
        """
        Initialize IBKR Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            local_factor_repo: Local repository implementing FactorPort for persistence
        """
        super().__init__(ibkr_client, local_factor_repo)

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

    def _extract_value_for_factor(self, factor_id: int, ibkr_data) -> Optional[str]:
        """
        Extract factor value from IBKR data.
        
        For Factor entities, this is typically metadata about the factor
        rather than time-series values.
        """
        # Factors are typically static metadata, so IBKR extraction
        # is less relevant here compared to FactorValue
        return None