# domain/entities/financial_statements/balance_sheet.py

from .financial_statement import FinancialStatement

class BalanceSheet(FinancialStatement):
    """
    Represents a balance sheet.
    """

    def __init__(self, company_id: int, period: str, year: int, assets: float, liabilities: float, equity: float):
        super().__init__(company_id, period, year)
        self.assets = assets
        self.liabilities = liabilities
        self.equity = equity
