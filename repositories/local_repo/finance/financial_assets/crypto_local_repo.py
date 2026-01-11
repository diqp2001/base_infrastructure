# Crypto Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/crypto.py

class CryptoLocalRepository:
    """Local repository for crypto model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, crypto):
        """Save crypto to local storage"""
        self.data_store.append(crypto)
        
    def find_by_id(self, crypto_id):
        """Find crypto by ID"""
        for crypto in self.data_store:
            if getattr(crypto, 'id', None) == crypto_id:
                return crypto
        return None
        
    def find_all(self):
        """Find all cryptos"""
        return self.data_store.copy()