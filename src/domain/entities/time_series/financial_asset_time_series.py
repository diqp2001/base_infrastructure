from datetime import datetime
from typing import List
from src.domain.entities.time_series.time_series import TimeSeries
from src.domain.entities.financial_assets.financial_asset import FinancialAsset

class FinancialAssetTimeSeries(TimeSeries):
    def __init__(self, id: int, dates: List[datetime], values: List[float], asset: FinancialAsset):
        """
        TimeSeries specifically for financial assets (e.g., stocks, bonds).
        
        :param id: Unique identifier for the TimeSeries.
        :param dates: List of datetime objects representing the dates of each data point.
        :param values: List of float values representing the time series data points.
        :param asset: The associated financial asset (e.g., Stock).
        """
        super().__init__(id, dates, values)
        self.asset = asset  # The associated FinancialAsset object (e.g., stock)

    def __repr__(self):
        return f"<FinancialAssetTimeSeries(id={self.id}, asset={self.asset.name}, length={len(self.dates)})>"

    def get_asset_name(self):
        """
        Returns the name of the associated financial asset.
        """
        return self.asset.name if self.asset else None
