# Symbol Local Repository
# Mirrors src/infrastructure/models/finance/back_testing/financial_assets/symbol.py

class SymbolLocalRepository:
    """Local repository for symbol model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, symbol):
        """Save symbol to local storage"""
        self.data_store.append(symbol)
        
    def find_by_id(self, symbol_id):
        """Find symbol by ID"""
        for symbol in self.data_store:
            if getattr(symbol, 'id', None) == symbol_id:
                return symbol
        return None
        
    def find_all(self):
        """Find all symbols"""
        return self.data_store.copy()