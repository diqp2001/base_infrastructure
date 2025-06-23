# src/domain/entities/exchange.py
from typing import List

class Exchange:
    def __init__(self, id:int, name: str, country_id: int):
        """
        Initialize an Exchange object with its name, location, and the assets it trades.
        
        :param name: Name of the exchange (e.g., 'NYSE', 'NASDAQ')
        :param location: Location of the exchange (e.g., 'New York', 'London')
        :param assets: A list of asset tickers traded on the exchange (e.g., ['AAPL', 'GOOGL'])
        """
        self.id = id
        self.name = name
        self.country_id = country_id

    

    def __repr__(self):
        return f"Exchange({self.name})"
