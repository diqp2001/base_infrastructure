from typing import Optional

from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.portfolio_company_share_holding import (
    PortfolioCompanyShareHolding
)

from src.infrastructure.models.finance.holding.portfolio_holding import (
    PortfolioHoldingsModel
)


class PortfolioHoldingMapper:
    """Mapper for converting between portfolio holding entities and models"""

    def to_entity(self, model: Optional[PortfolioHoldingsModel]) -> Optional[PortfolioHoldingsModel]:
        """Convert PortfolioHoldingModel to PortfolioHolding entity"""
        if not model:
            return None

        # --- Lazy imports to avoid circular dependencies --------------------
        from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

        # Placeholder FinancialAsset (should be loaded from repository in real impl)
        asset = FinancialAsset(
            id=model.asset_id,
            start_date=model.start_date.date(),
            end_date=model.end_date.date() if model.end_date else None
        )

        # Placeholder portfolio container
        portfolio = type("Portfolio", (), {"id": model.portfolio_id})()

        # --- Company Share Holding specialization ---------------------------
        if model.holding_type == "company_share":
            return PortfolioCompanyShareHolding(
                id=model.id,
                asset=asset,
                container=portfolio,
                quantity=model.quantity,
                start_date=model.start_date,
                end_date=model.end_date,
            )

        # --- Base PortfolioHolding -----------------------------------------
        return PortfolioHoldingsModel(
            id=model.id,
            asset=asset,
            container=portfolio,
            quantity=model.quantity,
            start_date=model.start_date,
            end_date=model.end_date,
        )

    def to_model(self, entity: PortfolioHoldingsModel) -> PortfolioHoldingsModel:
        """Convert PortfolioHolding entity to PortfolioHoldingModel"""

        holding_type = "company_share" if isinstance(entity, PortfolioCompanyShareHolding) else "generic"

        return PortfolioHoldingsModel(
            id=entity.id,
            asset_id=entity.asset.id,
            portfolio_id=entity.container.id,
            quantity=entity.quantity,
            holding_type=holding_type,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )
