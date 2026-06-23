"""
Company Share Portfolio Portfolio Holding Value Factor Mapper

Maps between CompanySharePortfolioPortfolioHoldingValueFactor domain entities
and CompanySharePortfolioPortfolioHoldingValueFactorModel ORM models.
"""

from typing import Optional

from src.domain.entities.factor.finance.holding.company_share_portfolio_portfolio.company_share_portfolio_portfolio_holding_value_factor import CompanySharePortfolioPortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import CompanySharePortfolioPortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioPortfolioHoldingValueFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioPortfolioHoldingValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'CompanySharePortfolioPortfolioHolding'

    @property
    def model_class(self):
        return CompanySharePortfolioPortfolioHoldingValueFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioPortfolioHoldingValueFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioPortfolioHoldingValueFactor

    def to_domain(self, orm_model: Optional[CompanySharePortfolioPortfolioHoldingValueFactorModel]) -> Optional[CompanySharePortfolioPortfolioHoldingValueFactor]:
        """Convert ORM model to CompanySharePortfolioPortfolioHoldingValueFactor domain entity."""
        if not orm_model:
            return None

        return CompanySharePortfolioPortfolioHoldingValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanySharePortfolioPortfolioHoldingValueFactor) -> CompanySharePortfolioPortfolioHoldingValueFactorModel:
        """Convert CompanySharePortfolioPortfolioHoldingValueFactor domain entity to ORM model."""
        return CompanySharePortfolioPortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_portfolio_portfolio_holding_value_factor",
        )
