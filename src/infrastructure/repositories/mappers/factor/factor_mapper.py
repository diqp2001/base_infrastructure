"""
Mapper for converting between Factor domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional

from src.infrastructure.models.factor.factor import FactorModel as Factormodel
from src.domain.entities.factor.factor import Factor as FactorEntity
from src.domain.entities.factor.continent_factor import ContinentFactor as ContinentFactorEntity
from src.domain.entities.factor.country_factor import CountryFactor as CountryFactorEntity
from src.domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor as FinancialAssetFactorEntity
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor as SecurityFactorEntity
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor as EquityFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor as ShareFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor as ShareMomentumFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor as ShareTechnicalFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor as ShareTargetFactorEntity
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor as ShareVolatilityFactorEntity


def _get_entity_type_from_factor(factor) -> str:
    """
    Helper function to determine entity_type from factor type.
    This avoids circular dependency with FactorCalculationService.
    """
    factor_class_name = factor.__class__.__name__
    
    # Map factor types to entity types
    if any(share_type in factor_class_name for share_type in ['Share', 'share']):
        return 'share'
    elif any(equity_type in factor_class_name for equity_type in ['Equity', 'equity']):
        return 'equity'
    elif any(country_type in factor_class_name for country_type in ['Country', 'country']):
        return 'country'
    elif any(continent_type in factor_class_name for continent_type in ['Continent', 'continent']):
        return 'continent'
    else:
        # For basic price factors and other general factors, default to 'share'
        # as most factors in the trading system are share-related
        return 'share'  # Default fallback



class FactorMapper:
    """Mapper for Factor domain entity and ORM model conversion."""
    @abstractmethod
    def get_factor_model(self):
        return Factormodel
    
    @abstractmethod
    def get_factor_entity(self):
        return FactorEntity

    
    @staticmethod
    def to_domain(orm_model: Optional[Factormodel]) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity based on factor_type discriminator."""
        if not orm_model:
            return None
        
        # Map based on discriminator type
        factor_type = orm_model.factor_type
        base_args = {
            'name': orm_model.name,
            'group': orm_model.group,
            'subgroup': orm_model.subgroup,
            'data_type': orm_model.data_type,
            'source': orm_model.source,
            'definition': orm_model.definition,
            'factor_id': orm_model.id,
        }
        
        if factor_type == 'continent':
            return ContinentFactorEntity(
                **base_args,
            )
        elif factor_type == 'country':
            return CountryFactorEntity(
                **base_args,
               
            )
        elif factor_type == 'financial_asset':
            return FinancialAssetFactorEntity(
                **base_args,
            )
        elif factor_type == 'security':
            return SecurityFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'equity':
            return EquityFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share':
            return ShareFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_momentum':
            return ShareMomentumFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_technical':
            return ShareTechnicalFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_target':
            return ShareTargetFactorEntity(
                **base_args,
                
            )
        elif factor_type == 'share_volatility':
            return ShareVolatilityFactorEntity(
                **base_args,
                
            )
        else:
            # Default to base Factor for unknown types
            # Since Factor is abstract, create a concrete implementation
            class GenericFactor(FactorEntity):
                pass
            
            return GenericFactor(**base_args)

    @staticmethod
    def to_orm(domain_entity: FactorEntity) -> Factormodel:
        """Convert domain entity to ORM model based on entity type."""
        base_data = {
            'id': domain_entity.id,
            'name': domain_entity.name,
            'group': domain_entity.group,
            'subgroup': domain_entity.subgroup,
            'data_type': domain_entity.data_type,
            'source': domain_entity.source,
            'definition': domain_entity.definition,
            'entity_type': _get_entity_type_from_factor(domain_entity),  # Derive entity_type from factor type
        }
        
        
        return Factormodel(**base_data)
    