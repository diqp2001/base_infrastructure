from .financial_asset import FinancialAsset

class Stock(FinancialAsset):
    def __init__(self, name, ticker, value, date, company_id):
        super().__init__(name, ticker, value, date)
        self.company_id = company_id

    def calculate_dividend(self):
        # Implement logic to calculate dividend for a stock
        pass