from datetime import datetime
from typing import Callable, List, Optional
from src.application.services.misbuffet.common.data_types import Slice
from src.application.services.data.entities.entity_service import EntityService


class MarketDataService:
    """
    Main market data service that provides data slices to the trading engine.
    Supports both real-time and backtest scenarios through different providers.
    """

    def __init__(self, entity_service: EntityService):
        self.entity_service = entity_service
        

        # Event callbacks
        self.on_data_slice: Optional[Callable[[Slice], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
