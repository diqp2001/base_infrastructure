from typing import Optional

from src.infrastructure.models.factor.factor import BondFutureAnnualizedYieldFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_annualized_yield_factor import BondFutureAnnualizedYieldFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class BondFutureAnnualizedYieldFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'BondFuture'

    @property
    def model_class(self):
        return BondFutureAnnualizedYieldFactorModel

    def get_factor_model(self):
        return BondFutureAnnualizedYieldFactorModel

    def get_factor_entity(self):
        return BondFutureAnnualizedYieldFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[BondFutureAnnualizedYieldFactorModel]) -> Optional[BondFutureAnnualizedYieldFactor]:
        if not orm_model:
            return None
        return BondFutureAnnualizedYieldFactor(
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
    def to_orm(cls, domain_entity: BondFutureAnnualizedYieldFactor) -> BondFutureAnnualizedYieldFactorModel:
        return BondFutureAnnualizedYieldFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
