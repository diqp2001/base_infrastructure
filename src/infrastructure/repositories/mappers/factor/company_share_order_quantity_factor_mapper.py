"""
Company Share Order Quantity Factor Mapper.
Maps between domain and ORM models for order quantity factors.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor
from src.infrastructure.models.factor.factor import CompanyShareOrderQuantityFactorModel


class CompanyShareOrderQuantityFactorMapper(BaseFactorMapper):
    """Mapper for Company Share Order Quantity Factor."""

    @property
    def discriminator(self):
        return 'company_share'

    @property
    def model_class(self):
        return CompanyShareOrderQuantityFactorModel
    
    def get_factor_model(self):
        return CompanyShareOrderQuantityFactorModel
    
    def get_factor_entity(self):
        return CompanyShareOrderQuantityFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareOrderQuantityFactorModel]) -> Optional[CompanyShareOrderQuantityFactor]:
        """Convert ORM model to CompanyShareOrderQuantityFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareOrderQuantityFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: CompanyShareOrderQuantityFactor) -> CompanyShareOrderQuantityFactorModel:
        """Convert CompanyShareOrderQuantityFactor domain entity to ORM model."""
        return CompanyShareOrderQuantityFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )