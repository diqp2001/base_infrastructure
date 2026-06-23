from typing import Optional

from src.domain.entities.factor.finance.holding.currency_portfolio_portfolio.currency_portfolio_portfolio_holding_value_factor import CurrencyPortfolioPortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import CurrencyPortfolioPortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CurrencyPortfolioPortfolioHoldingValueFactorMapper(BaseFactorMapper):
    """Mapper for CurrencyPortfolioPortfolioHoldingValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'CurrencyPortfolioPortfolioHolding'

    @property
    def model_class(self):
        return CurrencyPortfolioPortfolioHoldingValueFactorModel

    def get_factor_model(self):
        return CurrencyPortfolioPortfolioHoldingValueFactorModel

    def get_factor_entity(self):
        return CurrencyPortfolioPortfolioHoldingValueFactor

    def to_domain(self, orm_model: Optional[CurrencyPortfolioPortfolioHoldingValueFactorModel]) -> Optional[CurrencyPortfolioPortfolioHoldingValueFactor]:
        if not orm_model:
            return None
        return CurrencyPortfolioPortfolioHoldingValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CurrencyPortfolioPortfolioHoldingValueFactor) -> CurrencyPortfolioPortfolioHoldingValueFactorModel:
        return CurrencyPortfolioPortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="currency_portfolio_portfolio_holding_value_factor",
        )
