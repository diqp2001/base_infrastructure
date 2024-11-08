from datetime import datetime
from typing import List

class TimeSeries:
    def __init__(self, id: int, dates: List[datetime], values: List[float]):
        """
        TimeSeries object represents a series of time-stamped data for a generic asset or value.
        
        :param id: Unique identifier for the TimeSeries.
        :param dates: List of datetime objects representing the dates of each data point.
        :param values: List of float values representing the data points for the asset over time.
        """
        self.id = id
        self.dates = dates
        self.values = values

    def __repr__(self):
        return f"<TimeSeries(id={self.id}, asset_id={self.asset_id}, length={len(self.dates)})>"

    def get_average_value(self):
        """
        Returns the average value of the time series data.
        """
        return sum(self.values) / len(self.values) if self.values else None
