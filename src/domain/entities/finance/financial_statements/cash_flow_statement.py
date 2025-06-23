# domain/entities/financial_statements/cash_flow_statement.py

from .financial_statement import FinancialStatement

class CashFlowStatement(FinancialStatement):
    """
    Represents a cash flow statement.
    """

    def __init__(self, company_id: int, period: str, year: int, operating_cash_flow: float, investing_cash_flow: float, financing_cash_flow: float):
        super().__init__(company_id, period, year)
        self.operating_cash_flow = operating_cash_flow
        self.investing_cash_flow = investing_cash_flow
        self.financing_cash_flow = financing_cash_flow
