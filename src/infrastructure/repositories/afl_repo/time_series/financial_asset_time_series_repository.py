from typing import List
from src.infrastructure.repositories.local_repo.time_series.time_series_repository import TimeSeriesRepository
from src.domain.entities.time_series.finance.financial_asset_time_series import FinancialAssetTimeSeries
from sqlalchemy.orm import Session

class FinancialAssetTimeSeriesRepository(TimeSeriesRepository):
    def __init__(self, db_type='sqlite'):
        """
        Initializes the repository for FinancialAssetTimeSeries with the specified database type.
        :param db_type: Type of the database (sqlite, sql_server, etc.)
        """
        super().__init__(db_type)
    
    def get_by_id(self, id: int) -> FinancialAssetTimeSeries:
        """
        Retrieves a FinancialAssetTimeSeries object by its ID.
        :param id: The unique identifier for the time series.
        :return: FinancialAssetTimeSeries object or None if not found.
        """
        result = self.session.query(FinancialAssetTimeSeries).filter(FinancialAssetTimeSeries.id == id).first()
        return result
    
    def save(self, time_series: FinancialAssetTimeSeries) -> None:
        """
        Saves a FinancialAssetTimeSeries object to the database.
        :param time_series: The FinancialAssetTimeSeries object to be saved.
        """
        self.session.add(time_series)
        self.session.commit()

    def get_by_asset_id(self, asset_id: int) -> List[FinancialAssetTimeSeries]:
        """
        Retrieves all FinancialAssetTimeSeries related to a specific asset.
        :param asset_id: The ID of the financial asset (stock, bond, etc.)
        :return: List of FinancialAssetTimeSeries objects.
        """
        return self.session.query(FinancialAssetTimeSeries).filter(FinancialAssetTimeSeries.asset_id == asset_id).all()

    def get_all(self) -> List[FinancialAssetTimeSeries]:
        """
        Retrieves all FinancialAssetTimeSeries objects.
        :return: List of all FinancialAssetTimeSeries objects.
        """
        return self.session.query(FinancialAssetTimeSeries).all()
