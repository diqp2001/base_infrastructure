"""
Mapper for PortfolioCompanyShareOptionHolding domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.holding.company_share_option_portfolio_holding import PortfolioCompanyShareOptionHolding as DomainEntity
from src.infrastructure.models.finance.holding.portfolio_company_share_option_holding import CompanyShareOptionPortfolioHoldingModel as ORMModel


class PortfolioCompanyShareOptionHoldingMapper:
    """Mapper for PortfolioCompanyShareOptionHolding domain entity and ORM model."""

    @property
    def discriminator(self):
        return "portfolio_company_share_option_holding"

    @property
    def model_class(self):
        return ORMModel

    def get_entity(self):
        return DomainEntity

    def to_domain(self, orm_model: Optional[ORMModel]) -> Optional[DomainEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None

        # Note: This is a simplified mapping - in practice you'd need to 
        # resolve the asset, portfolio, and position relationships
        return DomainEntity(
            id=orm_model.id,
            asset=None,  # Would need to resolve CompanyShareOption
            portfolio=None,  # Would need to resolve PortfolioCompanyShareOption
            position=None,  # Would need to resolve Position
            start_date=orm_model.start_date,
            end_date=orm_model.end_date,
        )

    def to_orm(self, entity: DomainEntity) -> ORMModel:
        """Convert domain entity to ORM model."""
        return ORMModel(
            id=entity.id,
            portfolio_company_share_option_id=entity.portfolio.id if entity.portfolio else None,
            company_share_option_id=entity.asset.id if entity.asset else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )