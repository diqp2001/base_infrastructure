from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from domain.ports.finance.holding.portfolio_company_share_holding_port import PortfolioCompanyShareHoldingPort
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHoldingModel
from src.infrastructure.repositories.mappers.finance.holding.portfolio_company_share_holding_mapper import PortfolioCompanyShareHoldingMapper


class PortfolioCompanyShareHoldingRepository(BaseLocalRepository, PortfolioCompanyShareHoldingPort):
    """Repository for portfolio company share holding entities"""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = PortfolioCompanyShareHoldingMapper()

    def get_by_id(self, holding_id: int) -> Optional[PortfolioCompanyShareHoldingModel]:
        """Get a portfolio company share holding by ID"""
        model = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_portfolio_company_share_id(self, portfolio_id: int) -> List[PortfolioCompanyShareHoldingModel]:
        """Get all company share holdings for a specific portfolio company share"""
        models = self.session.query(PortfolioCompanyShareHoldingModel).filter_by(
            portfolio_company_share_id=portfolio_id
        ).all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, holding: PortfolioCompanyShareHoldingModel) -> PortfolioCompanyShareHoldingModel:
        """Save or update a portfolio company share holding"""
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)