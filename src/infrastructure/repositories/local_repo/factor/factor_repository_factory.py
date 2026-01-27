"""
Factor Repository Factory - provides type-safe repositories for different factor entities.
This replaces the problematic approach of having one repository with dynamic entity class switching.
"""

from typing import Type, Dict, Optional, Protocol, TypeVar
from sqlalchemy.orm import Session

from src.domain.entities.factor.factor import Factor
from src.domain.entities.factor.continent_factor import ContinentFactor
from src.domain.entities.factor.country_factor import CountryFactor
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor
from src.domain.entities.factor.finance.financial_assets.index_factor import IndexFactor
from src.domain.entities.factor.finance.financial_assets.currency_factor import CurrencyFactor
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor
from src.domain.entities.factor.finance.financial_assets.bond_factor.bond_factor import BondFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor

from src.infrastructure.repositories.local_repo.factor.generic_factor_repository import GenericFactorRepository


F = TypeVar('F', bound=Factor)


class FactorRepositoryProtocol(Protocol[F]):
    """Protocol defining the interface for factor repositories."""
    
    def create_or_get_factor(self, name: str, group: str = "price", subgroup: str = "default", **kwargs) -> Optional[F]:
        """Create or get a factor by name."""
        ...


class FactorRepositoryFactory:
    """
    Factory for creating type-safe factor repositories.
    This replaces the single repository with dynamic entity class switching.
    """
    
    def __init__(self, session: Session, factory):
        self.session = session
        self.factory = factory
        self._repositories: Dict[Type[Factor], FactorRepositoryProtocol] = {}
    
    def get_repository(self, factor_class: Type[F]) -> FactorRepositoryProtocol[F]:
        """
        Get a type-safe repository for the specified factor class.
        
        Args:
            factor_class: The factor entity class to get a repository for
            
        Returns:
            A repository instance specifically typed for the factor class
        """
        if factor_class not in self._repositories:
            self._repositories[factor_class] = GenericFactorRepository(
                session=self.session,
                factory=self.factory,
                factor_class=factor_class
            )
        
        return self._repositories[factor_class]
    
    def create_or_get_factor(self, factor_class: Type[F], name: str, group: str = "price", 
                           subgroup: str = "default", **kwargs) -> Optional[F]:
        """
        Convenience method to create or get a factor without explicitly getting the repository.
        
        Args:
            factor_class: The factor entity class
            name: Factor name
            group: Factor group (default: "price")
            subgroup: Factor subgroup (default: "default")
            **kwargs: Additional arguments
            
        Returns:
            Factor instance or None
        """
        repository = self.get_repository(factor_class)
        return repository.create_or_get_factor(name=name, group=group, subgroup=subgroup, **kwargs)
    
    def get_factor_class_from_entity_class(self, entity_class: Type) -> Optional[Type[Factor]]:
        """
        Helper method to determine the appropriate factor class from an entity class.
        Uses the existing ENTITY_FACTOR_MAPPING but returns the first (most general) factor type.
        
        Args:
            entity_class: The entity class (e.g., Share, Index, etc.)
            
        Returns:
            Appropriate factor class or None if no mapping exists
        """
        from src.infrastructure.repositories.mappers.factor.factor_mapper import ENTITY_FACTOR_MAPPING
        
        factor_classes = ENTITY_FACTOR_MAPPING.get(entity_class, [])
        if factor_classes:
            # Return the first (most general) factor class for the entity
            return factor_classes[0]
        return None
    
    def create_or_get_factor_for_entity(self, entity_class: Type, name: str, 
                                      group: str = "price", subgroup: str = "default", 
                                      **kwargs) -> Optional[Factor]:
        """
        Create or get a factor for a specific entity type.
        
        Args:
            entity_class: The entity class (e.g., Share, Index, etc.)
            name: Factor name
            group: Factor group (default: "price")
            subgroup: Factor subgroup (default: "default")
            **kwargs: Additional arguments
            
        Returns:
            Factor instance or None
        """
        factor_class = self.get_factor_class_from_entity_class(entity_class)
        if not factor_class:
            raise ValueError(f"No factor mapping found for entity class {entity_class.__name__}")
        
        return self.create_or_get_factor(factor_class, name, group, subgroup, **kwargs)