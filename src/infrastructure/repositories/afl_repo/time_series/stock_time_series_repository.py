from sqlalchemy.orm import Session
from sqlalchemy import func

from domain.entities.time_series.finance.stock_time_series import StockTimeSeries

class StockTimeSeriesRepository:
    def __init__(self, db_session: Session, stock_repository):
        """
        Initialize the StockTimeSeriesRepository.
        :param db_session: The database session to interact with the database.
        :param stock_repository: An instance of StockRepository to call save_list function.
        """
        self.db_session = db_session
        self.stock_repository = stock_repository

    def get_unique_group_by(self, time_series: StockTimeSeries, group_by_columns: list):
        """
        Get a unique group of stocks based on the specified columns from the time series.
        :param time_series: The StockTimeSeries object.
        :param group_by_columns: The list of column names to group by.
        :return: A list of unique stock entries.
        """
        # Create a query that groups by the specified columns
        group_by_columns = [time_series.time_series[col] for col in group_by_columns]
        
        # Query the DataFrame for unique groups based on the selected columns
        unique_stocks = time_series.time_series.groupby(group_by_columns).size().reset_index()
        
        # Return a list of stock entities
        stock_entities = []
        for _, row in unique_stocks.iterrows():
            stock = time_series.create_stock(
                row['stock_id'], 
                row['name'], 
                row['price'], 
                row.get('sector', None), 
                row.get('country', None)
            )
            stock_entities.append(stock)
        
        return stock_entities

    def save_unique_stocks(self, time_series: StockTimeSeries, group_by_columns: list, db):
        """
        Get unique stocks by group, then save them to the database using StockRepository.
        :param time_series: The StockTimeSeries object.
        :param group_by_columns: The list of columns to group by.
        :param db: The database session to interact with.
        """
        unique_stocks = self.get_unique_group_by(time_series, group_by_columns)
        self.stock_repository.save_list(unique_stocks, db)
