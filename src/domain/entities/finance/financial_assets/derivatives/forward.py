# src/domain/entities/financial_assets/forward.py
from .derivative import Derivative

class Forward(Derivative):
    def __init__(self, ticker: str, name: str, market: str, price: float, settlement_date: str):
        super().__init__(ticker, name, market)
        self.price = price
        self.settlement_date = settlement_date  # Settlement date for the forward contract

    def __repr__(self):
        return f"Forward({self.ticker}, {self.name}, {self.price}, {self.settlement_date})"
