"""
IBKR Portfolio Factor Repository - Interactive Brokers implementation for PortfolioFactor entities.

This repository handles portfolio factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.factor_port import FactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor


class IBKRPortfolioFactorRepository(BaseIBKRFactorRepository, FactorPort):
    """
    IBKR implementation of PortfolioFactorPort.
    Handles portfolio factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Portfolio Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return PortfolioFactor

    @property
    def local_repo(self):
        """Get local portfolio factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('portfolio_factor')
        return None

    # FactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[PortfolioFactor]:
        """Get portfolio factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[PortfolioFactor]:
        """Get portfolio factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[PortfolioFactor]:
        """Get portfolio factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[PortfolioFactor]:
        """Get portfolio factors by subgroup (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[PortfolioFactor]:
        """Get all portfolio factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: PortfolioFactor) -> Optional[PortfolioFactor]:
        """Add portfolio factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[PortfolioFactor]:
        """Update portfolio factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete portfolio factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def _create_or_get(self, name: str, group: str = "portfolio", subgroup: str = "general") -> Optional[PortfolioFactor]:
        """
        Get or create a portfolio factor from IBKR data.
        
        Args:
            name: Factor name
            group: Factor group (default: "portfolio")
            subgroup: Factor subgroup (default: "general")
            
        Returns:
            PortfolioFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new portfolio factor
            new_factor = PortfolioFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Portfolio factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new portfolio factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create portfolio factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for portfolio factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract portfolio factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For portfolio factors, extract portfolio-related information
            if 'portfolio_value' in ibkr_data:
                return ibkr_data['portfolio_value']
            elif 'net_liquidation' in ibkr_data:
                return ibkr_data['net_liquidation']
            elif 'total_cash_value' in ibkr_data:
                return ibkr_data['total_cash_value']
            
            return None
            
        except Exception as e:
            print(f"Error extracting portfolio factor value: {e}")
            return None