# src/application/services/api_service.py
import requests
from typing import Dict, Any, Optional
import json

class ApiService:
    """
    A service class for managing API connections and requests.
    Can be extended to handle specific API integrations (like Kaggle, REST APIs, etc.).
    """

    def __init__(self, api_url: str, headers: Dict[str, str] = None, timeout: int = 30):
        """
        Initialize the ApiService.
        :param api_url: Base URL for the API.
        :param headers: Optional default headers for API requests.
        :param timeout: Request timeout in seconds.
        """
        self.api_url = api_url.rstrip('/')  # Remove trailing slash
        self.headers = headers or {}
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def set_authentication(self, auth_type: str, **kwargs):
        """
        Set authentication for API requests.
        :param auth_type: Type of authentication ('bearer', 'basic', 'api_key').
        :param kwargs: Authentication parameters.
        """
        if auth_type == 'bearer':
            token = kwargs.get('token')
            if token:
                self.session.headers['Authorization'] = f'Bearer {token}'
        elif auth_type == 'basic':
            username = kwargs.get('username')
            password = kwargs.get('password')
            if username and password:
                self.session.auth = (username, password)
        elif auth_type == 'api_key':
            api_key = kwargs.get('api_key')
            key_header = kwargs.get('key_header', 'X-API-Key')
            if api_key:
                self.session.headers[key_header] = api_key
        else:
            raise ValueError(f"Unsupported authentication type: {auth_type}")

    def fetch_data(self, endpoint: str, params: Dict[str, Any] = None, method: str = 'GET') -> Optional[Dict[str, Any]]:
        """
        Fetch data from the given API endpoint.
        :param endpoint: The API endpoint to query.
        :param params: Optional parameters for the request.
        :param method: HTTP method ('GET', 'POST', 'PUT', 'DELETE').
        :return: The response data as a dictionary or None if failed.
        """
        try:
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=params, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=params, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If not JSON, return text content
                return {'content': response.text, 'status_code': response.status_code}
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {endpoint}: {e}")
            return None

    def post_data(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Post data to the given API endpoint.
        :param endpoint: The API endpoint to post to.
        :param data: Data to post.
        :return: The response data as a dictionary or None if failed.
        """
        return self.fetch_data(endpoint, params=data, method='POST')

    def put_data(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Put data to the given API endpoint.
        :param endpoint: The API endpoint to put to.
        :param data: Data to put.
        :return: The response data as a dictionary or None if failed.
        """
        return self.fetch_data(endpoint, params=data, method='PUT')

    def delete_resource(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Delete a resource at the given API endpoint.
        :param endpoint: The API endpoint to delete from.
        :param params: Optional parameters for the request.
        :return: The response data as a dictionary or None if failed.
        """
        return self.fetch_data(endpoint, params=params, method='DELETE')

    def upload_file(self, endpoint: str, file_path: str, file_field: str = 'file', additional_data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Upload a file to the API endpoint.
        :param endpoint: The API endpoint to upload to.
        :param file_path: Path to the file to upload.
        :param file_field: Name of the file field in the form.
        :param additional_data: Additional form data to include.
        :return: The response data as a dictionary or None if failed.
        """
        try:
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            with open(file_path, 'rb') as file:
                files = {file_field: file}
                data = additional_data or {}
                
                response = self.session.post(url, files=files, data=data, timeout=self.timeout)
                response.raise_for_status()
                
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'content': response.text, 'status_code': response.status_code}
                    
        except (requests.exceptions.RequestException, FileNotFoundError) as e:
            print(f"Error uploading file {file_path} to {endpoint}: {e}")
            return None

    def download_file(self, endpoint: str, save_path: str, params: Dict[str, Any] = None) -> bool:
        """
        Download a file from the API endpoint.
        :param endpoint: The API endpoint to download from.
        :param save_path: Path to save the downloaded file.
        :param params: Optional parameters for the request.
        :return: True if successful, False otherwise.
        """
        try:
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            response = self.session.get(url, params=params, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            
            print(f"File downloaded successfully to {save_path}")
            return True
            
        except (requests.exceptions.RequestException, IOError) as e:
            print(f"Error downloading file from {endpoint}: {e}")
            return False

    def paginated_fetch(self, endpoint: str, params: Dict[str, Any] = None, page_param: str = 'page', 
                       per_page_param: str = 'per_page', max_pages: int = None) -> List[Dict[str, Any]]:
        """
        Fetch data with pagination support.
        :param endpoint: The API endpoint to query.
        :param params: Optional parameters for the request.
        :param page_param: Name of the page parameter.
        :param per_page_param: Name of the per_page parameter.
        :param max_pages: Maximum number of pages to fetch (None for unlimited).
        :return: List of all fetched data.
        """
        all_data = []
        page = 1
        
        while max_pages is None or page <= max_pages:
            page_params = (params or {}).copy()
            page_params[page_param] = page
            
            response = self.fetch_data(endpoint, params=page_params)
            
            if not response:
                break
                
            # Assume data is in a 'data' field or directly as a list
            page_data = response.get('data', response)
            
            if isinstance(page_data, list):
                if not page_data:  # Empty page, stop pagination
                    break
                all_data.extend(page_data)
            else:
                all_data.append(page_data)
            
            # Check if there are more pages (common pagination indicators)
            if not response.get('has_next', True) or not response.get('next'):
                break
                
            page += 1
        
        return all_data

    def check_api_status(self) -> bool:
        """
        Check if the API is accessible.
        :return: True if API is accessible, False otherwise.
        """
        try:
            # Try to make a simple request to the base URL
            response = self.session.get(self.api_url, timeout=self.timeout)
            return response.status_code < 500  # Consider 4xx as accessible but client error
        except requests.exceptions.RequestException:
            return False

    def set_timeout(self, timeout: int):
        """
        Set the request timeout.
        :param timeout: Timeout in seconds.
        """
        self.timeout = timeout

    def add_header(self, key: str, value: str):
        """
        Add a header to all requests.
        :param key: Header name.
        :param value: Header value.
        """
        self.session.headers[key] = value

    def remove_header(self, key: str):
        """
        Remove a header from requests.
        :param key: Header name to remove.
        """
        if key in self.session.headers:
            del self.session.headers[key]

    def close(self):
        """
        Close the session.
        """
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()