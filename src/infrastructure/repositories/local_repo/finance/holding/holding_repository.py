"""
Repository for holding entities
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.infrastructure.models.finance.holding.holding import (
    Holding
)
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding

from src.infrastructure.repositories.mappers.finance.holding.holding_mapper import HoldingMapper
from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
from src.domain.ports.finance.holding.holding_port import HoldingPort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository


class HoldingRepository(BaseLocalRepository, HoldingPort):
    """Repository for holding entities with basic CRUD operations"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = HoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[Holding]:
        """Get a holding by ID"""
        model = self.session.query(Holding).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_all(self) -> List[Holding]:
        """Get all holdings"""
        models = self.session.query(Holding).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_container_id(self, container_id: int) -> List[Holding]:
        """Get all holdings for a specific container"""
        models = self.session.query(Holding).filter_by(container_id=container_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_active_holdings(self, container_id: int = None) -> List[Holding]:
        """Get active holdings (no end_date or end_date in future)"""
        query = self.session.query(Holding).filter(
            (Holding.end_date.is_(None)) | (Holding.end_date > datetime.now())
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
        model = self.session.query(Holding).filter_by(id=holding_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False





