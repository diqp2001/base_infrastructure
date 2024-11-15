# src/domain/entities/exchange.py
from typing import List

class Exchange:
    def __init__(self, name: str, location: str, assets: List[str]):
        """
        Initialize an Exchange object with its name, location, and the assets it trades.
        
        :param name: Name of the exchange (e.g., 'NYSE', 'NASDAQ')
        :param location: Location of the exchange (e.g., 'New York', 'London')
        :param assets: A list of asset tickers traded on the exchange (e.g., ['AAPL', 'GOOGL'])
        """
        self.name = name
        self.location = location
        self.assets = assets  # List of asset tickers

    def add_asset(self, ticker: str):
        """
        Add a new asset to the exchange's list of traded assets.
        
        :param ticker: The ticker of the asset to add
        """
        if ticker not in self.assets:
            self.assets.append(ticker)
        else:
            print(f"Asset {ticker} is already traded on {self.name}.")

    def remove_asset(self, ticker: str):
        """
        Remove an asset from the exchange's list of traded assets.
        
        :param ticker: The ticker of the asset to remove
        """
        if ticker in self.assets:
            self.assets.remove(ticker)
        else:
            print(f"Asset {ticker} not found on {self.name}.")

    def list_assets(self):
        """
        List all the assets traded on the exchange.
        """
        return self.assets

    def __repr__(self):
        return f"Exchange({self.name}, {self.location}, {len(self.assets)} assets)"
