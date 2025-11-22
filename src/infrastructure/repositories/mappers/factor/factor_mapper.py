"""
Mapper for converting between Factor domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional
from infrastructure.models.factor.factor_model import (
    FactorModel, ContinentFactor, CountryFactor, FinancialAssetFactor,
    SecurityFactor, EquityFactor, ShareFactor, ShareMomentumFactor,
    ShareTechnicalFactor, ShareTargetFactor, ShareVolatilityFactor
)
from domain.entities.factor.factor import Factor as FactorEntity
from domain.entities.factor.continent_factor import ContinentFactor as ContinentFactorEntity
from domain.entities.factor.country_factor import CountryFactor as CountryFactorEntity
from domain.entities.factor.finance.financial_assets.financial_asset_factor import FinancialAssetFactor as FinancialAssetFactorEntity
from domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor as SecurityFactorEntity
from domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor as EquityFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor as ShareFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor as ShareMomentumFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor as ShareTechnicalFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor as ShareTargetFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor as ShareVolatilityFactorEntity


def _get_entity_type_from_factor(factor) -> str:
    """
    Helper function to determine entity_type from factor type.
    Returns the exact domain entity class name to represent accurately what's a discriminator is.
    """
    factor_class_name = factor.__class__.__name__
    
    # Return exact domain class names as discriminators
    return factor_class_name



class FactorMapper:
    """Mapper for Factor domain entity and ORM model conversion."""
    @abstractmethod
    def get_factor_model(self):
        return FactorModel
    
    @abstractmethod
    def get_factor_entity(self):
        return FactorEntity

    
    @staticmethod
    def to_domain(orm_model: Optional[FactorModel]) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity based on entity_type discriminator."""
        if not orm_model:
            return None
        
        # Use only base args for all factor entity mappings
        base_args = {
            'name': orm_model.name,
            'group': orm_model.group,
            'subgroup': orm_model.subgroup,
            'data_type': orm_model.data_type,
            'source': orm_model.source,
            'definition': orm_model.definition,
            'factor_id': orm_model.id,
        }
        
        # Map based on entity_type discriminator to appropriate domain class
        entity_type = orm_model.entity_type
        
        if entity_type == 'ContinentFactor':
            return ContinentFactorEntity(**base_args)
        elif entity_type == 'CountryFactor':
            return CountryFactorEntity(**base_args)
        elif entity_type == 'ShareVolatilityFactor':
            return ShareVolatilityFactorEntity(**base_args)
        elif entity_type == 'ShareTargetFactor':
            return ShareTargetFactorEntity(**base_args)
        elif entity_type == 'ShareTechnicalFactor':
            return ShareTechnicalFactorEntity(**base_args)
        elif entity_type == 'ShareMomentumFactor':
            return ShareMomentumFactorEntity(**base_args)
        elif entity_type == 'ShareFactor':
            return ShareFactorEntity(**base_args)
        elif entity_type == 'EquityFactor':
            return EquityFactorEntity(**base_args)
        elif entity_type == 'SecurityFactor':
            return SecurityFactorEntity(**base_args)
        elif entity_type == 'FinancialAssetFactor':
            return FinancialAssetFactorEntity(**base_args)
        else:
            # Default to base Factor entity
            return FactorEntity(**base_args)

    @staticmethod
    def to_orm(domain_entity: FactorEntity) -> FactorModel:
        """Convert domain entity to ORM model using only base args."""
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
        
        # Always return base FactorModel with only base args
        return FactorModel(**base_data)
    