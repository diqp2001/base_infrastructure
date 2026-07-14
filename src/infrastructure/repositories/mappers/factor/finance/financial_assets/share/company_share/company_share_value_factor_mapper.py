"""
Mapper for CompanyShareValueFactor domain entity <-> ORM model.
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor
from src.infrastructure.models.factor.factor import CompanyShareValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareValueFactorMapper(BaseFactorMapper):
    """Mapper for CompanyShareValueFactor."""

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareValueFactorModel

    def get_factor_model(self):
        return CompanyShareValueFactorModel

    def get_factor_entity(self):
        return CompanyShareValueFactor

    def to_domain(self, orm_model: Optional[CompanyShareValueFactorModel]) -> Optional[CompanyShareValueFactor]:
        if not orm_model:
            return None
        return CompanyShareValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanyShareValueFactor) -> CompanyShareValueFactorModel:
        return CompanyShareValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type='company_share_value_factor',
        )
