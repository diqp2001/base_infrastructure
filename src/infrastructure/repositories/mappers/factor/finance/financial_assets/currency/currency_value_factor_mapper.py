"""
Mapper for CurrencyValueFactor domain entity <-> ORM model.
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor
from src.infrastructure.models.factor.factor import CurrencyValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CurrencyValueFactorMapper(BaseFactorMapper):
    """Mapper for CurrencyValueFactor."""

    @property
    def discriminator(self):
        return 'Currency'

    @property
    def model_class(self):
        return CurrencyValueFactorModel

    def get_factor_model(self):
        return CurrencyValueFactorModel

    def get_factor_entity(self):
        return CurrencyValueFactor

    def to_domain(self, orm_model: Optional[CurrencyValueFactorModel]) -> Optional[CurrencyValueFactor]:
        if not orm_model:
            return None
        return CurrencyValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CurrencyValueFactor) -> CurrencyValueFactorModel:
        return CurrencyValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type='currency_value_factor',
        )
