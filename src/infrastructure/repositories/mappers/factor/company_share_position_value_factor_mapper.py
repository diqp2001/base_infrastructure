"""
Company Share Position Value Factor Mapper.
Maps between domain and ORM models for position value factors.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor
from src.infrastructure.models.factor.factor import CompanySharePositionValueFactorModel


class CompanySharePositionValueFactorMapper(BaseFactorMapper):
    """Mapper for Company Share Position Value Factor."""

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanySharePositionValueFactorModel
    
    def get_factor_model(self):
        return CompanySharePositionValueFactorModel
    
    def get_factor_entity(self):
        return CompanySharePositionValueFactor
    
    def to_domain(self, orm_model: Optional[CompanySharePositionValueFactorModel]) -> Optional[CompanySharePositionValueFactor]:
        """Convert ORM model to CompanySharePositionValueFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanySharePositionValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: CompanySharePositionValueFactor) -> CompanySharePositionValueFactorModel:
        """Convert CompanySharePositionValueFactor domain entity to ORM model."""
        return CompanySharePositionValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )