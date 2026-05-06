"""
Mapper for CompanyShareOptionVegaFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionVegaFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor import CompanyShareOptionVegaFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanyShareOptionVegaFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionVegaFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option'
    
    @property
    def model_class(self):
        return CompanyShareOptionVegaFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionVegaFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionVegaFactor
    
    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionVegaFactorModel]) -> Optional[CompanyShareOptionVegaFactor]:
        """Convert ORM model to CompanyShareOptionVegaFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionVegaFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    @classmethod
    def to_orm(cls, domain_entity: CompanyShareOptionVegaFactor):
        """Convert CompanyShareOptionVegaFactor domain entity to ORM model."""
        return CompanyShareOptionVegaFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )