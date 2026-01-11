# Financial Asset Time Series Local Repository
# Mirrors src/infrastructure/models/time_series/finance/financial_asset_time_series.py

class FinancialAssetTimeSeriesLocalRepository:
    """Local repository for financial asset time series model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, financial_asset_time_series):
        """Save financial asset time series to local storage"""
        self.data_store.append(financial_asset_time_series)
        
    def find_by_id(self, financial_asset_time_series_id):
        """Find financial asset time series by ID"""
        for ts in self.data_store:
            if getattr(ts, 'id', None) == financial_asset_time_series_id:
                return ts
        return None
        
    def find_all(self):
        """Find all financial asset time series"""
        return self.data_store.copy()