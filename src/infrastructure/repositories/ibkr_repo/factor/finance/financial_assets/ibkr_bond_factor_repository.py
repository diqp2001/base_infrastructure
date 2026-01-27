"""
IBKR Bond Factor Repository - Interactive Brokers implementation for BondFactor entities.

This repository handles bond factor data from IBKR API,
applying IBKR-specific business rules before delegating persistence to local repository.
"""

from typing import Optional, List, Dict, Any
from datetime import date

from src.domain.ports.factor.bond_factor_port import BondFactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor
from src.infrastructure.repositories.ibkr_repo.tick_types.ibkr_tick_mapping import IBKRTickFactorMapper, IBKRTickType


class IBKRBondFactorRepository(BaseIBKRFactorRepository, BondFactorPort):
    """
    IBKR implementation of BondFactorPort.
    Handles bond factor data acquisition from Interactive Brokers API and delegates persistence to local repository.
    """

    def __init__(self, ibkr_client, factory=None):
        """
        Initialize IBKR Bond Factor Repository.
        
        Args:
            ibkr_client: Interactive Brokers API client
            factory: Repository factory for dependency injection (optional)
        """
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return BondFactor

    @property
    def local_repo(self):
        """Get local bond factor repository for delegation."""
        if self.factory:
            return self.factory._local_repositories.get('bond_factor')
        return None

    # BondFactorPort interface implementation (delegate to local repository)
    
    def get_by_id(self, entity_id: int) -> Optional[BondFactor]:
        """Get bond factor by ID (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[BondFactor]:
        """Get bond factor by name (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_bond_type(self, bond_type: str) -> List[BondFactor]:
        """Get bond factors by bond type (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_bond_type(bond_type)
        return []

    def get_by_maturity_range(self, min_years: Optional[float] = None, max_years: Optional[float] = None) -> List[BondFactor]:
        """Get bond factors by maturity range (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_maturity_range(min_years, max_years)
        return []

    def get_by_credit_rating(self, rating: str) -> List[BondFactor]:
        """Get bond factors by credit rating (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_credit_rating(rating)
        return []

    def get_by_group(self, group: str) -> List[BondFactor]:
        """Get bond factors by group (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_all(self) -> List[BondFactor]:
        """Get all bond factors (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: BondFactor) -> Optional[BondFactor]:
        """Add bond factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity: BondFactor) -> Optional[BondFactor]:
        """Update bond factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.update(entity)
        return None

    def delete(self, entity_id: int) -> bool:
        """Delete bond factor entity (delegates to local repository)."""
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def get_or_create_from_tick_type(self, tick_type: IBKRTickType, contract_data: Optional[Dict[str, Any]] = None) -> Optional[BondFactor]:
        """
        Get or create a bond factor from IBKR tick type.
        
        Args:
            tick_type: IBKR tick type enum (e.g., IBKRTickType.YIELD)
            contract_data: Optional contract details from IBKR API
            
        Returns:
            BondFactor entity from database or newly created
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
            
            # Create new bond factor from IBKR tick mapping
            new_factor = BondFactor(
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
                if 'maturity' in contract_data:
                    new_factor.definition += f" - Maturity: {contract_data['maturity']}"
                if 'rating' in contract_data:
                    new_factor.definition += f" - Rating: {contract_data['rating']}"
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new bond factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create bond factor: {factor_mapping.factor_name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create_from_tick_type for tick type {tick_type}: {e}")
            return None

    def get_or_create(self, name: str, group: str = "fixed_income", subgroup: str = "bond") -> Optional[BondFactor]:
        """
        Get or create a bond factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "fixed_income")
            subgroup: Factor subgroup (default: "bond")
            
        Returns:
            BondFactor entity from database or newly created
        """
        try:
            # Check if factor already exists by name
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            # Create new bond factor
            new_factor = BondFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Bond factor: {name} (from IBKR data)"
            )
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    print(f"Created new bond factor: {created_factor.name} (ID: {created_factor.id})")
                    return created_factor
            
            print(f"Failed to create bond factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for bond factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract bond factor value from IBKR data.
        
        Args:
            factor_id: The factor ID
            ibkr_data: Raw IBKR data dictionary
            
        Returns:
            Extracted value or None if not available
        """
        try:
            # For bond factors, extract price, yield, and duration data
            if 'yield' in ibkr_data:
                return float(ibkr_data['yield'])
            elif 'price' in ibkr_data:
                return float(ibkr_data['price'])
            elif 'lastPrice' in ibkr_data:
                return float(ibkr_data['lastPrice'])
            elif 'bid' in ibkr_data:
                return float(ibkr_data['bid'])
            elif 'ask' in ibkr_data:
                return float(ibkr_data['ask'])
            elif 'duration' in ibkr_data:
                return float(ibkr_data['duration'])
            elif 'convexity' in ibkr_data:
                return float(ibkr_data['convexity'])
            elif 'spread' in ibkr_data:
                return float(ibkr_data['spread'])
            
            return None
            
        except (ValueError, TypeError) as e:
            print(f"Error converting bond factor value: {e}")
            return None
        except Exception as e:
            print(f"Error extracting bond factor value: {e}")
            return None