from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.finance.portfolio.currency_portfolio import CurrencyPortfolio
from src.domain.ports.finance.portfolio.currency_portfolio_port import CurrencyPortfolioPort
from src.infrastructure.models.finance.portfolio.currency_portfolio import CurrencyPortfolioModel
from src.infrastructure.repositories.mappers.finance.portfolio.currency_portfolio_mapper import CurrencyPortfolioMapper


class CurrencyPortfolioRepository(CurrencyPortfolioPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = CurrencyPortfolioMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class

    @property
    def model_class(self):
        return self.mapper.model_class

    def _create_or_get(self, name: str, **kwargs) -> Optional[CurrencyPortfolio]:
        try:
            existing = self.get_by_name(name)
            if existing:
                return existing

            entity = self.entity_class(
                id=None,
                name=name,
                start_date=kwargs.get("start_date", datetime.now()),
                end_date=kwargs.get("end_date"),
            )
            orm_obj = self.mapper.to_orm(entity)
            self.session.add(orm_obj)
            self.session.commit()
            return self.mapper.to_domain(orm_obj)

        except Exception as e:
            print(f"Error creating CurrencyPortfolio '{name}': {e}")
            return None

    def get_by_name(self, name: str) -> Optional[CurrencyPortfolio]:
        model = self.session.query(CurrencyPortfolioModel).filter(
            CurrencyPortfolioModel.name == name
        ).first()
        return self.mapper.to_domain(model) if model else None

    def get_by_id(self, id: int) -> Optional[CurrencyPortfolio]:
        obj = self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        return self.mapper.to_domain(obj) if obj else None

    def get_all(self) -> List[CurrencyPortfolio]:
        return [self.mapper.to_domain(o) for o in self.session.query(self.model_class).all()]

    def add(self, entity: CurrencyPortfolio) -> Optional[CurrencyPortfolio]:
        obj = self.mapper.to_orm(entity)
        self.session.add(obj)
        self.session.commit()
        return self.mapper.to_domain(obj)

    def update(self, entity: CurrencyPortfolio) -> Optional[CurrencyPortfolio]:
        obj = self.session.query(self.model_class).filter(self.model_class.id == entity.id).one_or_none()
        if not obj:
            return None
        obj.name = entity.name
        obj.start_date = entity.start_date
        obj.end_date = entity.end_date
        self.session.commit()
        return self.mapper.to_domain(obj)

    def delete(self, id: int) -> bool:
        obj = self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()
        if not obj:
            return False
        self.session.delete(obj)
        self.session.commit()
        return True

    def get_related_entities(self, portfolio_id: int) -> List:
        """Return all CurrencyPortfolioHoldings for this portfolio."""
        try:
            from src.infrastructure.repositories.local_repo.finance.holding.currency_portfolio_holding_repository import CurrencyPortfolioHoldingRepository
            return CurrencyPortfolioHoldingRepository(self.session, self.factory).get_by_currency_portfolio_id(portfolio_id)
        except Exception as e:
            print(f"Error retrieving holdings for CurrencyPortfolio {portfolio_id}: {e}")
            return []
