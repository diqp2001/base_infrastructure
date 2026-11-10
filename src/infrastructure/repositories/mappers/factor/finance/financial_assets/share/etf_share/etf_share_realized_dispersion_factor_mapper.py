"""
ETFShareRealizedDispersionFactor Mapper - the ETF option dispersion factor (its name carries kind / right / measure / months).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareRealizedDispersionFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_realized_dispersion_factor import (
    ETFShareRealizedDispersionFactor,
)
from .....base_factor_mapper import BaseFactorMapper


class ETFShareRealizedDispersionFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareRealizedDispersionFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShareRealizedDispersion'

    def get_factor_model(self):
        return ETFShareRealizedDispersionFactorModel

    def get_factor_entity(self):
        return ETFShareRealizedDispersionFactor

    @property
    def model_class(self):
        return ETFShareRealizedDispersionFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareRealizedDispersionFactorModel]) -> Optional[ETFShareRealizedDispersionFactor]:
        """Convert ORM model to ETFShareRealizedDispersionFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareRealizedDispersionFactor(
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
    def to_orm(domain_entity: ETFShareRealizedDispersionFactor) -> ETFShareRealizedDispersionFactorModel:
        """Convert ETFShareRealizedDispersionFactor domain entity to ORM model."""
        return ETFShareRealizedDispersionFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
