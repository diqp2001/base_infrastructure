from typing import Optional

from src.domain.entities.finance.financial_assets.currency import Currency
from src.domain.entities.finance.holding.currency_portfolio_holding import CurrencyPortfolioHolding
from src.infrastructure.models.finance.holding.currency_portfolio_holding import CurrencyPortfolioHoldingModel


class CurrencyPortfolioHoldingMapper:
    """Mapper for CurrencyPortfolioHolding domain entity ↔ ORM model."""

    @property
    def discriminator(self):
        return "currency_portfolio_holding"

    @property
    def model_class(self):
        return CurrencyPortfolioHoldingModel

    def to_entity(
        self, model: Optional[CurrencyPortfolioHoldingModel]
    ) -> Optional[CurrencyPortfolioHolding]:
        if not model:
            return None

        # Placeholder domain objects; load full objects when relationships are needed
        asset = Currency(
            id=model.asset_id,
            name=None,
            symbol=None,
        )
        portfolio = type("CurrencyPortfolio", (), {"id": model.currency_portfolio_id})()

        return CurrencyPortfolioHolding(
            id=model.id,
            asset=asset,
            portfolio=portfolio,
            position=None,
            start_date=getattr(model, 'start_date', None),
            end_date=getattr(model, 'end_date', None),
        )

    def to_model(self, entity: CurrencyPortfolioHolding) -> CurrencyPortfolioHoldingModel:
        return CurrencyPortfolioHoldingModel(
            id=entity.id,
            asset_id=entity.asset.id,
            currency_portfolio_id=entity.container.id,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
