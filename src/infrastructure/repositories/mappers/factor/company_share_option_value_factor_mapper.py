from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_value_factor import CompanyShareOptionValueFactor
from src.infrastructure.models.factor.factor import CompanyShareOptionValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareOptionValueFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShareOptionValue'

    @property
    def model_class(self):
        return CompanyShareOptionValueFactorModel

    def get_factor_model(self):
        return CompanyShareOptionValueFactorModel

    def get_factor_entity(self):
        return CompanyShareOptionValueFactor

    def to_domain(self, orm_model: Optional[CompanyShareOptionValueFactorModel]) -> Optional[CompanyShareOptionValueFactor]:
        if not orm_model:
            return None
        return CompanyShareOptionValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanyShareOptionValueFactor) -> CompanyShareOptionValueFactorModel:
        return CompanyShareOptionValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_option_value_factor",
        )
