from typing import Optional, List

from sqlalchemy.orm import Session

from src.domain.entities.finance.holding.etf_share_option_portfolio_portfolio_holding import (
    ETFShareOptionPortfolioPortfolioHolding,
)
from src.infrastructure.models.finance.holding.etf_share_option_portfolio_portfolio_holding import (
    ETFShareOptionPortfolioPortfolioHoldingModel,
)
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.holding.etf_share_option_portfolio_portfolio_holding_mapper import (
    ETFShareOptionPortfolioPortfolioHoldingMapper,
)


class ETFShareOptionPortfolioPortfolioHoldingRepository(BaseLocalRepository):
    """Repository for ETFShareOptionPortfolioPortfolioHolding: a Portfolio holds a ETFShareOptionPortfolio."""

    def __init__(self, session: Session, factory=None, mapper=None):
        self.session = session
        self.factory = factory
        self.mapper = mapper or ETFShareOptionPortfolioPortfolioHoldingMapper()

    @property
    def entity_class(self):
        return self.mapper.entity_class

    def get_by_id(self, holding_id: int) -> Optional[ETFShareOptionPortfolioPortfolioHolding]:
        model = self.session.query(ETFShareOptionPortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_by_portfolio_id(self, portfolio_id: int) -> List[ETFShareOptionPortfolioPortfolioHolding]:
        """Return all holdings where this portfolio is the container."""
        models = self.session.query(ETFShareOptionPortfolioPortfolioHoldingModel).filter_by(
            etf_share_option_portfolio_portfolio_id=portfolio_id
        ).all()
        return [self.mapper.to_entity(m) for m in models]

    def get_by_container_and_asset(self, container_id: int, asset_id: int) -> Optional[ETFShareOptionPortfolioPortfolioHolding]:
        """Return the holding for a specific (main portfolio, option sub-portfolio) pair."""
        model = (
            self.session.query(ETFShareOptionPortfolioPortfolioHoldingModel)
            .filter_by(container_id=container_id, asset_id=asset_id)
            .first()
        )
        return self.mapper.to_entity(model) if model else None

    def get_related_entities(self, holding_id: int):
        """Return the ETFShareOptionPortfolio that this holding points to."""
        from src.infrastructure.models.finance.portfolio.etf_share_option_portfolio import (
            ETFShareOptionPortfolioModel,
        )
        model = self.session.query(ETFShareOptionPortfolioPortfolioHoldingModel).filter_by(id=holding_id).first()
        if model is None:
            return []
        sub_portfolio = self.session.query(ETFShareOptionPortfolioModel).filter_by(id=model.asset_id).first()
        return [sub_portfolio] if sub_portfolio else []

    def save(self, holding: ETFShareOptionPortfolioPortfolioHolding) -> ETFShareOptionPortfolioPortfolioHolding:
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)
