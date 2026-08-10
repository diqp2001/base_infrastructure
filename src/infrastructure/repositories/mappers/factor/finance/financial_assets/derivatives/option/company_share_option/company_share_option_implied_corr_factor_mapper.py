from typing import Optional
from src.infrastructure.models.factor.factor import CompanyShareOptionImpliedCorrFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_corr_factor import CompanyShareOptionImpliedCorrFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanyShareOptionImpliedCorrFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self):
        return 'CompanyShareOptionImpliedCorr'

    @property
    def model_class(self):
        return CompanyShareOptionImpliedCorrFactorModel

    def get_factor_model(self):
        return CompanyShareOptionImpliedCorrFactorModel

    def get_factor_entity(self):
        return CompanyShareOptionImpliedCorrFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[CompanyShareOptionImpliedCorrFactorModel]) -> Optional[CompanyShareOptionImpliedCorrFactor]:
        if not orm_model:
            return None
        return CompanyShareOptionImpliedCorrFactor(
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
    def to_orm(cls, domain_entity: CompanyShareOptionImpliedCorrFactor) -> CompanyShareOptionImpliedCorrFactorModel:
        return CompanyShareOptionImpliedCorrFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
