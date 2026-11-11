"""
ETFShareOptionReversePremiumFactor Mapper - an ETF option dispersion strategy factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareOptionReversePremiumFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_reverse_premium_factor import ETFShareOptionReversePremiumFactor
from ......base_factor_mapper import BaseFactorMapper


class ETFShareOptionReversePremiumFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareOptionReversePremiumFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShareOptionReversePremium'

    def get_factor_model(self):
        return ETFShareOptionReversePremiumFactorModel

    def get_factor_entity(self):
        return ETFShareOptionReversePremiumFactor

    @property
    def model_class(self):
        return ETFShareOptionReversePremiumFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareOptionReversePremiumFactorModel]) -> Optional[ETFShareOptionReversePremiumFactor]:
        """Convert ORM model to ETFShareOptionReversePremiumFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareOptionReversePremiumFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )

    @staticmethod
    def to_orm(domain_entity: ETFShareOptionReversePremiumFactor) -> ETFShareOptionReversePremiumFactorModel:
        """Convert ETFShareOptionReversePremiumFactor domain entity to ORM model."""
        return ETFShareOptionReversePremiumFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
