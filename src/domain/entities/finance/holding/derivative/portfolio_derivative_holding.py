from __future__ import annotations
from datetime import datetime
from typing import Optional

from domain.entities.finance.financial_assets.derivatives.derivative import Derivative
from domain.entities.finance.holding.position import Position
from domain.entities.finance.portfolio.portfolio_derivative import PortfolioDerivative
from src.domain.entities.finance.holding.portfolio_holding import PortfolioHolding



class PortfolioDerivativeHolding(PortfolioHolding):
    """
    Derivative held inside a PortfolioDerivativeHolding.
    """

    def __init__(
        self,
        id: int,
        asset: Derivative,
        portfolio: PortfolioDerivative,
        position: Position,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ):
        super().__init__(
            id=id,
            asset=asset,
            container=portfolio,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )

