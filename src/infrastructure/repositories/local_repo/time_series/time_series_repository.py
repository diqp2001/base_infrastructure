from typing import List
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository, EntityType, ModelType
from sqlalchemy.orm import Session

class TimeSeriesRepository(BaseLocalRepository[EntityType, ModelType]):
    def __init__(self, session: Session):
        super().__init__(session)
    
    def get_by_id(self, id: int) -> object:
        """
        Retrieves a TimeSeries object by its ID.
        :param id: The unique identifier for the time series.
        :return: TimeSeries object or None if not found.
        """
        raise NotImplementedError("This method should be implemented in child classes.")
    
    def save(self, time_series: object) -> None:
        """
        Saves a TimeSeries object to the database.
        :param time_series: The TimeSeries object to be saved.
        """
        raise NotImplementedError("This method should be implemented in child classes.")

    def get_all(self) -> List[object]:
        """
        Retrieves all time series from the database.
        :return: List of TimeSeries objects.
        """
        raise NotImplementedError("This method should be implemented in child classes.")
