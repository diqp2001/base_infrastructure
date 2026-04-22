"""
Mapper for PortfolioDerivative domain entity and ORM model.
Converts between domain entities and ORM models to avoid metaclass conflicts.
"""

from typing import Optional

from src.domain.entities.finance.portfolio.portfolio_derivative import PortfolioDerivative as DomainPortfolioDerivative
from src.infrastructure.models.finance.portfolio.portfolio_derivative import PortfolioDerivativeModel as ORMPortfolioDerivative


class PortfolioDerivativeMapper:
    """Mapper for PortfolioDerivative domain entity and ORM model."""

    @property
    def discriminator(self):
        return "portfolio_derivative"

    @property
    def model_class(self):
        return ORMPortfolioDerivative

    def get_entity(self):
        return DomainPortfolioDerivative

    def to_domain(self, orm_model: Optional[ORMPortfolioDerivative]) -> Optional[DomainPortfolioDerivative]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None

        return DomainPortfolioDerivative(
            id=orm_model.id,
            name=orm_model.name,
            start_date=orm_model.start_date,
            end_date=orm_model.end_date,
        )

    def to_orm(self, entity: DomainPortfolioDerivative) -> ORMPortfolioDerivative:
        """Convert domain entity to ORM model."""
        return ORMPortfolioDerivative(
            id=entity.id,
            name=entity.name,
            start_date=entity.start_date,
            end_date=entity.end_date,
        )