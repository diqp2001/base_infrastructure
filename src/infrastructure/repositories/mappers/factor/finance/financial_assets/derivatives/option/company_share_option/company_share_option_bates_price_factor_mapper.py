"""
Mapper for CompanyShareOptionBatesPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionBatesPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_bates_price_factor import CompanyShareOptionBatesPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanyShareOptionBatesPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionBatesPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option'
    
    @property
    def model_class(self):
        return CompanyShareOptionBatesPriceFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionBatesPriceFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionBatesPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareOptionBatesPriceFactorModel]) -> Optional[CompanyShareOptionBatesPriceFactor]:
        """Convert ORM model to CompanyShareOptionBatesPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionBatesPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanyShareOptionBatesPriceFactor) -> CompanyShareOptionBatesPriceFactorModel:
        """Convert CompanyShareOptionBatesPriceFactor domain entity to ORM model."""
        return CompanyShareOptionBatesPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )