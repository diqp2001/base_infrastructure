from .financial_asset import FinancialAsset

class Bond(FinancialAsset):
    def __init__(self, name, ticker, value, date, company_id):
        super().__init__(name, ticker, value, date)
        self.company_id = company_id

    def calculate_interest(self):
        pass