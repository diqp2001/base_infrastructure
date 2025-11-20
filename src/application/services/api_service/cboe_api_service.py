import datetime
import os
import requests
import pandas as pd
from urllib.parse import urljoin
from typing import List, Optional
from .api_service import ApiService


class CboeApiService(ApiService):
    """
    Service for downloading and managing CBOE (Chicago Board Options Exchange) data.
    Handles CSV file downloads from CBOE's historical data repository.
    """
    
    def __init__(self, base_url: str = "https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/",
                 download_folder: str = "downloads"):
        """
        Initialize the CBOE API service.
        
        Args:
            base_url: Base URL for CBOE data files
            download_folder: Directory to store downloaded files
        """
        super().__init__(base_url)
        self.base_url = base_url
        self.download_folder = download_folder
        
        # Ensure downloads folder exists
        os.makedirs(download_folder, exist_ok=True)
    
    def download_vx_data(self, start_date: datetime.datetime = None, 
                        end_date: datetime.datetime = None) -> pd.DataFrame:
        """
        Download and consolidate VX (volatility index) CSV data.
        
        Args:
            start_date: Start date for data download (default: 2024-11-01)
            end_date: End date for data download (default: 2025-04-01)
            
        Returns:
            Combined DataFrame with all VX data
        """
        if start_date is None:
            start_date = datetime.datetime(2024, 11, 1)
        if end_date is None:
            end_date = datetime.datetime(2025, 4, 1)
            
        combined_data = pd.DataFrame()
        current_date = start_date
        
        while current_date <= end_date:
            file_name = f"VX_{current_date.strftime('%Y-%m-%d')}.csv"
            file_url = urljoin(self.base_url + "VX/", file_name)
            file_path = os.path.join(self.download_folder, file_name)
            
            try:
                print(f"Downloading: {file_url}")
                response = self.get(file_url)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Saved: {file_path}")
                
                # Read CSV and append to combined data
                df = pd.read_csv(file_path)
                df['Source_File'] = file_name
                df['Date'] = current_date
                combined_data = pd.concat([combined_data, df], ignore_index=True)
                
            except requests.exceptions.RequestException as e:
                print(f"Failed to download {file_url}: {e}")
            
            current_date += datetime.timedelta(days=1)
        
        return combined_data
    
    def download_directory_data(self, directories: List[str] = None) -> pd.DataFrame:
        """
        Download data from multiple CBOE directories.
        
        Args:
            directories: List of directory names to download from (default: ["VX"])
            
        Returns:
            Combined DataFrame with all downloaded data
        """
        if directories is None:
            directories = ["VX"]
            
        combined_data = pd.DataFrame()
        
        for directory in directories:
            directory_url = urljoin(self.base_url, directory + "/")
            print(f"Processing directory: {directory}")
            
            # For now, focus on VX data with date range
            if directory == "VX":
                vx_data = self.download_vx_data()
                combined_data = pd.concat([combined_data, vx_data], ignore_index=True)
        
        return combined_data
    
    def get_local_file(self, filename: str) -> Optional[pd.DataFrame]:
        """
        Load a previously downloaded file from local storage.
        
        Args:
            filename: Name of the file to load
            
        Returns:
            DataFrame with file contents or None if file not found
        """
        file_path = os.path.join(self.download_folder, filename)
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
            
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            print(f"Error loading file {filename}: {e}")
            return None
    
    def list_downloaded_files(self) -> List[str]:
        """
        List all downloaded files in the download folder.
        
        Returns:
            List of filenames
        """
        try:
            return [f for f in os.listdir(self.download_folder) if f.endswith('.csv')]
        except FileNotFoundError:
            return []