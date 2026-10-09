from src.application.services.time_series.time_series_service import TimeSeriesService
from src.domain.entities.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeries
from typing import Any, List

class FinancialAssetTimeSeriesService(TimeSeriesService):
    def __init__(self, repository: Any):
        """
        Initializes the FinancialAssetTimeSeriesService with the specified repository.
        :param repository: repository of FinancialAssetTimeSeries (must provide get_by_asset_id).
        """
        super().__init__(repository)
    
    def get_by_asset_id(self, asset_id: int) -> List[FinancialAssetTimeSeries]:
        """
        Retrieves all FinancialAssetTimeSeries related to a specific asset.
        :param asset_id: The ID of the financial asset (stock, bond, etc.)
        :return: List of FinancialAssetTimeSeries objects.
        """
        return self.repository.get_by_asset_id(asset_id)
