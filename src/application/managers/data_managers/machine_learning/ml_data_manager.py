# src/managers/data_managers/machine_learning/ml_data_manager.py


import pandas as pd
from application.managers.data_managers.data_manager import DataManager


class MLDataManager(DataManager):
    """
    MLDataManager is a child of DataManager specific for handling machine learning-related data operations.
    It can include specialized methods for working with data used in ML models.
    """

    def __init__(self, database_manager, project_name: str, scaler: str = 'standard'):
        super().__init__(database_manager, scaler)  # Initialize the parent class with scaler type
        self.project_name = project_name  # Specific project context for ML (if needed)
    
    def get_training_data(self, query_key: str):
        """
        Retrieves training data from the database based on a specific query key.
        :param query_key: The query key to fetch the relevant data from the configuration.
        :return: The training data as a DataFrame.
        """
        query = self.database_manager.config_data_source_manager.QUERIES.get(query_key)
        if query:
            return self.query_data(query)
        else:
            print(f"No query found for key: {query_key}")
            return None

    def preprocess_data(self, dataframe: pd.DataFrame, handle_nulls: bool = True):
        """
        Perform ML-specific preprocessing on the dataframe (e.g., handling missing values, scaling, etc.).
        :param dataframe: The DataFrame to preprocess.
        :return: The preprocessed DataFrame.
        """
        return super().preprocess_data(dataframe, handle_nulls)

    # Add more ML-specific methods (e.g., feature engineering, outlier removal, etc.)
