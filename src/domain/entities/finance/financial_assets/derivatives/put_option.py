from .derivative import Option

class PutOption(Option):
    def __init__(self, ticker: str, name: str, market: str, price: float, expiration_date: str, strike_price: float):
        super().__init__(ticker, name, market, price, expiration_date, strike_price, option_type='put')

    def __repr__(self):
        return f"PutOption({self.ticker}, {self.name}, {self.price}, {self.expiration_date}, {self.strike_price})"
