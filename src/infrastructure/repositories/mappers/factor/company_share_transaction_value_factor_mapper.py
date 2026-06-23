"""
Company Share Transaction Value Factor Mapper.
Maps between domain and ORM models for transaction value factors.
"""

from typing import Optional
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.domain.entities.factor.finance.transaction.company_share_transaction_value_factor import CompanyShareTransactionValueFactor
from src.infrastructure.models.factor.factor import CompanyShareTransactionValueFactorModel


class CompanyShareTransactionValueFactorMapper(BaseFactorMapper):
    """Mapper for Company Share Transaction Value Factor."""

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareTransactionValueFactorModel
    
    def get_factor_model(self):
        return CompanyShareTransactionValueFactorModel
    
    def get_factor_entity(self):
        return CompanyShareTransactionValueFactor
    
    def to_domain(self, orm_model: Optional[CompanyShareTransactionValueFactorModel]) -> Optional[CompanyShareTransactionValueFactor]:
        """Convert ORM model to CompanyShareTransactionValueFactor domain entity."""
        if not orm_model:
            return None
        
        return CompanyShareTransactionValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition
        )
    
    def to_orm(self, domain_entity: CompanyShareTransactionValueFactor) -> CompanyShareTransactionValueFactorModel:
        """Convert CompanyShareTransactionValueFactor domain entity to ORM model."""
        return CompanyShareTransactionValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition
        )