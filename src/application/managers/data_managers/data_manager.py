# src/managers/data_managers/data_manager.py
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler

class DataManager:
    """
    Parent class for managing data operations across different themes (e.g., Machine Learning, Risk Management).
    Provides common methods for querying, handling data transformations (wrangling), and scaling.
    """

    def __init__(self, database_manager, scaler: str = 'standard'):
        """
        Initialize the DataManager with a specific database manager and scaler type.
        :param database_manager: The database manager responsible for DB operations.
        :param scaler: The type of scaler to use for data preprocessing ('standard' or 'minmax').
        """
        self.database_manager = database_manager  # Reference to the relevant database manager
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
            # Assuming the database manager is responsible for inserting data into the database
            self.database_manager.upload_dataframe_to_db(dataframe, table_name)
            print(f"Data uploaded to {table_name} successfully.")
        except Exception as e:
            print(f"Error uploading data to {table_name}: {e}")

    def query_data(self, query: str):
        """
        Executes a SQL query to retrieve data from the database.
        :param query: The SQL query string.
        :return: Query result (e.g., DataFrame).
        """
        try:
            return self.database_manager.execute_sql_query(query)
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

    def wrangle_data(self, dataframe: pd.DataFrame, handle_nulls: bool = True):
        """
        Perform data wrangling operations on the DataFrame.
        This includes handling missing values and performing other preprocessing steps.
        :param dataframe: The DataFrame to wrangle.
        :param handle_nulls: Whether to handle null values by dropping or filling them.
        :return: The wrangled DataFrame.
        """
        if handle_nulls:
            # Example of handling null values
            # Drop rows with any null values (or you can fill them with a default value)
            dataframe = dataframe.dropna()  # Or use dataframe.fillna() for imputation
        print("Data wrangling completed.")
        return dataframe

    def scale_data(self, dataframe: pd.DataFrame):
        """
        Scales the numeric columns of the DataFrame using the specified scaler.
        :param dataframe: The DataFrame to scale.
        :return: The scaled DataFrame.
        """
        numeric_columns = dataframe.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_columns) > 0:
            dataframe[numeric_columns] = self.scaler_instance.fit_transform(dataframe[numeric_columns])
            print(f"Data scaled using {self.scaler} scaler.")
        else:
            print("No numeric columns to scale.")
        return dataframe

    def preprocess_data(self, dataframe: pd.DataFrame, handle_nulls: bool = True):
        """
        A high-level method that combines wrangling and scaling.
        :param dataframe: The DataFrame to preprocess.
        :param handle_nulls: Whether to handle null values during wrangling.
        :return: The preprocessed DataFrame.
        """
        dataframe = self.wrangle_data(dataframe, handle_nulls)
        dataframe = self.scale_data(dataframe)
        return dataframe
    def get_identification_data_from_dataframe(df,identification_column_list):
        identification_data = df[identification_column_list].drop_duplicates()
        return identification_data

    # Add more general data handling methods here if needed (e.g., transforming data, exporting data)
