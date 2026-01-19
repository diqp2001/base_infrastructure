from datetime import date
from typing import Optional

from domain.entities.finance.financial_assets.share.share import Share


class CompanyShare(Share):
    ASSET_TYPE = "company_share"

    def __init__(
        self,
        id: Optional[int],
        symbol: str,
        company_id: int,
        exchange_id: int,
        name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        super().__init__(
            id=id,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

        self._symbol = symbol
        self._company_id = company_id
        self._exchange_id = exchange_id

    # -------- Polymorphic identity --------
    @property
    def asset_type(self) -> str:
        return self.ASSET_TYPE

    # -------- Asset-specific attributes --------
    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def company_id(self) -> int:
        return self._company_id

    @property
    def exchange_id(self) -> int:
        return self._exchange_id

    def __repr__(self) -> str:
        return (
            f"<CompanyShare(id={self.id}, symbol={self.symbol}, "
            f"exchange_id={self.exchange_id}, company_id={self.company_id})>"
        )
