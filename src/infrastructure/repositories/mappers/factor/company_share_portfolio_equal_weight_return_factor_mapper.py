from typing import Optional

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_equal_weight_return_factor import CompanySharePortfolioEqualWeightReturnFactor
from src.infrastructure.models.factor.factor import CompanySharePortfolioEqualWeightReturnFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioEqualWeightReturnFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self) -> str:
        return 'CompanySharePortfolio'

    @property
    def model_class(self):
        return CompanySharePortfolioEqualWeightReturnFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioEqualWeightReturnFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioEqualWeightReturnFactor

    def to_domain(self, orm_model: Optional[CompanySharePortfolioEqualWeightReturnFactorModel]) -> Optional[CompanySharePortfolioEqualWeightReturnFactor]:
        if not orm_model:
            return None
        return CompanySharePortfolioEqualWeightReturnFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanySharePortfolioEqualWeightReturnFactor) -> CompanySharePortfolioEqualWeightReturnFactorModel:
        return CompanySharePortfolioEqualWeightReturnFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_portfolio_equal_weight_return_factor",
        )
