from typing import Optional

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.domain.entities.finance.portfolio.company_share_portfolio import CompanySharePortfolio
from src.domain.entities.finance.holding.company_share_portfolio_holding import (
    CompanySharePortfolioHolding
)

from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
    CompanySharePortfolioHoldingModel 
)


class CompanySharePortfolioHoldingMapper:
    """Mapper for converting between PortfolioCompanyShareHolding entities and models"""
    @property
    def discriminator(self):
        return "CompanySharePortfolioHoldings"

    @property
    def model_class(self):
        return CompanySharePortfolioHoldingModel
    @property
    def asset_class(self):
        return CompanyShare
    @property
    def container_class(self):
        return CompanySharePortfolio

    @property
    def entity_class(self):
        return CompanySharePortfolioHolding

    def to_entity(
        self,
        model: Optional[CompanySharePortfolioHoldingModel],
    ) -> Optional[CompanySharePortfolioHoldingModel]:
        """Convert PortfolioCompanyShareHoldingModel to domain entity"""
        if not model:
            return None

        # --- Lazy imports to avoid circular dependencies --------------------
      

        # Placeholder PortfolioCompanyShare asset
        asset = CompanySharePortfolio(
            id=model.asset_id,
            name=model.name,
            start_date=model.start_date,
            end_date=model.end_date,
        )

        # Placeholder portfolio container
        portfolio = type("Portfolio", (), {"id": model.portfolio_id})()

        return CompanySharePortfolioHolding(
            id=model.id,
            asset=asset,
            container=portfolio,
            quantity=model.quantity,
            start_date=model.start_date,
            end_date=model.end_date,
        )

    def to_model(
        self,
        entity: CompanySharePortfolioHoldingModel,
    ) -> CompanySharePortfolioHoldingModel:
        """Convert PortfolioCompanyShareHolding entity to infrastructure model"""

        return CompanySharePortfolioHoldingModel(
            id=entity.id,
            holding_type=self.discriminator,
            asset_id=entity.asset.id,
            portfolio_id=entity.container.id,
            quantity=entity.quantity,
            ticker=entity.asset.ticker,
            exchange=entity.asset.exchange,
            currency=entity.asset.currency,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
