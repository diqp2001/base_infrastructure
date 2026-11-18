from typing import Optional

from src.domain.entities.factor.finance.holding.etf_share_option_portfolio.etf_share_option_portfolio_holding_value_factor import ETFShareOptionPortfolioHoldingValueFactor
from src.infrastructure.models.factor.factor import ETFShareOptionPortfolioHoldingValueFactorModel
from src.infrastructure.repositories.mappers.factor.base_factor_mapper import BaseFactorMapper


class ETFShareOptionPortfolioHoldingValueFactorMapper(BaseFactorMapper):

    @property
    def discriminator(self):
        return 'ETFShareOptionPortfolioHolding'

    @property
    def model_class(self):
        return ETFShareOptionPortfolioHoldingValueFactorModel

    def get_factor_model(self):
        return ETFShareOptionPortfolioHoldingValueFactorModel

    def get_factor_entity(self):
        return ETFShareOptionPortfolioHoldingValueFactor

    @classmethod
    def to_domain(cls, orm_model: Optional[ETFShareOptionPortfolioHoldingValueFactorModel]) -> Optional[ETFShareOptionPortfolioHoldingValueFactor]:
        if not orm_model:
            return None
        return ETFShareOptionPortfolioHoldingValueFactor(
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
    def to_orm(cls, domain_entity: ETFShareOptionPortfolioHoldingValueFactor) -> ETFShareOptionPortfolioHoldingValueFactorModel:
        return ETFShareOptionPortfolioHoldingValueFactorModel(
            name=domain_entity.name,
            group=domain_entity.group,
            subgroup=domain_entity.subgroup,
            frequency=domain_entity.frequency,
            data_type=domain_entity.data_type,
            source=domain_entity.source,
            definition=domain_entity.definition,
        )
