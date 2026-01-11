# Market Data Local Repository
# Mirrors src/infrastructure/models/finance/market_data.py

class MarketDataLocalRepository:
    """Local repository for market data model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, market_data):
        """Save market data to local storage"""
        self.data_store.append(market_data)
        
    def find_by_id(self, market_data_id):
        """Find market data by ID"""
        for market_data in self.data_store:
            if getattr(market_data, 'id', None) == market_data_id:
                return market_data
        return None
        
    def find_all(self):
        """Find all market data"""
        return self.data_store.copy()