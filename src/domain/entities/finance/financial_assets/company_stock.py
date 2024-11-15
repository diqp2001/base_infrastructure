# src/domain/entities/financial_assets/ETF.py
from .stock import Stock

class CompanyStock(Stock):
    def __init__(self, ticker: str, name: str, market: str, price: float, expense_ratio: float):
        super().__init__(ticker, name, market, price)

    def __repr__(self):
        return f"Stock({self.ticker}, {self.name}, {self.price}, {self.expense_ratio})"