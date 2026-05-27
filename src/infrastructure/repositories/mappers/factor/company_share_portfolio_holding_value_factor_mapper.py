"""
Company Share Portfolio Holding Value Factor Mapper

Maps between CompanySharePortfolioHoldingValueFactor domain entities
and CompanySharePortfolioHoldingValueFactorModel ORM models.
"""

from typing import Optional

from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import CompanySharePortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CompanySharePortfolioHoldingValueFactorMapper(BaseFactorMapper):
    """Mapper for CompanySharePortfolioHoldingValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'company_share_portfolio_holding'

    @property
    def model_class(self):
        return CompanySharePortfolioHoldingValueFactorModel

    def get_factor_model(self):
        return CompanySharePortfolioHoldingValueFactorModel

    def get_factor_entity(self):
        return CompanySharePortfolioHoldingValueFactor

    def to_domain(self, orm_model: Optional[CompanySharePortfolioHoldingValueFactorModel]) -> Optional[CompanySharePortfolioHoldingValueFactor]:
        """Convert ORM model to CompanySharePortfolioHoldingValueFactor domain entity."""
        if not orm_model:
            return None

        return CompanySharePortfolioHoldingValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CompanySharePortfolioHoldingValueFactor) -> CompanySharePortfolioHoldingValueFactorModel:
        """Convert CompanySharePortfolioHoldingValueFactor domain entity to ORM model."""
        return CompanySharePortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="company_share_portfolio_holding_value_factor",
        )
