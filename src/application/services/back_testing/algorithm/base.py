class QCAlgorithm:
    def initialize(self):
        """User-defined initialization logic."""
        pass

    def on_data(self, data):
        """Handle incoming market data."""
        pass

    def add_equity(self, symbol: str):
        print(f"Equity {symbol} added")

    def set_holdings(self, symbol: str, fraction: float):
        print(f"Set holdings for {symbol} to {fraction}")

    @property
    def portfolio(self):
        return Portfolio()

    @property
    def now(self):
        from datetime import datetime
        return datetime.now()

    def log(self, message: str):
        print("[LOG]:", message)
