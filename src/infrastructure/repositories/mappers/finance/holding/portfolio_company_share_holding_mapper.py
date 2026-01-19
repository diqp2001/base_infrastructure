from typing import Optional

from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare
from src.domain.entities.finance.holding.portfolio_company_share_holding import (
    PortfolioCompanyShareHolding
)

from src.infrastructure.models.finance.holding.portfolio_company_share_holding import (
    PortfolioCompanyShareHoldingModel
)


class PortfolioCompanyShareHoldingMapper:
    """Mapper for converting between PortfolioCompanyShareHolding entities and models"""

    def to_entity(
        self,
        model: Optional[PortfolioCompanyShareHoldingModel],
    ) -> Optional[PortfolioCompanyShareHoldingModel]:
        """Convert PortfolioCompanyShareHoldingModel to domain entity"""
        if not model:
            return None

        # --- Lazy imports to avoid circular dependencies --------------------
      

        # Placeholder PortfolioCompanyShare asset
        asset = PortfolioCompanyShare(
            id=model.asset_id,
            name=model.name,
            start_date=model.start_date,
            end_date=model.end_date,
        )

        # Placeholder portfolio container
        portfolio = type("Portfolio", (), {"id": model.portfolio_id})()

        return PortfolioCompanyShareHolding(
            id=model.id,
            asset=asset,
            container=portfolio,
            quantity=model.quantity,
            start_date=model.start_date,
            end_date=model.end_date,
        )

    def to_model(
        self,
        entity: PortfolioCompanyShareHoldingModel,
    ) -> PortfolioCompanyShareHoldingModel:
        """Convert PortfolioCompanyShareHolding entity to infrastructure model"""

        return PortfolioCompanyShareHoldingModel(
            id=entity.id,
            asset_id=entity.asset.id,
            portfolio_id=entity.container.id,
            quantity=entity.quantity,
            ticker=entity.asset.ticker,
            exchange=entity.asset.exchange,
            currency=entity.asset.currency,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
