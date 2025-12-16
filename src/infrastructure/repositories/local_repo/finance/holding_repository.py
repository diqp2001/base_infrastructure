"""
Repository for holding entities
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.infrastructure.models.finance.holding import (
    HoldingModel, 
    PortfolioHoldingModel, 
    PortfolioCompanyShareHoldingModel
)
from src.infrastructure.repositories.mappers.finance.holding_mapper import HoldingMapper
from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding


class HoldingRepository:
    """Repository for holding entities with basic CRUD operations"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = HoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[Holding]:
        """Get a holding by ID"""
        model = self.session.query(HoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_all(self) -> List[Holding]:
        """Get all holdings"""
        models = self.session.query(HoldingModel).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_container_id(self, container_id: int) -> List[Holding]:
        """Get all holdings for a specific container"""
        models = self.session.query(HoldingModel).filter_by(container_id=container_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_active_holdings(self, container_id: int = None) -> List[Holding]:
        """Get active holdings (no end_date or end_date in future)"""
        query = self.session.query(HoldingModel).filter(
            (HoldingModel.end_date.is_(None)) | (HoldingModel.end_date > datetime.now())
        )
        if container_id:
            query = query.filter_by(container_id=container_id)
        
        models = query.all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, holding: Holding) -> Holding:
        """Save or update a holding"""
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)

    def delete(self, holding_id: int) -> bool:
        """Delete a holding by ID"""
        model = self.session.query(HoldingModel).filter_by(id=holding_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False


class PortfolioHoldingRepository:
    """Repository for portfolio holding entities"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = HoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[PortfolioHolding]:
        """Get a portfolio holding by ID"""
        model = self.session.query(PortfolioHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.portfolio_holding_to_entity(model) if model else None

    def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioHolding]:
        """Get all holdings for a specific portfolio"""
        models = self.session.query(PortfolioHoldingModel).filter_by(portfolio_id=portfolio_id).all()
        return [self.mapper.portfolio_holding_to_entity(model) for model in models]

    def save(self, holding: PortfolioHolding) -> PortfolioHolding:
        """Save or update a portfolio holding"""
        model = self.mapper.portfolio_holding_to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.portfolio_holding_to_entity(model)


class PortfolioCompanyShareHoldingRepository:
    """Repository for portfolio company share holding entities"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = HoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[PortfolioCompanyShareHolding]:
        """Get a portfolio company share holding by ID"""
        model = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.portfolio_company_share_holding_to_entity(model) if model else None

    def get_by_portfolio_company_share_id(self, portfolio_id: int) -> List[PortfolioCompanyShareHolding]:
        """Get all company share holdings for a specific portfolio company share"""
        models = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(
            portfolio_company_share_id=portfolio_id
        ).all()
        return [self.mapper.portfolio_company_share_holding_to_entity(model) for model in models]

    def save(self, holding: PortfolioCompanyShareHolding) -> PortfolioCompanyShareHolding:
        """Save or update a portfolio company share holding"""
        model = self.mapper.portfolio_company_share_holding_to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.portfolio_company_share_holding_to_entity(model)