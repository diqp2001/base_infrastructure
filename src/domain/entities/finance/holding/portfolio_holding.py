


from datetime import datetime
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from src.domain.entities.finance.portfolio.portfolio import Portfolio
from src.domain.entities.finance.holding.holding import Holding


class PortfolioHolding(Holding):
    """Base class for holdings inside a portfolio."""
    def __init__(
        self,
        id: int,
        portfolio: Portfolio,
        asset: FinancialAsset,
        start_date: datetime,
        end_date: datetime,
    ):
        super().__init__(
            id=id,
            asset=asset,
            container=portfolio,
            start_date=start_date,
            end_date=end_date
        )
    