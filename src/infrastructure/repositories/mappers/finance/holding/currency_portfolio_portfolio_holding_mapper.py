from typing import Optional

from src.domain.entities.finance.holding.currency_portfolio_portfolio_holding import (
    CurrencyPortfolioPortfolioHolding as DomainEntity,
)
from src.domain.entities.finance.portfolio.currency_portfolio import CurrencyPortfolio
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import (
    CurrencyPortfolioPortfolioHoldingModel as ORMModel,
)


class CurrencyPortfolioPortfolioHoldingMapper:
    """Mapper for CurrencyPortfolioPortfolioHolding: a Portfolio holds a CurrencyPortfolio."""

    @property
    def discriminator(self):
        return "CurrencyPortfolioPortfolioHoldings"

    @property
    def model_class(self):
        return ORMModel

    @property
    def asset_class(self):
        return CurrencyPortfolio

    @property
    def container_class(self):
        return Portfolio

    @property
    def entity_class(self):
        return DomainEntity

    def to_entity(self, model: Optional[ORMModel]) -> Optional[DomainEntity]:
        if not model:
            return None

        # currency_portfolio_id is the Python attribute for the asset_id DB column
        asset_id = getattr(model, "currency_portfolio_id", None) or getattr(model, "asset_id", None)
        sub_portfolio = type("CurrencyPortfolio", (), {"id": asset_id})()
        container = type("Portfolio", (), {"id": model.container_id})()

        return DomainEntity(
            id=model.id,
            portfolio=container,
            currency_portfolio=sub_portfolio,
            position=None,
            start_date=getattr(model, "start_date", None),
            end_date=getattr(model, "end_date", None),
        )

    def to_model(self, entity: DomainEntity) -> ORMModel:
        # PortfolioHolding stores the portfolio kwarg as self.container (via Holding.__init__)
        portfolio_id = entity.container.id if entity.container else None
        sub_portfolio_id = entity.currency_portfolio.id if entity.currency_portfolio else None
        return ORMModel(
            id=entity.id,
            holding_type=self.discriminator,
            # asset_id sets holdings.asset_id (base table, no FK); currency_portfolio_id
            # sets currency_portfolio_portfolio_holdings.asset_id (child table FK).
            # Both are set explicitly because no column_property merges them.
            asset_id=sub_portfolio_id,
            currency_portfolio_id=sub_portfolio_id,
            portfolio_id=portfolio_id,
            container_id=portfolio_id,
            currency_portfolio_portfolio_id=portfolio_id,
            position_id=entity.position.id if entity.position else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
