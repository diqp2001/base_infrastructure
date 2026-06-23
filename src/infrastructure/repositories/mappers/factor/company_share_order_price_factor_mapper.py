"""
Company Share Order Price Factor Mapper.
Maps between domain and ORM models for order price factors.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor
from src.infrastructure.models.factor.factor import CompanyShareOrderPriceFactorModel


class CompanyShareOrderPriceFactorMapper(BaseFactorMapper):
    """Mapper for Company Share Order Price Factor."""

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareOrderPriceFactorModel
    
    def get_factor_model(self):
        return CompanyShareOrderPriceFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOrderPriceFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareOrderPriceFactorModel]) -> Optional[CompanyShareOrderPriceFactor]:
        """Convert ORM model to CompanyShareOrderPriceFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOrderPriceFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: CompanyShareOrderPriceFactor) -> CompanyShareOrderPriceFactorModel:
        """Convert CompanyShareOrderPriceFactor domain entity to ORM model."""
        return CompanyShareOrderPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )