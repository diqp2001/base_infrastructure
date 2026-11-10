"""
ETFShareImpliedDispersionFactor Mapper - the ETF option dispersion factor (its name carries kind / right / measure / months).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareImpliedDispersionFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_implied_dispersion_factor import (
    ETFShareImpliedDispersionFactor,
)
from .....base_factor_mapper import BaseFactorMapper


class ETFShareImpliedDispersionFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareImpliedDispersionFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShareImpliedDispersion'

    def get_factor_model(self):
        return ETFShareImpliedDispersionFactorModel

    def get_factor_entity(self):
        return ETFShareImpliedDispersionFactor

    @property
    def model_class(self):
        return ETFShareImpliedDispersionFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareImpliedDispersionFactorModel]) -> Optional[ETFShareImpliedDispersionFactor]:
        """Convert ORM model to ETFShareImpliedDispersionFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareImpliedDispersionFactor(
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
    def to_orm(domain_entity: ETFShareImpliedDispersionFactor) -> ETFShareImpliedDispersionFactorModel:
        """Convert ETFShareImpliedDispersionFactor domain entity to ORM model."""
        return ETFShareImpliedDispersionFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
