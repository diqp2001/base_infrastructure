from .financial_asset import FinancialAsset

"""Represents a core business concept, typically with behavior and attributes."""
class Stock(FinancialAsset):
    def __init__(self, id, ticker, company_id,  start_date, end_date):
        super().__init__( id,  start_date, end_date)
        self.company_id = company_id
        self.ticker = ticker
        

    def calculate_dividend(self):
        # Implement logic to calculate dividend for a stock
        pass
  