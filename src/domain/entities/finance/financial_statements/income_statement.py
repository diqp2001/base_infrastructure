# domain/entities/financial_statements/income_statement.py

from .financial_statement import FinancialStatement

class IncomeStatement(FinancialStatement):
    """
    Represents an income statement.
    """

    def __init__(self, company_id: int, period: str, year: int, revenue: float, expenses: float, net_income: float):
        super().__init__(company_id, period, year)
        self.revenue = revenue
        self.expenses = expenses
        self.net_income = net_income
