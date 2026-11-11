"""
ETFShareOptionFactor Mapper - the raw quote series of an ETF share option.
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareOptionFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import ETFShareOptionFactor
from ......base_factor_mapper import BaseFactorMapper


class ETFShareOptionFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareOptionFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShareOption'

    def get_factor_model(self):
        return ETFShareOptionFactorModel

    def get_factor_entity(self):
        return ETFShareOptionFactor

    @property
    def model_class(self):
        return ETFShareOptionFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareOptionFactorModel]) -> Optional[ETFShareOptionFactor]:
        """Convert ORM model to ETFShareOptionFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareOptionFactor(
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
    def to_orm(domain_entity: ETFShareOptionFactor) -> ETFShareOptionFactorModel:
        """Convert ETFShareOptionFactor domain entity to ORM model."""
        return ETFShareOptionFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
