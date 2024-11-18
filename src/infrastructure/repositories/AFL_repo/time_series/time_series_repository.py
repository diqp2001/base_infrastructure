from typing import List
from src.infrastructure.database.connections import get_database_session
from sqlalchemy.orm import Session

class TimeSeriesRepository:
    def __init__(self, db_type='sqlite'):
        """
        Initializes the repository with the specified database type.
        :param db_type: Type of the database (sqlite, sql_server, etc.)
        """
        self.db_type = db_type
        self.session: Session = get_database_session(db_type)
    
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
