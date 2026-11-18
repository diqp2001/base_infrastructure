"""
Mapper for PortfolioETFShareOptionHolding domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.holding.etf_share_option_portfolio_holding import ETFShareOptionPortfolioHolding as DomainEntity
from src.domain.entities.finance.financial_assets.derivatives.option.etf_share_option import ETFShareOption
from src.domain.entities.finance.portfolio.etf_share_option_portfolio import ETFShareOptionPortfolio
from src.infrastructure.models.finance.holding.etf_share_option_portfolio_holding import ETFShareOptionPortfolioHoldingModel as ORMModel


class ETFShareOptionPortfolioHoldingMapper:
    """Mapper for PortfolioETFShareOptionHolding domain entity and ORM model."""

    @property
    def discriminator(self):
        return "ETFShareOptionPortfolioHoldings"

    @property
    def model_class(self):
        return ORMModel

    @property
    def asset_class(self):
        return ETFShareOption

    @property
    def container_class(self):
        return ETFShareOptionPortfolio

    @property
    def entity_class(self):
        return DomainEntity

    def get_entity(self):
        return DomainEntity

    def to_entity(self, orm_model: Optional[ORMModel]) -> Optional[DomainEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None

        # Note: This is a simplified mapping - in practice you'd need to 
        # resolve the asset, portfolio, and position relationships
        return DomainEntity(
            id=orm_model.id,
            asset=None,  # Would need to resolve ETFShareOption
            portfolio=None,  # Would need to resolve PortfolioETFShareOption
            position=None,  # Would need to resolve Position
            start_date=orm_model.start_date,
            end_date=orm_model.end_date,
        )

    def to_model(self, entity: DomainEntity) -> ORMModel:
        """Convert domain entity to ORM model."""
        return ORMModel(
            id=entity.id,
            holding_type=self.discriminator,
            asset_id=entity.asset.id if entity.asset else None,
            portfolio_etf_share_option_id=entity.portfolio.id if entity.portfolio else None,
            etf_share_option_id=entity.asset.id if entity.asset else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )