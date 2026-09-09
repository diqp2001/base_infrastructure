"""
src/infrastructure/repositories/mappers/factor/constituent_score_factor_mapper.py

Mapper for ConstituentScoreFactor domain entity ↔ ORM model.
"""

from typing import Optional
from src.domain.entities.factor.constituent_score_factor import ConstituentScoreFactor
from src.infrastructure.models.factor.factor import ConstituentScoreFactorModel


class ConstituentScoreFactorMapper:

    @property
    def discriminator(self) -> str:
        return "ConstituentScoreFactor"

    @property
    def model_class(self):
        return ConstituentScoreFactorModel

    def get_entity(self):
        return ConstituentScoreFactor

    def get_factor_model(self):
        return ConstituentScoreFactorModel

    def get_factor_entity(self):
        return ConstituentScoreFactor

    def to_domain(self, orm_model: Optional[ConstituentScoreFactorModel]) -> Optional[ConstituentScoreFactor]:
        if not orm_model:
            return None
        return ConstituentScoreFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, entity: ConstituentScoreFactor) -> ConstituentScoreFactorModel:
        return ConstituentScoreFactorModel(
            id=entity.id,
            name=entity.name,
            group=entity.group,
            subgroup=entity.subgroup,
            frequency=entity.frequency,
            data_type=entity.data_type,
            source=entity.source,
            definition=entity.definition,
        )
