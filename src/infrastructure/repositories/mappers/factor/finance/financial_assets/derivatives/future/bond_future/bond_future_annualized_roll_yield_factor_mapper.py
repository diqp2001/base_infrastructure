from typing import Optional

from src.infrastructure.models.factor.factor import BondFutureAnnualizedRollYieldFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_roll_yield_factor import BondFutureAnnualizedRollYieldFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class BondFutureAnnualizedRollYieldFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'BondFutureAnnualizedRollYield'

    @property
    def model_class(self):
        return BondFutureAnnualizedRollYieldFactorModel

    def get_factor_model(self):
        return BondFutureAnnualizedRollYieldFactorModel

    def get_factor_entity(self):
        return BondFutureAnnualizedRollYieldFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[BondFutureAnnualizedRollYieldFactorModel]) -> Optional[BondFutureAnnualizedRollYieldFactor]:
        if not orm_model:
            return None
        return BondFutureAnnualizedRollYieldFactor(
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
    def to_orm(cls, domain_entity: BondFutureAnnualizedRollYieldFactor) -> BondFutureAnnualizedRollYieldFactorModel:
        return BondFutureAnnualizedRollYieldFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
