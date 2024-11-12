# src/application/managers/project_managers/cross_sectionnal_ML_stock_returns_project/cross_sectionnal_ML_stock_returns_project_manager.py

import os
from turtle import pd

from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.config import CONFIG_CROSS_SECTIONNAL_ML_STOCK_RETURNS as config
from infrastructure.database.base import create_engine_and_session
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.api_managers.api_kaggle_manager.api_manager_kaggle import KaggleAPIManager
from application.managers.database_managers.database_manager import DatabaseManager
from infrastructure.repositories.financial_assets.stock_repository import StockRepository
# (Import other managers as necessary)
#import CONFIG_CROSS_SECTIONNAL_ML_STOCK_RETURNS as config
class CrossSectionalMLStockReturnsProjectManager(ProjectManager):
    """
    Project Manager for handling cross-sectional machine learning on stock returns.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_api_manager(KaggleAPIManager())
        self.setup_database_manager(DatabaseManager(config['DB_TYPE']))
        self.stock_repository = StockRepository()
        # Initialize other managers as required (DataManager, ModelManager, etc.)
    def execute_database_management_tasks(self):
        """
        Workflow to download dataset from Kaggle, set up database connection, and create tables.
        """
        

        # Step 1: Create SQLite engine and session
        current_directory = os.getcwd() #cd ..

        # Step 2: Download dataset from Kaggle
        dataset_path = self.api_manager.download_dataset(config['dataset_name'])
        
        # Load dataset into a DataFrame
        try:
            data_df = self.database_manager.csv_to_dataframe(os.path.join(dataset_path, config['csv_stock_file']))
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return

        # Step 3: Process data and create Identification and FinancialAssetTimeSeries tables
        # Extract identification information and time series data
        identification_data = data_df[['ticker', 'company_name']].drop_duplicates()
        timeseries_data = data_df[['ticker', 'date', 'price', 'volume']]

        # Step 4: Create Identification table in the database
        # This may be stored as a Company table or similar depending on your setup
        self.create_identification_table(self.database_manager.session, identification_data)

        # Step 5: Create FinancialAssetTimeSeries table in the database
        self.create_financial_asset_timeseries_table(self.database_manager.session, timeseries_data)

        print("Database management tasks executed successfully.")
        

        return None


    def execute_entire_project(self):
        """
        Define the workflow for the cross-sectional ML stock returns project.
        """
        print("Executing Cross-Sectional ML Stock Returns Project Workflow")

        # Step 1: Download dataset from Kaggle
        dataset_name = 'zillow/zecon'
        dataset_file_path = self.api_manager.download_dataset(dataset_name)
        
        # Step 2: Load dataset into database
        table_name = 'stock_returns'
        self.database_manager.load_csv_to_db(file_path=dataset_file_path, table_name=table_name)

        # Step 3: Process data for machine learning
        # Example: Load data into DataFrame, clean, and transform
        df = self.database_manager.fetch_dataframe_with_dynamic_table('fetch_stock_data', table_name=table_name)
        # (Optional) Call data manager methods to process `df` if needed
        
        # Step 4: Train Model
        # Example: Call model manager to train on `df`
        # trained_model = self.model_manager.train_model(df)

        # Step 5: Generate and save reports
        # Example: Generate model performance reports
        # self.reporting_manager.generate_report(trained_model)

        print("Cross-Sectional ML Stock Returns Project Execution Complete")

    

