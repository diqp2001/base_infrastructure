"""
Mapper for CompanyShareOptionPriceReturnFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionPriceReturnFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor
from .base_factor_mapper import BaseFactorMapper


class CompanyShareOptionPriceReturnFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionPriceReturnFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option_price_return_factor'
    
    @property
    def model_class(self):
        return CompanyShareOptionPriceReturnFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionPriceReturnFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionPriceReturnFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionPriceReturnFactorModel]) -> Optional[CompanyShareOptionPriceReturnFactor]:
        """Convert ORM model to CompanyShareOptionPriceReturnFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionPriceReturnFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: CompanyShareOptionPriceReturnFactor):
        """Convert CompanyShareOptionPriceReturnFactor domain entity to ORM model."""
        return CompanyShareOptionPriceReturnFactorModel(
            id=domain_entity.factor_id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            discriminator=cls().discriminator
        )