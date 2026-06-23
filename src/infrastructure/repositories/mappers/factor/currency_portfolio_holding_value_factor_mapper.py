from typing import Optional

from src.domain.entities.factor.finance.holding.currency_portfolio_holding_value_factor import CurrencyPortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import CurrencyPortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CurrencyPortfolioHoldingValueFactorMapper(BaseFactorMapper):
    """Mapper for CurrencyPortfolioHoldingValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'CurrencyPortfolioHolding'

    @property
    def model_class(self):
        return CurrencyPortfolioHoldingValueFactorModel

    def get_factor_model(self):
        return CurrencyPortfolioHoldingValueFactorModel

    def get_factor_entity(self):
        return CurrencyPortfolioHoldingValueFactor

    def to_domain(self, orm_model: Optional[CurrencyPortfolioHoldingValueFactorModel]) -> Optional[CurrencyPortfolioHoldingValueFactor]:
        if not orm_model:
            return None
        return CurrencyPortfolioHoldingValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CurrencyPortfolioHoldingValueFactor) -> CurrencyPortfolioHoldingValueFactorModel:
        return CurrencyPortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="currency_portfolio_holding_value_factor",
        )
