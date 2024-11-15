# src/domain/entities/financial_assets/option.py
from .derivative import Derivative

class Option(Derivative):
    def __init__(self, ticker: str, name: str, market: str, price: float, expiration_date: str, strike_price: float, option_type: str):
        super().__init__(ticker, name, market, price)
        self.expiration_date = expiration_date
        self.strike_price = strike_price  # Strike price for the option
        self.option_type = option_type  # 'call' or 'put' 

    def __repr__(self):
        return f"Option({self.ticker}, {self.name}, {self.price}, {self.expiration_date}, {self.strike_price}, {self.option_type})"
