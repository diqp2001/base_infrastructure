"""
ETFShareOptionImpliedCorrelationFactor Mapper - an ETF option dispersion strategy factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareOptionImpliedCorrelationFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_implied_correlation_factor import ETFShareOptionImpliedCorrelationFactor
from ......base_factor_mapper import BaseFactorMapper


class ETFShareOptionImpliedCorrelationFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareOptionImpliedCorrelationFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShareOptionImpliedCorrelation'

    def get_factor_model(self):
        return ETFShareOptionImpliedCorrelationFactorModel

    def get_factor_entity(self):
        return ETFShareOptionImpliedCorrelationFactor

    @property
    def model_class(self):
        return ETFShareOptionImpliedCorrelationFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareOptionImpliedCorrelationFactorModel]) -> Optional[ETFShareOptionImpliedCorrelationFactor]:
        """Convert ORM model to ETFShareOptionImpliedCorrelationFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareOptionImpliedCorrelationFactor(
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
    def to_orm(domain_entity: ETFShareOptionImpliedCorrelationFactor) -> ETFShareOptionImpliedCorrelationFactorModel:
        """Convert ETFShareOptionImpliedCorrelationFactor domain entity to ORM model."""
        return ETFShareOptionImpliedCorrelationFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
