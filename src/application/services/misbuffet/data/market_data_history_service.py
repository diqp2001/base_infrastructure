
from typing import  Optional
from src.application.services.misbuffet.data.frontier import Frontier


class MarketDataHistoryService:
    """
    Provides historical market data with frontier enforcement to prevent look-ahead bias.
    This service ensures that algorithms can only access historical data up to the current
    simulation time, maintaining the integrity of backtesting.
    """

    def __init__(self, market_data_service):
        self.market_data_service = market_data_service
        self._frontier: Optional[Frontier] = None

       
   
    @property
    def frontier(self) -> Optional[Frontier]:
        """Get the frontier object."""
        return self._frontier