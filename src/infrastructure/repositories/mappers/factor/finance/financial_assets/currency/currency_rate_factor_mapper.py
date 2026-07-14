"""
Mapper for CurrencyRateFactor domain entity <-> ORM model.
"""

from typing import Optional

from src.domain.entities.factor.finance.financial_assets.currency.currency_rate_factor import CurrencyRateFactor
from src.infrastructure.models.factor.factor import CurrencyRateFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CurrencyRateFactorMapper(BaseFactorMapper):
    """Mapper for CurrencyRateFactor."""

    @property
    def discriminator(self):
        return 'Currency'

    @property
    def model_class(self):
        return CurrencyRateFactorModel

    def get_factor_model(self):
        return CurrencyRateFactorModel

    def get_factor_entity(self):
        return CurrencyRateFactor

    def to_domain(self, orm_model: Optional[CurrencyRateFactorModel]) -> Optional[CurrencyRateFactor]:
        if not orm_model:
            return None
        return CurrencyRateFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CurrencyRateFactor) -> CurrencyRateFactorModel:
        return CurrencyRateFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type='currency_rate_factor',
        )
