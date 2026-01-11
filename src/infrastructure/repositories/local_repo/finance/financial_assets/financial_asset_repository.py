# Financial Asset Local Repository
# Mirrors src/infrastructure/models/finance/financial_assets/financial_asset.py

class FinancialAssetRepository:
    """Local repository for financial asset model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, financial_asset):
        """Save financial asset to local storage"""
        self.data_store.append(financial_asset)
        
    def find_by_id(self, financial_asset_id):
        """Find financial asset by ID"""
        for financial_asset in self.data_store:
            if getattr(financial_asset, 'id', None) == financial_asset_id:
                return financial_asset
        return None
        
    def find_all(self):
        """Find all financial assets"""
        return self.data_store.copy()