from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_value_factor import ETFShareOptionValueFactor
from src.infrastructure.models.factor.factor import ETFShareOptionValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class ETFShareOptionValueFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'ETFShareOption'

    @property
    def model_class(self):
        return ETFShareOptionValueFactorModel

    def get_factor_model(self):
        return ETFShareOptionValueFactorModel

    def get_factor_entity(self):
        return ETFShareOptionValueFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[ETFShareOptionValueFactorModel]) -> Optional[ETFShareOptionValueFactor]:
        if not orm_model:
            return None
        return ETFShareOptionValueFactor(
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
    def to_orm(cls, domain_entity: ETFShareOptionValueFactor) -> ETFShareOptionValueFactorModel:
        return ETFShareOptionValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
