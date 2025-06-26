class Security:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.price = 0.0
        self.holdings = 0

class Portfolio:
    def __init__(self):
        self.securities = {}

    def is_invested(self, symbol: str) -> bool:
        return self.securities.get(symbol, Security(symbol)).holdings > 0

    def process_orders(self):
        print("Processing orders...")

    def __getitem__(self, symbol: str):
        return self.securities.setdefault(symbol, Security(symbol))
