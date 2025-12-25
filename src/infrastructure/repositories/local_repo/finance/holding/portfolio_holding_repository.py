from src.infrastructure.repositories.mappers.finance.holding.holding_mapper import HoldingMapper
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldings
from src.infrastructure.repositories.mappers.finance.holding.portfolio_holding_mapper import PortfolioHoldingMapper
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
class PortfolioHoldingRepository:
    """Repository for portfolio holding entities"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = PortfolioHoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[PortfolioHoldings]:
        """Get a portfolio holding by ID"""
        model = self.session.query(PortfolioHoldings).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioHoldings]:
        """Get all holdings for a specific portfolio"""
        models = self.session.query(PortfolioHoldings).filter_by(portfolio_id=portfolio_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, holding: PortfolioHoldings) -> PortfolioHoldings:
        """Save or update a portfolio holding"""
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)