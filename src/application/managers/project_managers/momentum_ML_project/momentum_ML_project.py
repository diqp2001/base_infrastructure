import pandas as pd

from application.managers.api_managers.api_quandl_manager.api_quandl_manager import QuandlApiManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.api_managers.api_nasdaq_data_link_manager.api_nasdaq_data_link_manager import NasdaqDataLinkApiManager
from application.managers.database_managers.database_manager import DatabaseManager
from .config import MOMENTUM_ML_FUTURES_RETURNS as config




class MomentumMLProjectManager(ProjectManager):
    def __init__(self):
        """
        Initializes the Momentum ML Project Manager with required managers.
        """
        super().__init__()
        # Initialize API manager with Nasdaq Data Link API key and data folder
        self.api_manager = NasdaqDataLinkApiManager(
            api_key=config["NASDAQ_API_KEY"],
            data_folder=config.get("DATA_FOLDER", "data/nasdaq_data_link"),
        )
        '''self.api_manager2 = QuandlApiManager(
            api_key=config["NASDAQ_API_KEY"],
            data_folder=config.get("DATA_FOLDER", "data/nasdaq_data_link"),
        )'''
        # Uncomment and configure DatabaseManager if needed
        # self.database_manager = DatabaseManager(config['DB_TYPE'])

    def test_single_future(self):
        """
        Test fetching data for a single future instrument.
        """
        df = self.fetch_futures_data(instrument='CME_FI')
        print(df.describe())

    def fetch_futures_data(
        self, database_code: str = "CHRIS", instrument: str = "CME_FI", params: dict = None
    ) -> pd.DataFrame:
        """
        Fetches continuous futures data from the Nasdaq Data Link API.

        Args:
        - database_code: Database code for Nasdaq Data Link API (default: 'CHRIS').
        - instrument: Specific instrument identifier (default: 'CME_FI').
        - params: Optional parameters for filtering data (e.g., 'start_date', 'end_date').

        Returns:
        - DataFrame: The fetched data as a pandas DataFrame.
        """
        print(f"Fetching continuous futures data for instrument: {instrument}...")
        try:
            #data = self.api_manager2.fetch_quandl_data()
            #data = self.api_manager.fetch_data_from_url()
            data = self.api_manager.fetch_data(
                dataset_code=instrument, database_code=database_code, params=params
            )

            print(f"Data successfully retrieved for {instrument}.")
            return data
        except Exception as e:
            print(f"Failed to fetch data for {instrument}: {e}")
            raise
