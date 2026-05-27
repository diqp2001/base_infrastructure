from typing import Optional
from .financial_statement import FinancialStatement


class CashFlowStatement(FinancialStatement):
    """Represents a cash flow statement."""

    def __init__(self, id: Optional[int] = None, company_id: int = None,
                 period: str = None, year: int = None,
                 operating_cash_flow: float = 0.0, investing_cash_flow: float = 0.0,
                 financing_cash_flow: float = 0.0):
        super().__init__(id=id, company_id=company_id, period=period, year=year)
        self.operating_cash_flow = operating_cash_flow
        self.investing_cash_flow = investing_cash_flow
        self.financing_cash_flow = financing_cash_flow
