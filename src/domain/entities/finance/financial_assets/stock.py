from .financial_asset import FinancialAsset

"""Represents a core business concept, typically with behavior and attributes."""
class Stock(FinancialAsset):
    def __init__(self, id, ticker, exchange_id, start_date, end_date):
        super().__init__(id, start_date, end_date)
        
        self.ticker = ticker
        self.exchange_id = exchange_id
        

    def calculate_dividend(self):
        # Implement logic to calculate dividend for a stock
        pass
  