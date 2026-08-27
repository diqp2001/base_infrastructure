from typing import Optional

from src.infrastructure.models.factor.factor import BondFutureDiscountedValueFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_discounted_value_factor import BondFutureDiscountedValueFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class BondFutureDiscountedValueFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'BondFutureDiscountedValue'

    @property
    def model_class(self):
        return BondFutureDiscountedValueFactorModel

    def get_factor_model(self):
        return BondFutureDiscountedValueFactorModel

    def get_factor_entity(self):
        return BondFutureDiscountedValueFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[BondFutureDiscountedValueFactorModel]) -> Optional[BondFutureDiscountedValueFactor]:
        if not orm_model:
            return None
        return BondFutureDiscountedValueFactor(
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
    def to_orm(cls, domain_entity: BondFutureDiscountedValueFactor) -> BondFutureDiscountedValueFactorModel:
        return BondFutureDiscountedValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
