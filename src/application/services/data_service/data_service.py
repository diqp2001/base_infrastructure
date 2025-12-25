# src/services/data_service.py
from typing import Optional
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from src.application.services.database_service.database_service import DatabaseService

class DataService:
    """
    Service class for managing data operations across different themes (e.g., Machine Learning, Risk Management).
    Provides common methods for querying, handling data transformations (wrangling), and scaling.
    """

    def __init__(self, database_service: Optional[DatabaseService] = None, db_type: str = 'sqlite', scaler: str = 'standard'):
        """
        Initialize the DataService with a database service and scaler type.
        :param database_service: Optional existing DatabaseService instance
        :param db_type: The database type for the DatabaseService (ignored if database_service provided).
        :param scaler: The type of scaler to use for data preprocessing ('standard' or 'minmax').
        """
        if database_service is not None:
            self.database_service = database_service
        else:
            self.database_service = DatabaseService(db_type)  # Use DatabaseService instead of database_manager
        self.scaler = scaler  # Scaling method ('standard' or 'minmax')
        self.scaler_instance = None

        # Initialize the scaler instance based on the type
        if scaler == 'standard':
            self.scaler_instance = StandardScaler()
        elif scaler == 'minmax':
            self.scaler_instance = MinMaxScaler()
        else:
            raise ValueError("Invalid scaler type. Choose 'standard' or 'minmax'.")

    def upload_data(self, dataframe, table_name: str):
        """
        Upload a DataFrame to the specified table in the database.
        :param dataframe: The DataFrame to upload.
        :param table_name: The target table name in the database.
        """
        try:
            # Use DatabaseService's dataframe_replace_table method
            self.database_service.dataframe_replace_table(dataframe, table_name)
            print(f"Data uploaded to {table_name} successfully.")
        except Exception as e:
            print(f"Error uploading data to {table_name}: {e}")

    def append_data(self, dataframe, table_name: str):
        """
        Append a DataFrame to the specified table in the database.
        :param dataframe: The DataFrame to append.
        :param table_name: The target table name in the database.
        """
        try:
            # Use DatabaseService's dataframe_append_to_table method
            self.database_service.dataframe_append_to_table(dataframe, table_name)
            print(f"Data appended to {table_name} successfully.")
        except Exception as e:
            print(f"Error appending data to {table_name}: {e}")

    def query_data(self, query: str):
        """
        Executes a SQL query to retrieve data from the database.
        :param query: The SQL query string.
        :return: Query result (DataFrame).
        """
        try:
            # Use DatabaseService's session to execute raw SQL
            result = self.database_service.session.execute(query)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            print(f"Error executing query: {e}")
            return pd.DataFrame()

    def query_config_data(self, query_key: str):
        """
        Executes a predefined query from config.
        :param query_key: The key for the query in config.
        :return: Query result as list of dictionaries.
        """
        try:
            return self.database_service.execute_config_query(query_key)
        except Exception as e:
            print(f"Error executing config query {query_key}: {e}")
            return []

    def fetch_dataframe_with_filters(
        self,
        query_key: str,
        table_name: str,
        columns: list = None,
        filters: dict = None,
        top_n: int = None
    ) -> pd.DataFrame:
        """
        Fetches data with dynamic table name and optional filters.
        :param query_key: Key in config QUERIES.
        :param table_name: The table to query.
        :param columns: Optional list of columns to retrieve.
        :param filters: Optional dictionary for filtering results.
        :param top_n: Optional limit on the number of rows.
        :return: DataFrame of query results.
        """
        try:
            return self.database_service.fetch_dataframe_with_dynamic_table(
                query_key=query_key,
                table_name=table_name,
                columns=columns,
                filters=filters,
                top_n=top_n
            )
        except Exception as e:
            print(f"Error fetching filtered data: {e}")
            return pd.DataFrame()

    def clean_data(self, dataframe: pd.DataFrame, strategy: str = 'drop'):
        """
        Clean the dataframe by handling missing values.
        :param dataframe: The DataFrame to clean.
        :param strategy: Strategy for handling missing values ('drop', 'fillna_mean', 'fillna_median', 'fillna_mode').
        :return: Cleaned DataFrame.
        """
        try:
            if strategy == 'drop':
                return dataframe.dropna()
            elif strategy == 'fillna_mean':
                return dataframe.fillna(dataframe.mean())
            elif strategy == 'fillna_median':
                return dataframe.fillna(dataframe.median())
            elif strategy == 'fillna_mode':
                return dataframe.fillna(dataframe.mode().iloc[0])
            else:
                print(f"Unknown cleaning strategy: {strategy}")
                return dataframe
        except Exception as e:
            print(f"Error cleaning data: {e}")
            return dataframe

    def scale_data(self, dataframe: pd.DataFrame, columns: list = None):
        """
        Scale the specified columns of the DataFrame.
        :param dataframe: The DataFrame to scale.
        :param columns: List of column names to scale. If None, all numeric columns are scaled.
        :return: Scaled DataFrame.
        """
        try:
            df_copy = dataframe.copy()
            if columns is None:
                columns = df_copy.select_dtypes(include=[pd.np.number]).columns.tolist()

            if self.scaler_instance:
                df_copy[columns] = self.scaler_instance.fit_transform(df_copy[columns])

            return df_copy
        except Exception as e:
            print(f"Error scaling data: {e}")
            return dataframe

    def transform_data(self, dataframe: pd.DataFrame, transformations: dict):
        """
        Apply transformations to the DataFrame.
        :param dataframe: The DataFrame to transform.
        :param transformations: Dictionary mapping column names to transformation functions.
        :return: Transformed DataFrame.
        """
        try:
            df_copy = dataframe.copy()
            for column, transformation in transformations.items():
                if column in df_copy.columns:
                    df_copy[column] = transformation(df_copy[column])
                else:
                    print(f"Warning: Column '{column}' not found in DataFrame.")
            return df_copy
        except Exception as e:
            print(f"Error transforming data: {e}")
            return dataframe

    def aggregate_data(self, dataframe: pd.DataFrame, group_by: list, aggregations: dict):
        """
        Aggregate data by specified columns.
        :param dataframe: The DataFrame to aggregate.
        :param group_by: List of columns to group by.
        :param aggregations: Dictionary mapping column names to aggregation functions.
        :return: Aggregated DataFrame.
        """
        try:
            return dataframe.groupby(group_by).agg(aggregations).reset_index()
        except Exception as e:
            print(f"Error aggregating data: {e}")
            return dataframe

    def merge_datasets(self, left: pd.DataFrame, right: pd.DataFrame, on: str, how: str = 'inner'):
        """
        Merge two DataFrames.
        :param left: Left DataFrame.
        :param right: Right DataFrame.
        :param on: Column(s) to join on.
        :param how: Type of merge ('left', 'right', 'outer', 'inner').
        :return: Merged DataFrame.
        """
        try:
            return pd.merge(left, right, on=on, how=how)
        except Exception as e:
            print(f"Error merging datasets: {e}")
            return left

    def load_from_csv(self, file_path: str, table_name: str = None):
        """
        Load data from CSV file.
        :param file_path: Path to the CSV file.
        :param table_name: Optional table name to upload to database.
        :return: DataFrame.
        """
        try:
            df = self.database_service.csv_to_dataframe(file_path)
            if table_name:
                self.upload_data(df, table_name)
            return df
        except Exception as e:
            print(f"Error loading CSV from {file_path}: {e}")
            return pd.DataFrame()

    def load_from_excel(self, file_path: str, sheet_name: str = 0, table_name: str = None):
        """
        Load data from Excel file.
        :param file_path: Path to the Excel file.
        :param sheet_name: Sheet name or index.
        :param table_name: Optional table name to upload to database.
        :return: DataFrame.
        """
        try:
            df = self.database_service.excel_to_dataframe(file_path, sheet_name)
            if table_name:
                self.upload_data(df, table_name)
            return df
        except Exception as e:
            print(f"Error loading Excel from {file_path}: {e}")
            return pd.DataFrame()

    def close_connection(self):
        """Close the database connection."""
        try:
            self.database_service.close_session()
            print("Database connection closed successfully.")
        except Exception as e:
            print(f"Error closing database connection: {e}")