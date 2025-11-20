import requests
import os
import quandl
import datetime as dt
from typing import List, Optional
import pandas as pd
import numpy as np
from .api_service import ApiService


class QuandlApiService(ApiService):
    """
    Service for managing interactions with the Quandl API.
    Handles data fetching, local storage, and data processing.
    """

    def __init__(
        self,
        api_url: str = "https://data.nasdaq.com/api/v3",
        api_key: Optional[str] = None,
        data_folder: str = "data/quandl",
    ):
        """
        Initialize the Quandl API service.

        Args:
            api_url: Base URL for Quandl API (default is for Nasdaq Data Link)
            api_key: API key for Quandl
            data_folder: Directory to save downloaded data
        """
        super().__init__(api_url)
        self.api_key = api_key or os.getenv("QUANDL_API_KEY")
        self.data_folder = data_folder
        
        if self.api_key:
            quandl.ApiConfig.api_key = self.api_key

        # Ensure data folder exists
        os.makedirs(data_folder, exist_ok=True)

    def pull_quandl_sample_data(self, ticker: str) -> pd.DataFrame:
        """
        Pull sample data from local Quandl files for a specific ticker.

        Args:
            ticker: The ticker for which to pull data

        Returns:
            DataFrame with processed data containing date as index and 'close' column
        """
        file_path = os.path.join(self.data_folder, f"{ticker}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file for {ticker} not found at {file_path}")

        data = pd.read_csv(file_path, parse_dates=[0])
        return (
            data.rename(columns={"Trade Date": "date", "Date": "date", "Settle": "close"})
            .set_index("date")
            .replace(0.0, np.nan)
        )

    def _fill_blanks(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Fill blanks in a DataFrame by forward filling and limiting the date range.

        Args:
            data: Input DataFrame with a 'close' column

        Returns:
            DataFrame with missing values filled
        """
        return data[data["close"].first_valid_index() : data["close"].last_valid_index()].ffill()

    def pull_pinnacle_data(self, ticker: str, folder: str, cut: str) -> pd.DataFrame:
        """
        Pull data from Pinnacle for a specific ticker.

        Args:
            ticker: Ticker symbol
            folder: Folder containing the Pinnacle data files
            cut: Data cut version

        Returns:
            DataFrame with processed data containing date as index and 'close' column
        """
        file_path = os.path.join(folder, f"{ticker}_{cut}.CSV")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Pinnacle data file for {ticker} not found at {file_path}")

        data = pd.read_csv(
            file_path,
            names=["date", "open", "high", "low", "close", "volume", "open_int"],
            parse_dates=[0],
            index_col=0,
        )
        return data[["close"]].replace(0.0, np.nan)

    def pull_pinnacle_data_multiple(
        self, tickers: List[str], folder: str, cut: str, fill_missing_dates: bool = False
    ) -> pd.DataFrame:
        """
        Pull data for multiple tickers and optionally fill missing dates.

        Args:
            tickers: List of tickers
            folder: Folder containing Pinnacle data files
            cut: Data cut version
            fill_missing_dates: Whether to fill missing dates

        Returns:
            DataFrame with consolidated data for all tickers
        """
        data = pd.concat(
            [self.pull_pinnacle_data(ticker, folder, cut).assign(ticker=ticker) for ticker in tickers]
        )

        if not fill_missing_dates:
            return data.dropna()

        # Generate all possible dates
        dates = data.reset_index()[["date"]].drop_duplicates().sort_values("date")
        data = data.reset_index().set_index("ticker")

        filled_data = pd.concat(
            [
                self._fill_blanks(
                    dates.merge(data.loc[ticker], on="date", how="left").assign(ticker=ticker)
                )
                for ticker in tickers
            ]
        )
        return filled_data.reset_index().set_index("date").drop(columns="index")

    def fetch_quandl_data(self, codes: List[str] = ['CME'], start_date: str = "2020-01-01", depth: int = 1):
        """
        Fetch data from Quandl and save locally.

        Args:
            codes: List of Quandl codes to fetch
            start_date: Starting date for data fetching
            depth: Depth parameter for the Quandl code (e.g., futures depth)
        """
        for code in codes:
            print(f"Fetching data for: {code}")
            try:
                # Fetch continuous futures data
                data = quandl.get('CHRIS/wiki-continuous-futures', start_date=start_date)
                
            except Exception as ex:
                print(f"Error fetching data for {code}: {ex}")
                continue

            # Save data if it meets criteria
            if "Settle" in data.columns and data.index.min() <= dt.datetime(2015, 1, 1):
                file_name = f"{code.split('/')[-1]}.csv"
                save_path = os.path.join(self.data_folder, file_name)
                data[["Settle"]].to_csv(save_path)
                print(f"Data saved to: {save_path}")
            else:
                print(f"No valid data found for {code}.")

    def fetch_dataset(self, dataset_code: str, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None, **kwargs) -> pd.DataFrame:
        """
        Fetch a specific dataset from Quandl.

        Args:
            dataset_code: Quandl dataset code (e.g., 'WIKI/AAPL')
            start_date: Start date for data (YYYY-MM-DD format)
            end_date: End date for data (YYYY-MM-DD format)
            **kwargs: Additional parameters for quandl.get()

        Returns:
            DataFrame with fetched data
        """
        try:
            print(f"Fetching dataset: {dataset_code}")
            data = quandl.get(dataset_code, start_date=start_date, end_date=end_date, **kwargs)
            print(f"Successfully fetched {len(data)} rows for {dataset_code}")
            return data
            
        except Exception as e:
            print(f"Failed to fetch dataset {dataset_code}: {e}")
            raise

    def fetch_oil_prices(self) -> pd.DataFrame:
        """
        Fetch oil price data from Quandl.

        Returns:
            DataFrame with oil price data
        """
        try:
            return self.fetch_dataset("EIA/PET_RWTC_D")
        except Exception as e:
            print(f"Failed to fetch oil prices: {e}")
            raise

    def save_data(self, ticker: str, data: pd.DataFrame, subfolder: str = None) -> str:
        """
        Save DataFrame to local storage.

        Args:
            ticker: Ticker symbol for filename
            data: DataFrame to save
            subfolder: Optional subfolder within data_folder

        Returns:
            Path to saved file
        """
        folder = os.path.join(self.data_folder, subfolder) if subfolder else self.data_folder
        os.makedirs(folder, exist_ok=True)
        
        file_path = os.path.join(folder, f"{ticker}.csv")
        data.to_csv(file_path)
        print(f"Data saved to: {file_path}")
        return file_path

    def load_saved_data(self, ticker: str, subfolder: str = None) -> pd.DataFrame:
        """
        Load saved data for a specific ticker from local storage.

        Args:
            ticker: Ticker for which data should be loaded
            subfolder: Optional subfolder within data_folder

        Returns:
            DataFrame with loaded data
        """
        folder = os.path.join(self.data_folder, subfolder) if subfolder else self.data_folder
        file_path = os.path.join(folder, f"{ticker}.csv")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file for {ticker} not found at {file_path}")

        return pd.read_csv(file_path, parse_dates=["date"], index_col="date")

    def list_saved_files(self, subfolder: str = None) -> List[str]:
        """
        List all saved CSV files.

        Args:
            subfolder: Optional subfolder to list

        Returns:
            List of saved filenames
        """
        folder = os.path.join(self.data_folder, subfolder) if subfolder else self.data_folder
        
        try:
            return [f for f in os.listdir(folder) if f.endswith('.csv')]
        except FileNotFoundError:
            return []

    def fetch_and_save(self, dataset_code: str, ticker: str = None, 
                      subfolder: str = None, **kwargs) -> str:
        """
        Fetch data from Quandl and save it locally.

        Args:
            dataset_code: Quandl dataset code
            ticker: Ticker symbol for filename (defaults to dataset_code)
            subfolder: Optional subfolder
            **kwargs: Additional parameters for fetching

        Returns:
            Path to saved file
        """
        if ticker is None:
            ticker = dataset_code.replace('/', '_')
            
        data = self.fetch_dataset(dataset_code, **kwargs)
        return self.save_data(ticker, data, subfolder)