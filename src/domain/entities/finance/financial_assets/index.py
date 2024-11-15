# src/domain/entities/financial_assets/index.py
from .financial_asset import FinancialAsset

class Index(FinancialAsset):
    def __init__(self, ticker: str, name: str, market: str, level: float):
        super().__init__(ticker, name, market)
        self.level = level  # Index level (e.g., S&P 500)

    def __repr__(self):
        return f"Index({self.ticker}, {self.name}, {self.level})"