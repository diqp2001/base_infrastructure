# src/application/managers/project_managers/cross_sectionnal_ML_stock_returns_project/cross_sectionnal_ML_stock_returns_project_manager.py

import os
from turtle import pd

from application.services.data_service import DataService
from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.config import CONFIG_CROSS_SECTIONNAL_ML_STOCK_RETURNS as config

from application.managers.project_managers.project_manager import ProjectManager
from application.managers.api_managers.api_kaggle_manager.api_manager_kaggle import KaggleAPIManager
from application.services.database_service import DatabaseService
from src.domain.entities.finance.financial_assets.stock import Stock as Stock_Entity
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
        self.setup_database_manager(DatabaseService(config['DB_TYPE']))
        self.setup_data_manager(DataService())
        # Initialize other managers as required (DataManager, ModelManager, etc.)
    def execute_database_management_tasks(self):
        """
        Workflow to download dataset from Kaggle, set up database connection, and create tables.
        """
        # Step 1: Create SQLite engine and session
        current_directory = os.getcwd()  # Get current working directory

        # Define the path to the CSV file in the dataset
        dataset_path = os.path.join(current_directory, config['csv_stock_file'])

        # Step 2: Check if the CSV file already exists in the dataset path
        if not os.path.exists(dataset_path):
            # If the file does not exist, download it from Kaggle
            print("CSV file not found. Downloading dataset from Kaggle...")
            try:
                dataset_path = self.api_manager.download_dataset(config['dataset_name'],current_directory)
            except Exception as e:
                print(f"Error downloading dataset from Kaggle: {e}")
                return
        else:
            # If the CSV file exists, no need to download
            print(f"CSV file already exists at {dataset_path}. Skipping download.")

        # Step 3: Load the dataset into a DataFrame
        try:
            data_df = self.database_manager.csv_to_dataframe(dataset_path)
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            

        # Step 4: Process data and create Identification and FinancialAssetTimeSeries tables
        # Extract identification information and time series data
        identification_data = self.data_manager.get_identification_data_from_dataframe(data_df, ['ticker', 'company_name'])
        timeseries_data = data_df[['ticker', 'date', 'price', 'volume']]

        # Step 4.1: Create list of Stock_Entity objects from identification_data
        stock_entities = []
        for _, row in identification_data.iterrows():
            stock_entity = Stock_Entity(
                id=row['ticker'],  # Assuming 'ticker' is the primary key
                name=row['company_name']  # Assuming 'company_name' is the stock's name
            )
            stock_entities.append(stock_entity)

        # Step 4.2: Save list of Stock_Entity using the save_list method of StockRepository
        try:
            # Pass the session object from the database manager for saving the data
            self.stock_repository.save_list(stock_entities, self.database_manager.session)
        except Exception as e:
            print(f"Error saving stock entities: {e}")
            return

        # Step 5: Create FinancialAssetTimeSeries table in the database
        self.create_financial_asset_timeseries_table(self.database_manager.session, timeseries_data)




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

    

