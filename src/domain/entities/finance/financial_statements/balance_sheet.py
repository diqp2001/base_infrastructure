from typing import Optional
from .financial_statement import FinancialStatement


class BalanceSheet(FinancialStatement):
    """Represents a balance sheet."""

    def __init__(self, id: Optional[int] = None, company_id: int = None,
                 period: str = None, year: int = None,
                 assets: float = 0.0, liabilities: float = 0.0, equity: float = 0.0):
        super().__init__(id=id, company_id=company_id, period=period, year=year)
        self.assets = assets
        self.liabilities = liabilities
        self.equity = equity
