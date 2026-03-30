"""
Mapper for CompanyShareOptionDeltaFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionDeltaFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor import CompanyShareOptionDeltaFactor
from .base_factor_mapper import BaseFactorMapper


class CompanyShareOptionDeltaFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionDeltaFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option_delta'
    
    @property
    def model_class(self):
        return CompanyShareOptionDeltaFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionDeltaFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionDeltaFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionDeltaFactorModel]) -> Optional[CompanyShareOptionDeltaFactor]:
        """Convert ORM model to CompanyShareOptionDeltaFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionDeltaFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: CompanyShareOptionDeltaFactor):
        """Convert CompanyShareOptionDeltaFactor domain entity to ORM model."""
        return CompanyShareOptionDeltaFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )