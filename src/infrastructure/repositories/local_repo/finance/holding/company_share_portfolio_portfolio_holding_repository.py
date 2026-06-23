from typing import Optional

from sqlalchemy.orm import Session

from src.domain.entities.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHolding
from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import CompanySharePortfolioPortfolioHoldingModel
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.holding.company_share_portfolio_portfolio_holding_mapper import CompanySharePortfolioPortfolioHoldingMapper


class CompanySharePortfolioPortfolioHoldingRepository(BaseLocalRepository):
    """Repository for CompanySharePortfolioPortfolioHolding: a Portfolio holds a CompanySharePortfolio."""

    def __init__(self, session: Session, factory=None, mapper: CompanySharePortfolioPortfolioHoldingMapper = None):
        self.session = session
        self.factory = factory
        self.mapper = mapper or CompanySharePortfolioPortfolioHoldingMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class

    def get_by_id(self, holding_id: int) -> Optional[CompanySharePortfolioPortfolioHolding]:
        model = self.session.query(CompanySharePortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def save(self, holding: CompanySharePortfolioPortfolioHolding) -> CompanySharePortfolioPortfolioHolding:
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)
