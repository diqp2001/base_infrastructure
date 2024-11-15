class FinancialAsset:
    def __init__(self, name, ticker, value, date):
        self.name = name
        self.ticker = ticker
        self.value = value
        self.date = date

    @property
    def asset_type(self):
        raise NotImplementedError("This method should be implemented by subclass.")
    
    def __repr__(self):
        return f"<{self.asset_type}({self.name}, {self.ticker}, {self.value}, {self.date})>"