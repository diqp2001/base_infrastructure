from typing import List

class TimeSeriesService:
    def __init__(self, repository):
        """
        Initializes the TimeSeriesService with a repository instance.
        :param repository: The repository instance to interact with the database.
        """
        self.repository = repository
    
    def get_by_id(self, id: int):
        """
        Retrieves a time series object by its ID.
        :param id: The unique identifier for the time series.
        :return: TimeSeries object or None if not found.
        """
        return self.repository.get_by_id(id)
    
    def save(self, time_series):
        """
        Saves a time series object to the database.
        :param time_series: The time series object to be saved.
        """
        self.repository.save(time_series)
    
    def get_all(self) -> List:
        """
        Retrieves all time series.
        :return: List of time series objects.
        """
        return self.repository.get_all()
