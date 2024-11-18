
from src.domain.entities.time_series.time_series import TimeSeries
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

class FinancialAssetTimeSeries(TimeSeries):
    def __init__(self, data):
        """
        Initialize the FinancialAssetTimeSeries object.
        :param data: Data that can be a DataFrame, numpy array, list, or dict.
        """
        super().__init__(data)
        # Additional attributes or methods specific to financial assets can go here