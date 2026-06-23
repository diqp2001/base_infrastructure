"""
Mapper for CompanySharePortfolioOptionPortfolioHolding domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.holding.company_share_portfolio_option_portfolio_holding import CompanySharePortfolioOptionPortfolioHolding as DomainEntity
from src.domain.entities.finance.financial_assets.derivatives.option.company_share_portfolio_option import CompanySharePortfolioOption
from src.domain.entities.finance.portfolio.company_share_portfolio_option_portfolio import CompanySharePortfolioOptionPortfolio
from src.infrastructure.models.finance.holding.company_share_portfolio_option_portfolio_holding import CompanySharePortfolioOptionPortfolioHoldingModel as ORMModel


class CompanySharePortfolioOptionPortfolioHoldingMapper:
    """Mapper for CompanySharePortfolioOptionPortfolioHolding domain entity and ORM model."""

    @property
    def discriminator(self):
        return "CompanySharePortfolioOptionPortfolioHoldings"

    @property
    def model_class(self):
        return ORMModel

    @property
    def asset_class(self):
        return CompanySharePortfolioOption

    @property
    def container_class(self):
        return CompanySharePortfolioOptionPortfolio

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
            asset=None,  # Would need to resolve CompanySharePortfolioOption
            portfolio=None,  # Would need to resolve CompanySharePortfolioOptionPortfolio
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
            company_share_portfolio_option_portfolio_id=entity.portfolio.id if entity.portfolio else None,
            company_share_portfolio_option_id=entity.asset.id if entity.asset else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )