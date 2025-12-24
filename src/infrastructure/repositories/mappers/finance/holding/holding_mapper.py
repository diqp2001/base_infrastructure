"""
Mappers for converting between holding domain entities and infrastructure models
"""
from typing import Optional

from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
from infrastructure.models.finance.holding.holding import (
    Holding
)


class HoldingMapper:
    """Mapper for converting between holding entities and models"""

    def to_entity(self, model: Optional[Holding]) -> Optional[Holding]:
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

    def to_model(self, entity: Holding) -> Holding:
        """Convert Holding entity to HoldingModel"""
        return Holding(
            id=entity.id,
            asset_id=entity.asset.id,
            container_id=entity.id,
            start_date=entity.start_date,
            end_date=entity.end_date
        )

   