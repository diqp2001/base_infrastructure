# src/domain/entities/financial_assets/ETF.py
from .derivative import Derivative

class ETF(Derivative):
    def __init__(self, ticker: str, name: str, market: str, price: float, expense_ratio: float):
        super().__init__(ticker, name, market, price)
        self.expense_ratio = expense_ratio  # Expense ratio for the ETF

    def __repr__(self):
        return f"ETF({self.ticker}, {self.name}, {self.price}, {self.expense_ratio})"