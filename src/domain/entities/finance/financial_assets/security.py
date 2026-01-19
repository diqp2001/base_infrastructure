from datetime import date
from typing import Optional
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset


class Security(FinancialAsset):
    """
    Base class for all tradeable securities following QuantConnect architecture.
    """

    ASSET_TYPE = "security"
    
    def __init__(
        self,
        id: Optional[int],
        name: Optional[str],
        
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbol: Optional[str] = None,
        portfolio_id: Optional[int] = None,
    ):
        super().__init__(
            id, name, symbol, start_date, end_date
        )

        self._portfolio_id = portfolio_id

    # -------- Polymorphic identity --------
    @property
    def asset_type(self) -> str:
        return self.ASSET_TYPE

    # -------- Security-specific attributes --------
    @property
    def symbol(self) -> Optional[str]:
        return self._symbol

    @property
    def portfolio_id(self) -> Optional[int]:
        return self._portfolio_id

    def __repr__(self):
        return f"<Security(id={self.id}, symbol={self.symbol})>"
