from typing import Optional
from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionValueFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_value_factor import CompanySharePortfolioOptionValueFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionValueFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self):
        return 'CompanySharePortfolioOptionValue'

    @property
    def model_class(self):
        return CompanySharePortfolioOptionValueFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioOptionValueFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioOptionValueFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[CompanySharePortfolioOptionValueFactorModel]) -> Optional[CompanySharePortfolioOptionValueFactor]:
        if not orm_model:
            return None
        return CompanySharePortfolioOptionValueFactor(
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
    def to_orm(cls, domain_entity: CompanySharePortfolioOptionValueFactor) -> CompanySharePortfolioOptionValueFactorModel:
        return CompanySharePortfolioOptionValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
