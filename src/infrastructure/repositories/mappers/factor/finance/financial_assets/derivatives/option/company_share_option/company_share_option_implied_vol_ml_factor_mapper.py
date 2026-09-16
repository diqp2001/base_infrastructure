from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_implied_vol_ml_factor import (
    CompanyShareOptionImpliedVolMlFactor,
)
from src.infrastructure.models.factor.factor import FactorModel


class CompanyShareOptionImpliedVolMlFactorMapper:

    @property
    def discriminator(self) -> str:
        return "CompanyShareOption"

    @property
    def model_class(self):
        from src.infrastructure.models.factor.factor import CompanyShareOptionImpliedVolMlFactorModel
        return CompanyShareOptionImpliedVolMlFactorModel

    def get_factor_model(self):
        from src.infrastructure.models.factor.factor import CompanyShareOptionImpliedVolMlFactorModel
        return CompanyShareOptionImpliedVolMlFactorModel

    def get_factor_entity(self):
        return CompanyShareOptionImpliedVolMlFactor

    def to_domain(self, orm_model) -> Optional[CompanyShareOptionImpliedVolMlFactor]:
        if not orm_model:
            return None
        return CompanyShareOptionImpliedVolMlFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanyShareOptionImpliedVolMlFactor):
        from src.infrastructure.models.factor.factor import CompanyShareOptionImpliedVolMlFactorModel
        return CompanyShareOptionImpliedVolMlFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition or f"CompanyShareOptionImpliedVolMlFactor: {domain_entity.name}",
        )
