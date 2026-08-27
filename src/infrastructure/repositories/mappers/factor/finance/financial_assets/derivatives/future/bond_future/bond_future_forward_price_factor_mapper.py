from typing import Optional

from src.infrastructure.models.factor.factor import BondFutureForwardPriceFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_forward_price_factor import BondFutureForwardPriceFactor
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class BondFutureForwardPriceFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'BondFutureForwardPrice'

    @property
    def model_class(self):
        return BondFutureForwardPriceFactorModel

    def get_factor_model(self):
        return BondFutureForwardPriceFactorModel

    def get_factor_entity(self):
        return BondFutureForwardPriceFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[BondFutureForwardPriceFactorModel]) -> Optional[BondFutureForwardPriceFactor]:
        if not orm_model:
            return None
        return BondFutureForwardPriceFactor(
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
    def to_orm(cls, domain_entity: BondFutureForwardPriceFactor) -> BondFutureForwardPriceFactorModel:
        return BondFutureForwardPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
