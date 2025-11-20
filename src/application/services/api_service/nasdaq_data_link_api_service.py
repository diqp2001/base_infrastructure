import os
import pandas as pd
import nasdaqdatalink
import requests
from typing import Optional, Dict, Any
from .api_service import ApiService


class NasdaqDataLinkApiService(ApiService):
    """
    Service for managing interactions with the Nasdaq Data Link API.
    Handles data fetching, local storage, and data processing for financial datasets.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        data_folder: str = "data/nasdaq",
    ):
        """
        Initialize the Nasdaq Data Link API service.

        Args:
            api_key: API key for accessing Nasdaq Data Link
            data_folder: Directory to save downloaded data
        """
        super().__init__("https://data.nasdaq.com/api/v3")
        self.api_key = api_key or os.getenv("NASDAQ_API_KEY")
        self.data_folder = data_folder

        if not self.api_key:
            raise ValueError("API key is required. Set NASDAQ_API_KEY environment variable or provide api_key parameter.")

        # Set the API key using the nasdaqdatalink package
        nasdaqdatalink.ApiConfig.api_key = self.api_key

        # Ensure the data folder exists
        os.makedirs(data_folder, exist_ok=True)

    def fetch_dataset(self, dataset_code: str, database_code: Optional[str] = None, 
                     **kwargs) -> pd.DataFrame:
        """
        Fetch data from Nasdaq Data Link using the nasdaqdatalink package.

        Args:
            dataset_code: Dataset code (e.g., 'OIL')
            database_code: Database code (optional)
            **kwargs: Additional parameters (start_date, end_date, limit, etc.)

        Returns:
            DataFrame with fetched data
        """
        try:
            full_code = f"{database_code}/{dataset_code}" if database_code else dataset_code
            print(f"Fetching data for {full_code}...")
            
            # Use nasdaqdatalink.get for time series data
            data = nasdaqdatalink.get(full_code, **kwargs)
            print(f"Data successfully retrieved for {full_code}.")
            return data
            
        except Exception as e:
            print(f"Failed to fetch data for {dataset_code}: {e}")
            raise

    def fetch_table(self, table_code: str, **kwargs) -> pd.DataFrame:
        """
        Fetch table data from Nasdaq Data Link.

        Args:
            table_code: Table code (e.g., 'ZACKS/FC', 'CHRIS/CME')
            **kwargs: Parameters like ticker, date, etc.

        Returns:
            DataFrame with table data
        """
        try:
            print(f"Fetching table data for {table_code}...")
            data = nasdaqdatalink.get_table(table_code, **kwargs)
            print(f"Table data successfully retrieved for {table_code}.")
            return data
            
        except Exception as e:
            print(f"Failed to fetch table data for {table_code}: {e}")
            raise

    def fetch_bulk_data(self, database_code: str, **kwargs) -> pd.DataFrame:
        """
        Fetch bulk data download from Nasdaq Data Link.

        Args:
            database_code: Database code for bulk download
            **kwargs: Additional parameters

        Returns:
            DataFrame with bulk data
        """
        try:
            print(f"Fetching bulk data for {database_code}...")
            data = nasdaqdatalink.export_table(database_code, **kwargs)
            print(f"Bulk data successfully retrieved for {database_code}.")
            return data
            
        except Exception as e:
            print(f"Failed to fetch bulk data for {database_code}: {e}")
            raise

    def fetch_continuous_futures(self, start_date: Optional[str] = None, 
                                end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch continuous futures data from Nasdaq Data Link.

        Args:
            start_date: Start date for the data (YYYY-MM-DD format)
            end_date: End date for the data (YYYY-MM-DD format)

        Returns:
            DataFrame with continuous futures data
        """
        try:
            # Use the table method for continuous futures
            kwargs = {}
            if start_date:
                kwargs['date.gte'] = start_date
            if end_date:
                kwargs['date.lte'] = end_date
                
            return self.fetch_table('CHRIS/CME', **kwargs)
            
        except Exception as e:
            print(f"Failed to fetch continuous futures data: {e}")
            raise

    def fetch_zacks_fundamentals(self, ticker: str, **kwargs) -> pd.DataFrame:
        """
        Fetch Zacks fundamentals data for a specific ticker.

        Args:
            ticker: Stock ticker symbol
            **kwargs: Additional parameters

        Returns:
            DataFrame with fundamental data
        """
        try:
            return self.fetch_table('ZACKS/FC', ticker=ticker, **kwargs)
        except Exception as e:
            print(f"Failed to fetch Zacks data for {ticker}: {e}")
            raise

    def search_datasets(self, query: str, **kwargs) -> pd.DataFrame:
        """
        Search for datasets on Nasdaq Data Link.

        Args:
            query: Search query string
            **kwargs: Additional search parameters

        Returns:
            DataFrame with search results
        """
        try:
            results = nasdaqdatalink.search(query, **kwargs)
            return results
        except Exception as e:
            print(f"Failed to search for datasets: {e}")
            raise

    def save_data(self, dataset_code: str, df: pd.DataFrame, 
                  file_format: str = 'csv') -> str:
        """
        Save data locally in specified format.

        Args:
            dataset_code: Dataset identifier for the file name
            df: DataFrame to save
            file_format: Format to save ('csv', 'json', 'parquet')

        Returns:
            Path to saved file
        """
        file_path = os.path.join(self.data_folder, f"{dataset_code}.{file_format}")
        
        try:
            if file_format.lower() == 'csv':
                df.to_csv(file_path)
            elif file_format.lower() == 'json':
                df.to_json(file_path, orient='records', date_format='iso')
            elif file_format.lower() == 'parquet':
                df.to_parquet(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
                
            print(f"Data saved to {file_path}")
            return file_path
            
        except Exception as e:
            print(f"Failed to save data: {e}")
            raise

    def load_data(self, dataset_code: str, file_format: str = 'csv') -> pd.DataFrame:
        """
        Load saved data from local storage.

        Args:
            dataset_code: Dataset identifier
            file_format: Format of the saved file ('csv', 'json', 'parquet')

        Returns:
            DataFrame with loaded data
        """
        file_path = os.path.join(self.data_folder, f"{dataset_code}.{file_format}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file for {dataset_code} not found at {file_path}")

        try:
            if file_format.lower() == 'csv':
                # Try to parse dates if there's a 'Date' column
                df = pd.read_csv(file_path)
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                return df
            elif file_format.lower() == 'json':
                return pd.read_json(file_path, orient='records')
            elif file_format.lower() == 'parquet':
                return pd.read_parquet(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
                
        except Exception as e:
            print(f"Failed to load data: {e}")
            raise

    def fetch_and_save(self, dataset_code: str, database_code: Optional[str] = None,
                      file_format: str = 'csv', **kwargs) -> str:
        """
        Fetch data from Nasdaq Data Link and save it locally.

        Args:
            dataset_code: Dataset code
            database_code: Database code (optional)
            file_format: Format to save the data
            **kwargs: Additional parameters for fetching

        Returns:
            Path to saved file
        """
        df = self.fetch_dataset(dataset_code, database_code, **kwargs)
        return self.save_data(dataset_code, df, file_format)

    def get_usage_info(self) -> Dict[str, Any]:
        """
        Get API usage information.

        Returns:
            Dictionary with usage information
        """
        try:
            return nasdaqdatalink.ApiConfig.api_key_usage()
        except Exception as e:
            print(f"Failed to get usage info: {e}")
            return {}

    def list_saved_files(self) -> list:
        """
        List all saved data files.

        Returns:
            List of saved filenames
        """
        try:
            return [f for f in os.listdir(self.data_folder) 
                   if f.endswith(('.csv', '.json', '.parquet'))]
        except FileNotFoundError:
            return []