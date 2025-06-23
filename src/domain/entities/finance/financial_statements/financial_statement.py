# domain/entities/financial_statements/financial_statement.py

class FinancialStatement:
    """
    Base class for financial statements.
    """

    def __init__(self, company_id: int, period: str, year: int):
        """
        Initialize a financial statement.

        :param company_id: ID of the company associated with the financial statement.
        :param period: Reporting period (e.g., "Q1", "Q2", "Q3", "Q4", "Annual").
        :param year: Year of the financial statement.
        """
        self.company_id = company_id
        self.period = period
        self.year = year
