# src/domain/entities/financial_assets/commodity.py
from .financial_asset import FinancialAsset

class Commodity(FinancialAsset):
    def __init__(self, ticker: str, name: str, market: str, price: float):
        super().__init__(ticker, name, market)
        self.price = price  # Price of the commodity (e.g., per unit)

    def __repr__(self):
        return f"Commodity({self.ticker}, {self.name}, {self.price})"
        