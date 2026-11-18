from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_model_price_factor import ETFShareOptionModelPriceFactor
from src.infrastructure.models.factor.factor import ETFShareOptionModelPriceFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class ETFShareOptionModelPriceFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'ETFShareOption'

    @property
    def model_class(self):
        return ETFShareOptionModelPriceFactorModel

    def get_factor_model(self):
        return ETFShareOptionModelPriceFactorModel

    def get_factor_entity(self):
        return ETFShareOptionModelPriceFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[ETFShareOptionModelPriceFactorModel]) -> Optional[ETFShareOptionModelPriceFactor]:
        if not orm_model:
            return None
        return ETFShareOptionModelPriceFactor(
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
    def to_orm(cls, domain_entity: ETFShareOptionModelPriceFactor) -> ETFShareOptionModelPriceFactorModel:
        return ETFShareOptionModelPriceFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
