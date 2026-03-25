"""
Mapper for CompanyShareOptionGammaFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionGammaFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import CompanyShareOptionGammaFactor
from .base_factor_mapper import BaseFactorMapper


class CompanyShareOptionGammaFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionGammaFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option_gamma_factor'
    
    @property
    def model_class(self):
        return CompanyShareOptionGammaFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionGammaFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionGammaFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionGammaFactorModel]) -> Optional[CompanyShareOptionGammaFactor]:
        """Convert ORM model to CompanyShareOptionGammaFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionGammaFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: CompanyShareOptionGammaFactor):
        """Convert CompanyShareOptionGammaFactor domain entity to ORM model."""
        return CompanyShareOptionGammaFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )