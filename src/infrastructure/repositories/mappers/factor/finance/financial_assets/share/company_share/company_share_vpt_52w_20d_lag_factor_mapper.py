from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareVpt52w20dLagFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_vpt_52w_20d_lag_factor import CompanyShareVpt52w20dLagFactor


class CompanyShareVpt52w20dLagFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShare'

    @property
    def model_class(self):
        return CompanyShareVpt52w20dLagFactorModel

    def get_factor_model(self):
        return CompanyShareVpt52w20dLagFactorModel

    def get_factor_entity(self):
        return CompanyShareVpt52w20dLagFactor

    def to_domain(self, orm_model: Optional[CompanyShareVpt52w20dLagFactorModel]) -> Optional[CompanyShareVpt52w20dLagFactor]:
        if not orm_model:
            return None
        return CompanyShareVpt52w20dLagFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanyShareVpt52w20dLagFactor) -> CompanyShareVpt52w20dLagFactorModel:
        return CompanyShareVpt52w20dLagFactorModel(
            id=domain_entity.id,
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
