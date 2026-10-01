from typing import Optional, List

from sqlalchemy.orm import Session

from src.domain.entities.finance.holding.company_share_option_portfolio_portfolio_holding import (
    CompanyShareOptionPortfolioPortfolioHolding,
)
from src.infrastructure.models.finance.holding.company_share_option_portfolio_portfolio_holding import (
    CompanyShareOptionPortfolioPortfolioHoldingModel,
)
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.holding.company_share_option_portfolio_portfolio_holding_mapper import (
    CompanyShareOptionPortfolioPortfolioHoldingMapper,
)


class CompanyShareOptionPortfolioPortfolioHoldingRepository(BaseLocalRepository):
    """Repository for CompanyShareOptionPortfolioPortfolioHolding: a Portfolio holds a CompanyShareOptionPortfolio."""

    def __init__(self, session: Session, factory=None, mapper=None):
        self.session = session
        self.factory = factory
        self.mapper = mapper or CompanyShareOptionPortfolioPortfolioHoldingMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class

    def get_by_id(self, holding_id: int) -> Optional[CompanyShareOptionPortfolioPortfolioHolding]:
        model = self.session.query(CompanyShareOptionPortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_portfolio_id(self, portfolio_id: int) -> List[CompanyShareOptionPortfolioPortfolioHolding]:
        """Return all holdings where this portfolio is the container."""
        models = self.session.query(CompanyShareOptionPortfolioPortfolioHoldingModel).filter_by(
            company_share_option_portfolio_portfolio_id=portfolio_id
        ).all()
        return [self.mapper.to_entity(m) for m in models]

    def get_by_container_and_asset(self, container_id: int, asset_id: int) -> Optional[CompanyShareOptionPortfolioPortfolioHolding]:
        """Return the holding for a specific (main portfolio, option sub-portfolio) pair."""
        model = (
            self.session.query(CompanyShareOptionPortfolioPortfolioHoldingModel)
            .filter_by(container_id=container_id, asset_id=asset_id)
            .first()
        )
        return self.mapper.to_entity(model) if model else None

    def get_related_entities(self, holding_id: int):
        """Return the CompanyShareOptionPortfolio that this holding points to."""
        from src.infrastructure.models.finance.portfolio.company_share_option_portfolio import (
            CompanyShareOptionPortfolioModel,
        )
        model = self.session.query(CompanyShareOptionPortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        if model is None:
            return []
        sub_portfolio = self.session.query(CompanyShareOptionPortfolioModel).filter_by(id=model.asset_id).first()
        return [sub_portfolio] if sub_portfolio else []

    def save(self, holding: CompanyShareOptionPortfolioPortfolioHolding) -> CompanyShareOptionPortfolioPortfolioHolding:
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)
