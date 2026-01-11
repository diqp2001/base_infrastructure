# Exchange Local Repository
# Mirrors src/infrastructure/models/finance/exchange.py

class ExchangeLocalRepository:
    """Local repository for exchange model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, exchange):
        """Save exchange to local storage"""
        self.data_store.append(exchange)
        
    def find_by_id(self, exchange_id):
        """Find exchange by ID"""
        for exchange in self.data_store:
            if getattr(exchange, 'id', None) == exchange_id:
                return exchange
        return None
        
    def find_all(self):
        """Find all exchanges"""
        return self.data_store.copy()