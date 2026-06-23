from typing import Optional

from src.domain.entities.finance.holding.company_share_portfolio_portfolio_holding import (
    CompanySharePortfolioPortfolioHolding as DomainEntity,
)
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
    CompanySharePortfolioPortfolioHoldingModel as ORMModel,
)


class CompanySharePortfolioPortfolioHoldingMapper:
    """Mapper for CompanySharePortfolioPortfolioHolding: a Portfolio holds a CompanySharePortfolio."""

    @property
    def discriminator(self):
        return "CompanySharePortfolioPortfolioHoldings"

    @property
    def model_class(self):
        return ORMModel

    @property
    def asset_class(self):
        return CompanySharePortfolio

    @property
    def container_class(self):
        return Portfolio

    @property
    def entity_class(self):
        return DomainEntity

    def to_entity(self, model: Optional[ORMModel]) -> Optional[DomainEntity]:
        if not model:
            return None

        sub_portfolio = type("CompanySharePortfolio", (), {"id": model.asset_id})()
        container = type("Portfolio", (), {"id": model.container_id})()

        return DomainEntity(
            id=model.id,
            portfolio=container,
            company_share_portfolio=sub_portfolio,
            position=None,
            start_date=getattr(model, "start_date", None),
            end_date=getattr(model, "end_date", None),
        )

    def to_model(self, entity: DomainEntity) -> ORMModel:
        return ORMModel(
            id=entity.id,
            holding_type=self.discriminator,
            asset_id=entity.company_share_portfolio.id if entity.company_share_portfolio else None,
            container_id=entity.portfolio.id if entity.portfolio else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
