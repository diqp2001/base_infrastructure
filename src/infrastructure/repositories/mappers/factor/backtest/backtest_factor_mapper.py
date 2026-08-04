from typing import Optional
from src.infrastructure.models.factor.factor import BacktestFactorModel
from src.domain.entities.factor.backtest.backtest_factor import BacktestFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class BacktestFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'BacktestFactor'

    def get_factor_model(self):
        return BacktestFactorModel

    def get_factor_entity(self):
        return BacktestFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[BacktestFactorModel]) -> Optional[BacktestFactor]:
        if not orm_model:
            return None
        return BacktestFactor(
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
            factor_id=orm_model.id,
        )

    @classmethod
    def to_orm(cls, domain_entity: BacktestFactor) -> BacktestFactorModel:
        return BacktestFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
