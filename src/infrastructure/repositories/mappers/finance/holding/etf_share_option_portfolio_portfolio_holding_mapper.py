from typing import Optional

from src.domain.entities.finance.holding.etf_share_option_portfolio_portfolio_holding import (
    ETFShareOptionPortfolioPortfolioHolding as DomainEntity,
)
from src.domain.entities.finance.portfolio.etf_share_option_portfolio import ETFShareOptionPortfolio
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.infrastructure.models.finance.holding.etf_share_option_portfolio_portfolio_holding import (
    ETFShareOptionPortfolioPortfolioHoldingModel as ORMModel,
)


class ETFShareOptionPortfolioPortfolioHoldingMapper:
    """Mapper for ETFShareOptionPortfolioPortfolioHolding: a Portfolio holds a ETFShareOptionPortfolio."""

    @property
    def discriminator(self):
        return "ETFShareOptionPortfolioPortfolioHoldings"

    @property
    def model_class(self):
        return ORMModel

    @property
    def asset_class(self):
        return ETFShareOptionPortfolio

    @property
    def container_class(self):
        return Portfolio

    @property
    def entity_class(self):
        return DomainEntity

    def to_entity(self, model: Optional[ORMModel]) -> Optional[DomainEntity]:
        if not model:
            return None

        sub_portfolio = type("ETFShareOptionPortfolio", (), {"id": model.asset_id})()
        container = type("Portfolio", (), {"id": model.container_id})()

        return DomainEntity(
            id=model.id,
            portfolio=container,
            etf_share_option_portfolio=sub_portfolio,
            position=None,
            start_date=getattr(model, "start_date", None),
            end_date=getattr(model, "end_date", None),
        )

    def to_model(self, entity: DomainEntity) -> ORMModel:
        return ORMModel(
            id=entity.id,
            holding_type=self.discriminator,
            asset_id=entity.etf_share_option_portfolio.id if entity.etf_share_option_portfolio else None,
            container_id=entity.portfolio.id if entity.portfolio else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
