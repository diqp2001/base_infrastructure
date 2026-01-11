# Currency Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/currency.py

class CurrencyLocalRepository:
    """Local repository for currency model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, currency):
        """Save currency to local storage"""
        self.data_store.append(currency)
        
    def find_by_id(self, currency_id):
        """Find currency by ID"""
        for currency in self.data_store:
            if getattr(currency, 'id', None) == currency_id:
                return currency
        return None
        
    def find_all(self):
        """Find all currencies"""
        return self.data_store.copy()