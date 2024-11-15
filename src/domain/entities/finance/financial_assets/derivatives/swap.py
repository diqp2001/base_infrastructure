# src/domain/entities/financial_assets/swap.py
from .derivative import Derivative

class Swap(Derivative):
    def __init__(self, ticker: str, name: str, market: str, notional: float, maturity_date: str):
        super().__init__(ticker, name, market)
        self.notional = notional  # Notional value of the swap
        self.maturity_date = maturity_date  # Maturity date for the swap contract

    def __repr__(self):
        return f"Swap({self.ticker}, {self.name}, {self.notional}, {self.maturity_date})"
