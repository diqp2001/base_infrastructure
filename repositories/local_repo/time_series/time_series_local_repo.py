# Time Series Local Repository
# Mirrors src/infrastructure/models/time_series/time_series.py

class TimeSeriesLocalRepository:
    """Local repository for time series model"""
    
    def __init__(self):
        self.data_store = []
    
    def save(self, time_series):
        """Save time series to local storage"""
        self.data_store.append(time_series)
        
    def find_by_id(self, time_series_id):
        """Find time series by ID"""
        for ts in self.data_store:
            if getattr(ts, 'id', None) == time_series_id:
                return ts
        return None
        
    def find_all(self):
        """Find all time series"""
        return self.data_store.copy()