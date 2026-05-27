from typing import Optional
from .financial_statement import FinancialStatement


class IncomeStatement(FinancialStatement):
    """Represents an income statement."""

    def __init__(self, id: Optional[int] = None, company_id: int = None,
                 period: str = None, year: int = None,
                 revenue: float = 0.0, expenses: float = 0.0, net_income: float = 0.0):
        super().__init__(id=id, company_id=company_id, period=period, year=year)
        self.revenue = revenue
        self.expenses = expenses
        self.net_income = net_income
