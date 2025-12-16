"""
Mappers for converting between holding domain entities and infrastructure models
"""
from typing import Optional

from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
from src.infrastructure.models.finance.holding import (
    HoldingModel,
    PortfolioHoldingModel,
    PortfolioCompanyShareHoldingModel
)


class HoldingMapper:
    """Mapper for converting between holding entities and models"""

    def to_entity(self, model: Optional[HoldingModel]) -> Optional[Holding]:
        """Convert HoldingModel to Holding entity"""
        if not model:
            return None

        # For now, we'll use a simplified approach where asset is just referenced by ID
        # In a full implementation, you'd load the actual asset entity
        from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
        
        # Create a placeholder FinancialAsset - in real implementation you'd load from repository
        asset = FinancialAsset(id=model.asset_id, start_date=model.start_date.date(), end_date=model.end_date.date() if model.end_date else None)

        # Create a placeholder container object - in real implementation you'd load from repository
        container = type('Container', (), {'id': model.container_id})()

        return Holding(
            id=model.id,
            asset=asset,
            container=container,
            start_date=model.start_date,
            end_date=model.end_date
        )

    def to_model(self, entity: Holding) -> HoldingModel:
        """Convert Holding entity to HoldingModel"""
        return HoldingModel(
            id=entity.id,
            asset_id=entity.asset.id,
            container_id=entity.container.id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )

    def portfolio_holding_to_entity(self, model: Optional[PortfolioHoldingModel]) -> Optional[PortfolioHolding]:
        """Convert PortfolioHoldingModel to PortfolioHolding entity"""
        if not model:
            return None

        # Create base holding first
        base_holding = self.to_entity(model)
        if not base_holding:
            return None

        # Create a placeholder portfolio - in real implementation you'd load from repository
        from src.domain.entities.finance.portfolio.portfolio import Portfolio
        portfolio = Portfolio(
            id=model.portfolio_id,
            name=f"Portfolio_{model.portfolio_id}",
            start_date=model.start_date.date(),
            end_date=model.end_date.date() if model.end_date else None
        )

        return PortfolioHolding(
            id=base_holding.id,
            portfolio=portfolio,
            asset=base_holding.asset,
            start_date=base_holding.start_date,
            end_date=base_holding.end_date
        )

    def portfolio_holding_to_model(self, entity: PortfolioHolding) -> PortfolioHoldingModel:
        """Convert PortfolioHolding entity to PortfolioHoldingModel"""
        return PortfolioHoldingModel(
            id=entity.id,
            asset_id=entity.asset.id,
            container_id=entity.portfolio.id,
            portfolio_id=entity.portfolio.id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )

    def portfolio_company_share_holding_to_entity(self, model: Optional[PortfolioCompanyShareHoldingModel]) -> Optional[PortfolioCompanyShareHolding]:
        """Convert PortfolioCompanyShareHoldingModel to PortfolioCompanyShareHolding entity"""
        if not model:
            return None

        # Create placeholder objects - in real implementation you'd load from repositories
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
        from src.domain.entities.finance.portfolio.portfolio_company_share import PortfolioCompanyShare

        company_share = CompanyShare(
            id=model.company_share_id,
            start_date=model.start_date.date(),
            end_date=model.end_date.date() if model.end_date else None
        )
        
        portfolio = PortfolioCompanyShare(
            id=model.portfolio_company_share_id,
            start_date=model.start_date.date(),
            end_date=model.end_date.date() if model.end_date else None
        )

        return PortfolioCompanyShareHolding(
            id=model.id,
            asset=company_share,
            portfolio=portfolio,
            start_date=model.start_date,
            end_date=model.end_date
        )

    def portfolio_company_share_holding_to_model(self, entity: PortfolioCompanyShareHolding) -> PortfolioCompanyShareHoldingModel:
        """Convert PortfolioCompanyShareHolding entity to PortfolioCompanyShareHoldingModel"""
        return PortfolioCompanyShareHoldingModel(
            id=entity.id,
            asset_id=entity.asset.id,
            container_id=entity.portfolio.id,
            portfolio_id=entity.portfolio.id,
            company_share_id=entity.asset.id,
            portfolio_company_share_id=entity.portfolio.id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )