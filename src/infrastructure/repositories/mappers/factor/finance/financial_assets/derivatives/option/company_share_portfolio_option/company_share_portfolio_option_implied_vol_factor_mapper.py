from typing import Optional
from src.infrastructure.models.factor.factor import CompanySharePortfolioOptionImpliedVolFactorModel
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_implied_vol_factor import CompanySharePortfolioOptionImpliedVolFactor
from ......base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioOptionImpliedVolFactorMapper(BaseFactorMapper):
    @property
    def discriminator(self):
        return 'CompanySharePortfolioOptionImpliedVol'

    @property
    def model_class(self):
        return CompanySharePortfolioOptionImpliedVolFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioOptionImpliedVolFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioOptionImpliedVolFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[CompanySharePortfolioOptionImpliedVolFactorModel]) -> Optional[CompanySharePortfolioOptionImpliedVolFactor]:
        if not orm_model:
            return None
        return CompanySharePortfolioOptionImpliedVolFactor(
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
    def to_orm(cls, domain_entity: CompanySharePortfolioOptionImpliedVolFactor) -> CompanySharePortfolioOptionImpliedVolFactorModel:
        return CompanySharePortfolioOptionImpliedVolFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
