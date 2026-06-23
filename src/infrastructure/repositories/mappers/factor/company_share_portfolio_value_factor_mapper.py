"""
Company Share Portfolio Value Factor Mapper

Maps between CompanySharePortfolioValueFactor domain entities
and CompanySharePortfolioValueFactorModel ORM models.
"""

from typing import Optional

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor
from src.infrastructure.models.factor.factor import CompanySharePortfolioValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioValueFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'CompanySharePortfolio'

    @property
    def model_class(self):
        return CompanySharePortfolioValueFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioValueFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioValueFactor

    def to_domain(self, orm_model: Optional[CompanySharePortfolioValueFactorModel]) -> Optional[CompanySharePortfolioValueFactor]:
        """Convert ORM model to CompanySharePortfolioValueFactor domain entity."""
        if not orm_model:
            return None

        return CompanySharePortfolioValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanySharePortfolioValueFactor) -> CompanySharePortfolioValueFactorModel:
        """Convert CompanySharePortfolioValueFactor domain entity to ORM model."""
        return CompanySharePortfolioValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_portfolio_value_factor",
        )
