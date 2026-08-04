from typing import Optional

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_price_return_factor import CompanySharePortfolioPriceReturnFactor
from src.infrastructure.models.factor.factor import CompanySharePortfolioPriceReturnFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioPriceReturnFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self) -> str:
        return 'CompanySharePortfolio'

    @property
    def model_class(self):
        return CompanySharePortfolioPriceReturnFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioPriceReturnFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioPriceReturnFactor

    def to_domain(self, orm_model: Optional[CompanySharePortfolioPriceReturnFactorModel]) -> Optional[CompanySharePortfolioPriceReturnFactor]:
        if not orm_model:
            return None
        return CompanySharePortfolioPriceReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanySharePortfolioPriceReturnFactor) -> CompanySharePortfolioPriceReturnFactorModel:
        return CompanySharePortfolioPriceReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_portfolio_price_return_factor",
        )
