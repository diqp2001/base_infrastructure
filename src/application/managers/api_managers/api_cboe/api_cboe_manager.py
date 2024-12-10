import datetime
import os
import requests
import pandas as pd
from urllib.parse import urljoin

# Base URL of the webpage containing the CSV files
base_url = "https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/"

# List of subdirectories or files to download
directories = [
    "VX",  # Add more directories if needed
]

# Ensure the downloads folder exists
os.makedirs("downloads", exist_ok=True)

def download_and_consolidate_csv():
    combined_data = pd.DataFrame()  # Initialize an empty DataFrame to hold all data

    for directory in directories:
        # Construct full URL to the directory
        directory_url = urljoin(base_url, directory + "/")
        
        start_date = datetime.datetime(2024, 11, 1)
        end_date = datetime.datetime(2025, 4, 1)
        current_date = start_date
        
        filenames = []
        
        while current_date <= end_date:
            file_name = f"VX_{current_date.strftime('%Y-%m-%d')}.csv"
            file_url = base_url + file_name
            filenames.append(file_name)
        for filename in filenames:
            file_url = urljoin(directory_url, filename)
            file_path = os.path.join("downloads", filename)
            
            # Download the file
            print(f"Downloading: {file_url}")
            try:
                response = requests.get(file_url)
                response.raise_for_status()  # Ensure the request was successful
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Saved: {file_path}")
                
                # Read CSV into DataFrame and append to the combined DataFrame
                df = pd.read_csv(file_path)
                df['Source_File'] = filename  # Add a column to track the source file
                combined_data = pd.concat([combined_data, df], ignore_index=True)
            
            except requests.exceptions.RequestException as e:
                print(f"Failed to download {file_url}: {e}")
    
    return combined_data



