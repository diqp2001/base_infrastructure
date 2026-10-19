"""
Mapper for CompanyShareOptionHestonSLVPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionHestonSLVPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_slv_price_factor import CompanyShareOptionHestonSLVPriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanyShareOptionHestonSLVPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionHestonSLVPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'CompanyShareOption'
    
    @property
    def model_class(self):
        return CompanyShareOptionHestonSLVPriceFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionHestonSLVPriceFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionHestonSLVPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareOptionHestonSLVPriceFactorModel]) -> Optional[CompanyShareOptionHestonSLVPriceFactor]:
        """Convert ORM model to CompanyShareOptionHestonSLVPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionHestonSLVPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanyShareOptionHestonSLVPriceFactor) -> CompanyShareOptionHestonSLVPriceFactorModel:
        """Convert CompanyShareOptionHestonSLVPriceFactor domain entity to ORM model."""
        return CompanyShareOptionHestonSLVPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )