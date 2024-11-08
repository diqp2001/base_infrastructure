from src.application.services.time_series.time_series_service import TimeSeriesService
from src.infrastructure.repositories.time_series.financial_asset_time_series_repository import FinancialAssetTimeSeriesRepository
from src.domain.entities.time_series.financial_asset_time_series import FinancialAssetTimeSeries
from typing import List

class FinancialAssetTimeSeriesService(TimeSeriesService):
    def __init__(self, repository: FinancialAssetTimeSeriesRepository):
        """
        Initializes the FinancialAssetTimeSeriesService with the specified repository.
        :param repository: The repository instance for FinancialAssetTimeSeries.
        """
        super().__init__(repository)
    
    def get_by_asset_id(self, asset_id: int) -> List[FinancialAssetTimeSeries]:
        """
        Retrieves all FinancialAssetTimeSeries related to a specific asset.
        :param asset_id: The ID of the financial asset (stock, bond, etc.)
        :return: List of FinancialAssetTimeSeries objects.
        """
        return self.repository.get_by_asset_id(asset_id)
