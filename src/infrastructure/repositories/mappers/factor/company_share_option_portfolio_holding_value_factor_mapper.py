from typing import Optional

from src.domain.entities.factor.finance.holding.company_share_option_portfolio.company_share_option_portfolio_holding_value_factor import CompanyShareOptionPortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import CompanyShareOptionPortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanyShareOptionPortfolioHoldingValueFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'CompanyShareOptionPortfolioHolding'

    @property
    def model_class(self):
        return CompanyShareOptionPortfolioHoldingValueFactorModel

    def get_factor_model(self):
        return CompanyShareOptionPortfolioHoldingValueFactorModel

    def get_factor_entity(self):
        return CompanyShareOptionPortfolioHoldingValueFactor

    def to_domain(self, orm_model: Optional[CompanyShareOptionPortfolioHoldingValueFactorModel]) -> Optional[CompanyShareOptionPortfolioHoldingValueFactor]:
        if not orm_model:
            return None
        return CompanyShareOptionPortfolioHoldingValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanyShareOptionPortfolioHoldingValueFactor) -> CompanyShareOptionPortfolioHoldingValueFactorModel:
        return CompanyShareOptionPortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_option_portfolio_holding_value_factor",
        )
