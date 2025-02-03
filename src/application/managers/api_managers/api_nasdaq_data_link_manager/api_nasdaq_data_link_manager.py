import os
import pandas as pd
import nasdaqdatalink
import requests
from src.application.managers.api_managers.api_manager import APIManager


class NasdaqDataLinkApiManager(APIManager):
    """
    Manages interactions with the Nasdaq Data Link API, including data fetching, local storage, and data processing.
    """

    def __init__(
        self,
        api_key: str ,
        data_folder: str ,
    ):
        """
        Initialize the Nasdaq Data Link API manager.

        Args:
        - api_key: API key for accessing Nasdaq Data Link.
        - data_folder: Directory to save downloaded data.
        """
        super().__init__("https://data.nasdaq.com/api/v3")
        self.api_key = api_key or os.getenv("NASDAQ_API_KEY")
        self.data_folder = data_folder

        # Set the API key using the nasdaqdatalink package
        nasdaqdatalink.ApiConfig.api_key = self.api_key

        # Ensure the data folder exists
        os.makedirs(data_folder, exist_ok=True)

    def fetch_data(self, dataset_code: str, database_code: str = None, params: dict = None) -> pd.DataFrame:
        """
        Fetch data from Nasdaq Data Link using the nasdaqdatalink package.

        Args:
        - dataset_code: Dataset code (e.g., 'OIL').
        - database_code: Database code (optional, not needed with nasdaqdatalink.get).
        - params: Additional parameters for fetching data (not used with nasdaqdatalink.get).

        Returns:
        - DataFrame: Fetched data as a Pandas DataFrame.
        """
        try:
            # Fetch data using nasdaqdatalink.get
            full_code = f"{database_code}/{dataset_code}" if database_code else dataset_code
            print(f"Fetching data for {full_code}...")
            #data = nasdaqdatalink.get(full_code)
            #data = nasdaqdatalink.get_table('ZACKS/FC', ticker='AAPL')
            data = nasdaqdatalink.get_table('CHRIS/CME', ticker='DC')
            print(f"Data successfully retrieved for {full_code}.")
            return data
        except Exception as e:
            print(f"Failed to fetch data for {dataset_code}: {e}")
            raise
    def fetch_data_from_url(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch data from a hardcoded URL.

        Args:
        - start_date: Start date for the data (optional, default is undefined).
        - end_date: End date for the data (optional, default is undefined).

        Returns:
        - DataFrame: Fetched data as a Pandas DataFrame.
        """
        base_url = "https://data.nasdaq.com/api/v3/datasets/CHRIS-wiki-continuous-futures/"
        params = {
            "start_date": start_date or "undefined",
            "end_date": end_date or "undefined",
            "api_key": self.api_key,
        }

        try:
            print(f"Fetching data from {base_url} with parameters: {params}...")
            base_url='https://data.nasdaq.com/api/v3/datasets/CHRIS-wiki-continuous-futures/?start_date=undefined&end_date=undefined&api_key=bh2-cWzMCw5e2K2ioUqV'
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract and convert data into a DataFrame
            df = pd.DataFrame(data["dataset"]["data"], columns=data["dataset"]["column_names"])
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            print(f"Data successfully retrieved from {base_url}.")
            return df
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch data from URL: {e}")
            raise

    def save_data(self, dataset_code: str, df: pd.DataFrame):
        """
        Save data locally.

        Args:
        - dataset_code: Dataset identifier for the file name.
        - df: DataFrame to save.
        """
        file_path = os.path.join(self.data_folder, f"{dataset_code}.csv")
        df.to_csv(file_path)
        print(f"Data saved to {file_path}")

    def load_data(self, dataset_code: str) -> pd.DataFrame:
        """
        Load saved data from local storage.

        Args:
        - dataset_code: Dataset identifier.

        Returns:
        - DataFrame: Loaded data as a Pandas DataFrame.
        """
        file_path = os.path.join(self.data_folder, f"{dataset_code}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file for {dataset_code} not found at {file_path}")

        return pd.read_csv(file_path, parse_dates=["Date"], index_col="Date")

    def fetch_and_save(self, dataset_code: str, database_code: str = None):
        """
        Fetch data from Nasdaq Data Link and save it locally.

        Args:
        - dataset_code: Dataset code.
        - database_code: Database code (optional).
        """
        df = self.fetch_data(dataset_code, database_code)
        self.save_data(dataset_code, df)

