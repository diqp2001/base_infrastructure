"""
Mapper for PortfolioCompanyShareOption domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional
from datetime import datetime

from src.domain.entities.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOption as DomainPortfolioCompanyShareOption
from src.infrastructure.models.finance.portfolio.portfolio_company_share_option import PortfolioCompanyShareOptionModel as ORMPortfolioCompanyShareOption


class PortfolioCompanyShareOptionMapper:
    """Mapper for PortfolioCompanyShareOption domain entity and ORM model."""

    @property
    def discriminator(self):
        return "portfolio_company_share_option"

    @property
    def model_class(self):
        return ORMPortfolioCompanyShareOption

    def get_entity(self):
        return DomainPortfolioCompanyShareOption

    def to_domain(self, orm_model: Optional[ORMPortfolioCompanyShareOption]) -> Optional[DomainPortfolioCompanyShareOption]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None

        return DomainPortfolioCompanyShareOption(
            id=orm_model.id,
            name=orm_model.name,
            start_date=orm_model.start_date if hasattr(orm_model, 'start_date') else None,
            end_date=orm_model.end_date if hasattr(orm_model, 'end_date') else None,
        )

    def to_orm(self, entity: DomainPortfolioCompanyShareOption) -> ORMPortfolioCompanyShareOption:
        """Convert domain entity to ORM model."""
        return ORMPortfolioCompanyShareOption(
            id=entity.id,
            name=entity.name,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )