from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareOptionVolFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vol_factor import CompanyShareOptionVolFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanyShareOptionVolFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self):
        return 'CompanyShareOptionVol'

    @property
    def model_class(self):
        return CompanyShareOptionVolFactorModel

    def get_factor_model(self):
        return CompanyShareOptionVolFactorModel

    def get_factor_entity(self):
        return CompanyShareOptionVolFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionVolFactorModel]) -> Optional[CompanyShareOptionVolFactor]:
        if not orm_model:
            return None
        return CompanyShareOptionVolFactor(
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
    def to_orm(cls, domain_entity: CompanyShareOptionVolFactor) -> CompanyShareOptionVolFactorModel:
        return CompanyShareOptionVolFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
