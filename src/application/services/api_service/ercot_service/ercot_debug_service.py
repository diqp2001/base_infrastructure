"""
ERCOT API Debug Service

This module contains debugging functions that exactly replicate Postman requests
to help identify differences between working Postman calls and Python implementation.

Created to debug authentication and API call issues.
"""

import requests
import json
import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ERCOTDebugCredentials:
    """ERCOT credentials for debugging - matches Postman setup"""
    username: str
    password: str
    subscription_key: str
    
    @classmethod
    def from_file(cls, filepath: str) -> 'ERCOTDebugCredentials':
        """Load credentials from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(
            username=data['username'],
            password=data['password'], 
            subscription_key=data['subscription_key']
        )


class ErcotDebugService:
    """
    Debug service that exactly replicates the Postman workflow.
    
    This service is designed to help identify what's different between
    the working Postman requests and the Python implementation.
    """
    
    def __init__(self, credentials: ERCOTDebugCredentials):
        """Initialize debug service with credentials"""
        self.credentials = credentials
        self.access_token = None
        self.session = requests.Session()
        
    def get_token_postman_style(self) -> Dict[str, Any]:
        """
        Get token using exact Postman URL structure and parameters.
        
        This function replicates the exact POST request that works in Postman:
        https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token
        
        Returns:
            Dictionary containing the full token response or error info
        """
        print("🔐 Getting token using Postman-style request...")
        
        # Exact URL from Postman
        auth_url = (
            "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
            "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
        )
        
        # Build URL with parameters exactly like Postman does
        url_with_params = (
            f"{auth_url}?"
            f"username={self.credentials.username}&"
            f"password={self.credentials.password}&"
            f"grant_type=password&"
            f"scope=openid+fec253ea-0d06-4272-a5e6-b478baeecd70+offline_access&"
            f"client_id=fec253ea-0d06-4272-a5e6-b478baeecd70&"
            f"response_type=id_token"
        )
        
        print(f"📍 Request URL: {auth_url}")
        print(f"📍 Parameters in URL: {url_with_params.split('?')[1] if '?' in url_with_params else 'None'}")
        
        try:
            # Make POST request exactly like Postman
            print("📡 Sending POST request...")
            response = requests.post(url_with_params, timeout=30)
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                print("✅ Successfully parsed JSON response")
                
                # Store access token if present
                if 'access_token' in response_data:
                    self.access_token = response_data['access_token']
                    print("✅ Access token retrieved and stored")
                else:
                    print("⚠️ No access_token in response")
                
                # Print key fields
                for key in ['access_token', 'token_type', 'expires_in', 'refresh_token', 'id_token']:
                    if key in response_data:
                        value = response_data[key]
                        if key in ['access_token', 'refresh_token', 'id_token']:
                            # Truncate long tokens for display
                            display_value = f"{value[:50]}..." if len(value) > 50 else value
                        else:
                            display_value = value
                        print(f"📋 {key}: {display_value}")
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'data': response_data,
                    'has_access_token': 'access_token' in response_data
                }
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"📄 Raw response: {response.text}")
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': f"JSON decode error: {e}",
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {
                'success': False,
                'error': f"Request error: {e}"
            }
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {e}"
            }
    
    def call_api_postman_style(self, endpoint: str = "") -> Dict[str, Any]:
        """
        Call ERCOT API using exact Postman headers and authentication.
        
        Args:
            endpoint: API endpoint to call (optional, defaults to base reports endpoint)
            
        Returns:
            Dictionary containing API response or error info
        """
        if not self.access_token:
            print("⚠️ No access token available. Call get_token_postman_style() first.")
            return {
                'success': False,
                'error': 'No access token available'
            }
            
        print("🌐 Calling ERCOT API using Postman-style request...")
        
        # Base URL
        base_url = "https://api.ercot.com/api/public-reports"
        full_url = f"{base_url}{endpoint}" if endpoint else base_url
        
        # Headers exactly like Postman
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Ocp-Apim-Subscription-Key': self.credentials.subscription_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'PostmanRuntime/7.36.0'  # Mimicking Postman
        }
        
        print(f"📍 Request URL: {full_url}")
        print("📋 Headers:")
        for key, value in headers.items():
            if key == 'Authorization':
                print(f"  {key}: Bearer {value[7:57]}...")  # Show first 50 chars of token
            elif key == 'Ocp-Apim-Subscription-Key':
                print(f"  {key}: {value[:10]}...")  # Show first 10 chars
            else:
                print(f"  {key}: {value}")
        
        try:
            print("📡 Sending GET request...")
            response = requests.get(full_url, headers=headers, timeout=30)
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")
            
            # Try to parse response
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    response_data = response.json()
                    print("✅ Successfully parsed JSON response")
                    print(f"📋 Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                    
                    return {
                        'success': response.status_code == 200,
                        'status_code': response.status_code,
                        'data': response_data,
                        'content_type': response.headers.get('content-type')
                    }
                else:
                    print(f"📄 Non-JSON response: {response.text}")
                    return {
                        'success': response.status_code == 200,
                        'status_code': response.status_code,
                        'raw_response': response.text,
                        'content_type': response.headers.get('content-type')
                    }
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"📄 Raw response: {response.text}")
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': f"JSON decode error: {e}",
                    'raw_response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return {
                'success': False,
                'error': f"Request error: {e}"
            }
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {e}"
            }
    
    def full_debug_workflow(self, api_endpoint: str = "") -> Dict[str, Any]:
        """
        Run the complete debug workflow: get token + call API
        
        Args:
            api_endpoint: Optional API endpoint to test (e.g., "/np3-907-ex/2d_agg_edc")
            
        Returns:
            Dictionary with complete workflow results
        """
        print("🚀 Starting full debug workflow...")
        print("=" * 60)
        
        # Step 1: Get token
        print("\n📍 STEP 1: Getting authentication token...")
        token_result = self.get_token_postman_style()
        
        if not token_result.get('success'):
            return {
                'success': False,
                'step_failed': 'authentication',
                'token_result': token_result,
                'api_result': None
            }
        
        print("\n✅ Token acquisition successful!")
        
        # Step 2: Call API
        print("\n📍 STEP 2: Calling ERCOT API...")
        api_result = self.call_api_postman_style(api_endpoint)
        
        print("\n🏁 Debug workflow complete!")
        print("=" * 60)
        
        return {
            'success': token_result.get('success') and api_result.get('success'),
            'token_result': token_result,
            'api_result': api_result,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
    def compare_with_existing_service(self) -> Dict[str, Any]:
        """
        Compare debug results with existing authenticated service
        
        Returns:
            Comparison results
        """
        print("🔍 Comparing debug service with existing implementation...")
        
        # Import existing service
        from .ercot_authenticated_api_service import ErcotAuthenticatedApiService, ERCOTCredentials
        
        # Create existing service instance
        existing_creds = ERCOTCredentials(
            username=self.credentials.username,
            password=self.credentials.password,
            subscription_key=self.credentials.subscription_key
        )
        existing_service = ErcotAuthenticatedApiService(existing_creds)
        
        # Test both
        debug_result = self.get_token_postman_style()
        existing_result = existing_service._get_auth_token()
        
        return {
            'debug_service': {
                'success': debug_result.get('success', False),
                'has_token': self.access_token is not None
            },
            'existing_service': {
                'success': existing_result,
                'has_token': existing_service._access_token is not None
            },
            'timestamp': datetime.datetime.now().isoformat()
        }