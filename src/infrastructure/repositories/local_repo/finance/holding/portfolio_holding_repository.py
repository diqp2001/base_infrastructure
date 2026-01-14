from decimal import Decimal
from domain.ports.finance.holding.portfolio_holding_port import PortfolioHoldingPort
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.holding.holding_mapper import HoldingMapper
from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldings
from src.infrastructure.repositories.mappers.finance.holding.portfolio_holding_mapper import PortfolioHoldingMapper
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldings
class PortfolioHoldingRepository(BaseLocalRepository, PortfolioHoldingPort):
    """Repository for portfolio holding entities"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = PortfolioHoldingMapper()
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for PortfolioHoldings."""
        return PortfolioHoldings
    
    def _to_entity(self, model: PortfolioHoldings) -> dict:
        """Convert infrastructure model to entity-like dict."""
        if not model:
            return None
        
        return {
            'id': model.id,
            'portfolio_id': model.portfolio_id,
            'cash_balance': Decimal(str(model.cash_balance)) if model.cash_balance else Decimal('0'),
            'total_value': Decimal(str(model.total_value)) if model.total_value else Decimal('0'),
            'holdings_value': Decimal(str(model.holdings_value)) if model.holdings_value else Decimal('0'),
            'holdings_data': model.holdings_data or {},
            'created_at': model.created_at,
            'updated_at': model.updated_at
        }
    
    def _to_model(self, entity_data: dict) -> PortfolioHoldings:
        """Convert entity-like dict to infrastructure model."""
        if not entity_data:
            return None
        
        return PortfolioHoldings(
            portfolio_id=entity_data.get('portfolio_id'),
            cash_balance=float(entity_data.get('cash_balance', 0)),
            total_value=float(entity_data.get('total_value', 0)),
            holdings_value=float(entity_data.get('holdings_value', 0)),
            holdings_data=entity_data.get('holdings_data', {}),
            created_at=entity_data.get('created_at', datetime.now()),
            updated_at=entity_data.get('updated_at', datetime.now())
        )
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