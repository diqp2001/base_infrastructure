# Stock Time Series Local Repository
# Mirrors src/infrastructure/models/time_series/finance/stock_time_series.py

class StockTimeSeriesRepository:
    """Local repository for stock time series model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, stock_time_series):
        """Save stock time series to local storage"""
        self.data_store.append(stock_time_series)
        
    def find_by_id(self, stock_time_series_id):
        """Find stock time series by ID"""
        for ts in self.data_store:
            if getattr(ts, 'id', None) == stock_time_series_id:
                return ts
        return None
        
    def find_all(self):
        """Find all stock time series"""
        return self.data_store.copy()