from .financial_asset import FinancialAsset

"""Represents a core business concept, typically with behavior and attributes."""
class Stock(FinancialAsset):
    def __init__(self, name, ticker, value, date, company_id):
        super().__init__(name, ticker, value, date)
        self.company_id = company_id

    def calculate_dividend(self):
        # Implement logic to calculate dividend for a stock
        pass
    def calculate_market_value(self):
        return self.value #* self.volume