"""
ETFShareFactor Mapper - Mapper for ETFShareFactor domain entities and ORM models (mirrors CompanyShareFactorMapper).
"""

from typing import Optional
from src.infrastructure.models.factor.factor import ETFShareFactorModel
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor
from .....base_factor_mapper import BaseFactorMapper


class ETFShareFactorMapper(BaseFactorMapper):
    """Mapper for ETFShareFactor domain entity and ORM model conversion."""
    @property
    def discriminator(self):
        return 'ETFShare'

    def get_factor_model(self):
        return ETFShareFactorModel

    def get_factor_entity(self):
        return ETFShareFactor

    @property
    def model_class(self):
        return ETFShareFactorModel

    @staticmethod
    def to_domain(orm_model: Optional[ETFShareFactorModel]) -> Optional[ETFShareFactor]:
        """Convert ORM model to ETFShareFactor domain entity."""
        if not orm_model:
            return None
        return ETFShareFactor(
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
    def to_orm(domain_entity: ETFShareFactor) -> ETFShareFactorModel:
        """Convert ETFShareFactor domain entity to ORM model."""
        return ETFShareFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
