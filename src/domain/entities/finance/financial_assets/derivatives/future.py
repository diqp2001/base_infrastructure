# src/domain/entities/financial_assets/future.py
from .derivative import Derivative

class Future(Derivative):
    def __init__(self, ticker: str, name: str, market: str, price: float, expiration_date: str):
        super().__init__(ticker, name, market)
        self.price = price
        self.expiration_date = expiration_date  # Expiration date for the future contract

    def __repr__(self):
        return f"Future({self.ticker}, {self.name}, {self.price}, {self.expiration_date})"
