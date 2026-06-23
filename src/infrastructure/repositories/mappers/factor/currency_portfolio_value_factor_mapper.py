from typing import Optional

from src.domain.entities.factor.finance.portfolio.currency_portfolio_value_factor import CurrencyPortfolioValueFactor
from src.infrastructure.models.factor.factor import CurrencyPortfolioValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class CurrencyPortfolioValueFactorMapper(BaseFactorMapper):
    """Mapper for CurrencyPortfolioValueFactor domain entity."""

    @property
    def discriminator(self):
        return 'CurrencyPortfolio'

    @property
    def model_class(self):
        return CurrencyPortfolioValueFactorModel

    def get_factor_model(self):
        return CurrencyPortfolioValueFactorModel

    def get_factor_entity(self):
        return CurrencyPortfolioValueFactor

    def to_domain(self, orm_model: Optional[CurrencyPortfolioValueFactorModel]) -> Optional[CurrencyPortfolioValueFactor]:
        if not orm_model:
            return None
        return CurrencyPortfolioValueFactor(
            factor_id=orm_model.id,
            name=orm_model.name,
            group=orm_model.group,
            subgroup=orm_model.subgroup,
            frequency=orm_model.frequency,
            data_type=orm_model.data_type,
            source=orm_model.source,
            definition=orm_model.definition,
        )

    def to_orm(self, domain_entity: CurrencyPortfolioValueFactor) -> CurrencyPortfolioValueFactorModel:
        return CurrencyPortfolioValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
            factor_type="currency_portfolio_value_factor",
        )
