from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.finance.holding.currency_portfolio_holding import CurrencyPortfolioHolding
from src.domain.ports.finance.holding.currency_portfolio_holding_port import CurrencyPortfolioHoldingPort
from src.infrastructure.models.finance.holding.currency_portfolio_holding import CurrencyPortfolioHoldingModel
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.holding.currency_portfolio_holding_mapper import CurrencyPortfolioHoldingMapper


class CurrencyPortfolioHoldingRepository(BaseLocalRepository, CurrencyPortfolioHoldingPort):
    """Repository for CurrencyPortfolioHolding entities."""

    def __init__(self, session: Session, factory=None, mapper: CurrencyPortfolioHoldingMapper = None):
        self.session = session
        self.factory = factory
        self.mapper = mapper or CurrencyPortfolioHoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[CurrencyPortfolioHolding]:
        model = self.session.query(CurrencyPortfolioHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_currency_portfolio_id(self, portfolio_id: int) -> List[CurrencyPortfolioHolding]:
        models = self.session.query(CurrencyPortfolioHoldingModel).filter_by(
            currency_portfolio_id=portfolio_id
        ).all()
        return [self.mapper.to_entity(m) for m in models]

    def save(self, holding: CurrencyPortfolioHolding) -> CurrencyPortfolioHolding:
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)
