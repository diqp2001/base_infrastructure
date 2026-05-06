"""
Mapper for CompanyShareOptionHullWhitePriceFactor domain entity and ORM model conversion.
"""

from typing import Optional

from src.infrastructure.models.factor.factor import CompanyShareOptionHullWhitePriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_hull_white_price_factor import CompanyShareOptionHullWhitePriceFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanyShareOptionHullWhitePriceFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareOptionHullWhitePriceFactor domain entity and ORM model conversion."""
    
    @property
    def discriminator(self):
        return 'company_share_option'
    
    @property
    def model_class(self):
        return CompanyShareOptionHullWhitePriceFactorModel
    
    def get_factor_model(self):
        return CompanyShareOptionHullWhitePriceFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOptionHullWhitePriceFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareOptionHullWhitePriceFactorModel]) -> Optional[CompanyShareOptionHullWhitePriceFactor]:
        """Convert ORM model to CompanyShareOptionHullWhitePriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOptionHullWhitePriceFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id
        )
    
    def to_orm(self, domain_entity: CompanyShareOptionHullWhitePriceFactor) -> CompanyShareOptionHullWhitePriceFactorModel:
        """Convert CompanyShareOptionHullWhitePriceFactor domain entity to ORM model."""
        return CompanyShareOptionHullWhitePriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )