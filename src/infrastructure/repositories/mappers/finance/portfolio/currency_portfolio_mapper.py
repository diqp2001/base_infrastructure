from typing import Optional

from src.domain.entities.finance.portfolio.currency_portfolio import CurrencyPortfolio as DomainCurrencyPortfolio
from src.infrastructure.models.finance.portfolio.currency_portfolio import CurrencyPortfolioModel as ORMCurrencyPortfolio


class CurrencyPortfolioMapper:
    """Mapper for CurrencyPortfolio domain entity ↔ ORM model."""

    @property
    def discriminator(self):
        return "CurrencyPortfolio"

    @property
    def entity_class(self):
        return DomainCurrencyPortfolio

    @property
    def model_class(self):
        return ORMCurrencyPortfolio

    def to_domain(self, orm_obj: ORMCurrencyPortfolio) -> DomainCurrencyPortfolio:
        return self.entity_class(
            id=orm_obj.id,
            name=orm_obj.name,
            start_date=getattr(orm_obj, 'start_date', None),
            end_date=getattr(orm_obj, 'end_date', None),
        )

    def to_orm(
        self,
        domain_obj: DomainCurrencyPortfolio,
        orm_obj: Optional[ORMCurrencyPortfolio] = None,
    ) -> ORMCurrencyPortfolio:
        if orm_obj is None:
            orm_obj = self.model_class(
                name=domain_obj.name,
                start_date=getattr(domain_obj, 'start_date', None),
                end_date=getattr(domain_obj, 'end_date', None),
            )
        return orm_obj
