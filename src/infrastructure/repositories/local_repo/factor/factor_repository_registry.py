"""
Registry for mapping factor entity types to their corresponding repository classes.
"""

from typing import Type, Dict
from sqlalchemy.orm import Session

# Import all factor repositories
from .geographic.continent_factor_repository import ContinentFactorRepository
from .geographic.country_factor_repository import CountryFactorRepository
from .finance.financial_assets.financial_asset_factor_repository import FinancialAssetFactorRepository
from .finance.financial_assets.security_factor_repository import SecurityFactorRepository
from .finance.financial_assets.index_factor_repository import IndexFactorRepository
from .finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from .finance.financial_assets.equity_factor_repository import EquityFactorRepository
from .finance.financial_assets.share_factor_repository import ShareFactorRepository
from .finance.financial_assets.share_momentum_factor_repository import ShareMomentumFactorRepository
from .finance.financial_assets.share_technical_factor_repository import ShareTechnicalFactorRepository
from .finance.financial_assets.share_target_factor_repository import ShareTargetFactorRepository
from .finance.financial_assets.share_volatility_factor_repository import ShareVolatilityFactorRepository
from .finance.financial_assets.bond_factor_repository import BondFactorRepository
from .finance.financial_assets.derivative_factor_repository import DerivativeFactorRepository
from .finance.financial_assets.options_factor_repository import OptionsFactorRepository
from .finance.financial_assets.futures_factor_repository import FuturesFactorRepository

# Import factor entity types
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

from .base_factor_repository import BaseFactorRepository


# Factor Entity to Repository Class Mapping
FACTOR_REPOSITORY_MAPPING: Dict[Type, Type[BaseFactorRepository]] = {
    # Geographic factors
    ContinentFactor: ContinentFactorRepository,
    CountryFactor: CountryFactorRepository,
    
    # Financial asset factors
    FinancialAssetFactor: FinancialAssetFactorRepository,
    SecurityFactor: SecurityFactorRepository,
    IndexFactor: IndexFactorRepository,
    CurrencyFactor: CurrencyFactorRepository,
    EquityFactor: EquityFactorRepository,
    
    # Share factors
    ShareFactor: ShareFactorRepository,
    ShareMomentumFactor: ShareMomentumFactorRepository,
    ShareTechnicalFactor: ShareTechnicalFactorRepository,
    ShareTargetFactor: ShareTargetFactorRepository,
    ShareVolatilityFactor: ShareVolatilityFactorRepository,
    
    # Bond factors
    BondFactor: BondFactorRepository,
    
    # Derivative factors
    DerivativeFactor: DerivativeFactorRepository,
    OptionFactor: OptionsFactorRepository,
    FutureFactor: FuturesFactorRepository,
}


class FactorRepositoryRegistry:
    """Registry for getting the appropriate repository for a given factor entity type."""
    
    @staticmethod
    def get_repository(factor_entity_class: Type, session: Session) -> BaseFactorRepository:
        """
        Get the appropriate repository instance for a given factor entity class.
        
        Args:
            factor_entity_class: The factor entity class (e.g., IndexFactor)
            session: Database session
            
        Returns:
            Repository instance for the given factor entity type
            
        Raises:
            KeyError: If no repository is registered for the given factor entity class
        """
        if factor_entity_class not in FACTOR_REPOSITORY_MAPPING:
            raise KeyError(f"No repository registered for factor entity class: {factor_entity_class}")
        
        repository_class = FACTOR_REPOSITORY_MAPPING[factor_entity_class]
        return repository_class(session)
    
    @staticmethod
    def get_repository_class(factor_entity_class: Type) -> Type[BaseFactorRepository]:
        """
        Get the repository class (not instance) for a given factor entity class.
        
        Args:
            factor_entity_class: The factor entity class
            
        Returns:
            Repository class for the given factor entity type
            
        Raises:
            KeyError: If no repository is registered for the given factor entity class
        """
        if factor_entity_class not in FACTOR_REPOSITORY_MAPPING:
            raise KeyError(f"No repository registered for factor entity class: {factor_entity_class}")
        
        return FACTOR_REPOSITORY_MAPPING[factor_entity_class]
    
    @staticmethod
    def get_all_mappings() -> Dict[Type, Type[BaseFactorRepository]]:
        """
        Get all factor entity to repository class mappings.
        
        Returns:
            Dictionary of all mappings
        """
        return FACTOR_REPOSITORY_MAPPING.copy()
    
    @staticmethod
    def register_repository(factor_entity_class: Type, repository_class: Type[BaseFactorRepository]) -> None:
        """
        Register a new factor entity to repository mapping.
        
        Args:
            factor_entity_class: The factor entity class
            repository_class: The repository class for this entity
        """
        FACTOR_REPOSITORY_MAPPING[factor_entity_class] = repository_class