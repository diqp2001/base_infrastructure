"""
Mapper for CompanyShareOptionBlackScholesMertonPriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionBlackScholesMertonPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_black_scholes_merton_price_factor import CompanyShareOptionBlackScholesMertonPriceFactor
from .base_factor_mapper import BaseFactorMapper


class CompanyShareOptionBlackScholesMertonPriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionBlackScholesMertonPriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option'
    
    @property
    def model_class(self):
        return CompanyShareOptionBlackScholesMertonPriceFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionBlackScholesMertonPriceFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionBlackScholesMertonPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareOptionBlackScholesMertonPriceFactorModel]) -> Optional[CompanyShareOptionBlackScholesMertonPriceFactor]:
        """Convert ORM model to CompanyShareOptionBlackScholesMertonPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionBlackScholesMertonPriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanyShareOptionBlackScholesMertonPriceFactor) -> CompanyShareOptionBlackScholesMertonPriceFactorModel:
        """Convert CompanyShareOptionBlackScholesMertonPriceFactor domain entity to ORM model."""
        return CompanyShareOptionBlackScholesMertonPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )