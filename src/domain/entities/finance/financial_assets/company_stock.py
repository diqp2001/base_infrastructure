
from .stock import Stock

class CompanyStock(Stock):
    def __init__(self, id, ticker, exchange_id, company_id,  start_date, end_date):
        super().__init__( id,ticker, exchange_id,  start_date, end_date)
        
        self.company_id = company_id

    def __repr__(self):
        return f"CompanyStock({self.ticker})"