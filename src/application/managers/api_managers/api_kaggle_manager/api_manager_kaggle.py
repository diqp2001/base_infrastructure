# src/application/managers/api_managers/api_kaggle_manager/api_manager_kaggle.py

from src.application.managers.api_managers.api_manager import APIManager
import os
import kaggle

class KaggleAPIManager(APIManager):
    """
    A class to manage Kaggle API interactions, including downloading datasets.
    """

    def __init__(self, api_url: str = "https://www.kaggle.com", kaggle_json_path: str = None):
        super().__init__(api_url)
        self.kaggle_json_path = kaggle_json_path or os.path.expanduser('~/.kaggle/kaggle.json')

    def authenticate(self):
        """
        Authenticate using the Kaggle API credentials stored in kaggle.json.
        """
        os.environ['KAGGLE_CONFIG_DIR'] = self.kaggle_json_path
        kaggle.api.authenticate()
        print("Authenticated with Kaggle API.")

    def download_dataset(self, dataset_name: str, download_path: str = './data'):
        """
        Download a dataset from Kaggle and return the local file path.
        :param dataset_name: The dataset identifier (e.g., 'zillow/zecon').
        :param download_path: The folder to download the dataset to.
        :return: The local file path of the downloaded dataset.
        """
        self.authenticate()
        print(f"Downloading dataset {dataset_name}...")
        kaggle.api.dataset_download_files(dataset_name, path=download_path, unzip=True)
        dataset_file_path = os.path.join(download_path, dataset_name.split('/')[1] + '.csv')
        print(f"Dataset {dataset_name} downloaded to {dataset_file_path}.")
        return dataset_file_path
