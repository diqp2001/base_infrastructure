"""
ETFShareOptionScenarioPayoffFactor Mapper - an ETF option dispersion strategy factor (its name carries the measure).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareOptionScenarioPayoffFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_scenario_payoff_factor import ETFShareOptionScenarioPayoffFactor
from ......base_factor_mapper import BaseFactorMapper


class ETFShareOptionScenarioPayoffFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareOptionScenarioPayoffFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShareOptionScenarioPayoff'

    def get_factor_model(self):
        return ETFShareOptionScenarioPayoffFactorModel

    def get_factor_entity(self):
        return ETFShareOptionScenarioPayoffFactor

    @property
    def model_class(self):
        return ETFShareOptionScenarioPayoffFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareOptionScenarioPayoffFactorModel]) -> Optional[ETFShareOptionScenarioPayoffFactor]:
        """Convert ORM model to ETFShareOptionScenarioPayoffFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareOptionScenarioPayoffFactor(
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
    def to_orm(domain_entity: ETFShareOptionScenarioPayoffFactor) -> ETFShareOptionScenarioPayoffFactorModel:
        """Convert ETFShareOptionScenarioPayoffFactor domain entity to ORM model."""
        return ETFShareOptionScenarioPayoffFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
