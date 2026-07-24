from typing import Optional

from sqlalchemy.orm import Session

from src.domain.entities.finance.holding.currency_portfolio_portfolio_holding import CurrencyPortfolioPortfolioHolding
from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import CurrencyPortfolioPortfolioHoldingModel
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.holding.currency_portfolio_portfolio_holding_mapper import CurrencyPortfolioPortfolioHoldingMapper


class CurrencyPortfolioPortfolioHoldingRepository(BaseLocalRepository):
    """Repository for CurrencyPortfolioPortfolioHolding: a Portfolio holds a CurrencyPortfolio."""

    def __init__(self, session: Session, factory=None, mapper: CurrencyPortfolioPortfolioHoldingMapper = None):
        self.session = session
        self.factory = factory
        self.mapper = mapper or CurrencyPortfolioPortfolioHoldingMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class

    def get_by_id(self, holding_id: int) -> Optional[CurrencyPortfolioPortfolioHolding]:
        model = self.session.query(CurrencyPortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_portfolio_id(self, portfolio_id: int):
        """Return all holdings where this portfolio is the container."""
        models = self.session.query(CurrencyPortfolioPortfolioHoldingModel).filter_by(
            currency_portfolio_portfolio_id=portfolio_id
        ).all()
        return [self.mapper.to_entity(m) for m in models]

    def get_related_entities(self, holding_id: int):
        """Return the CurrencyPortfolio asset that this holding points to."""
        from src.infrastructure.models.finance.portfolio.currency_portfolio import CurrencyPortfolioModel
        model = self.session.query(CurrencyPortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        if model is None:
            return []
        currency_portfolio = self.session.query(CurrencyPortfolioModel).filter_by(
            id=model.currency_portfolio_id
        ).first()
        return [currency_portfolio] if currency_portfolio else []

    def save(self, holding: CurrencyPortfolioPortfolioHolding) -> CurrencyPortfolioPortfolioHolding:
        model = self.mapper.to_model(holding)
        model = self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)
