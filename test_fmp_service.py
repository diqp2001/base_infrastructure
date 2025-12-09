"""
Test script for Financial Modeling Prep API Service

This script tests the basic functionality of the FMP API service implementation.
Run this after setting up your credentials to verify the service works correctly.
"""

import sys
import os

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from application.services.api_service.financial_modeling_prep_api_service import (
    FinancialModelingPrepApiService, 
    FMPCredentials,
    FMPRateLimit
)


def test_fmp_service():
    """Test basic FMP API service functionality"""
    
    print("Testing Financial Modeling Prep API Service")
    print("=" * 50)
    
    try:
        # Test credential loading from environment (if available)
        print("1. Testing credential loading...")
        try:
            credentials = FMPCredentials.from_env()
            if credentials.api_key:
                print("✓ Credentials loaded from environment")
            else:
                print("ℹ No API key in environment variables")
                # Create dummy credentials for structure testing
                credentials = FMPCredentials(api_key="demo")
                print("ℹ Using demo credentials for structure testing")
        except Exception as e:
            print(f"✗ Error loading credentials: {e}")
            return False
        
        # Test service initialization
        print("\n2. Testing service initialization...")
        try:
            rate_limit = FMPRateLimit(max_requests_per_minute=60, request_delay=1.0)
            service = FinancialModelingPrepApiService(credentials, rate_limit=rate_limit)
            print("✓ Service initialized successfully")
            print(f"  - Base URL: {service.BASE_URL}")
            print(f"  - Rate limit: {service.rate_limit.max_requests_per_minute} requests/minute")
        except Exception as e:
            print(f"✗ Error initializing service: {e}")
            return False
        
        # Test utility methods
        print("\n3. Testing utility methods...")
        try:
            exchanges = service.get_supported_exchanges()
            periods = service.get_supported_periods()
            indices = service.get_major_indices()
            
            print(f"✓ Supported exchanges: {exchanges}")
            print(f"✓ Supported periods: {periods}")
            print(f"✓ Major indices: {indices}")
        except Exception as e:
            print(f"✗ Error testing utility methods: {e}")
            return False
        
        # Test API health check (only if we have a real API key)
        print("\n4. Testing API health check...")
        if credentials.api_key and credentials.api_key != "demo":
            try:
                health = service.check_api_health()
                print(f"✓ API Health Check: {health['status']}")
                print(f"  - Responsive: {health['api_responsive']}")
                print(f"  - Has API key: {health['has_api_key']}")
                if health['status'] == 'healthy':
                    print("✓ API is accessible and working")
                else:
                    print(f"⚠ API health check failed: {health.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"✗ Error testing API health: {e}")
        else:
            print("ℹ Skipping API health check (no valid API key)")
        
        # Test credential template loading
        print("\n5. Testing credential template structure...")
        try:
            template_path = "src/application/services/api_service/fmp_credentials_template.json"
            if os.path.exists(template_path):
                print("✓ Credential template file exists")
                print(f"  - Location: {template_path}")
                with open(template_path, 'r') as f:
                    import json
                    template = json.load(f)
                    if 'api_key' in template:
                        print("✓ Template has correct structure")
                    else:
                        print("✗ Template missing api_key field")
            else:
                print(f"✗ Template file not found: {template_path}")
        except Exception as e:
            print(f"✗ Error testing credential template: {e}")
        
        print("\n" + "=" * 50)
        print("✓ FMP API Service test completed successfully!")
        print("\nNext steps:")
        print("1. Copy fmp_credentials_template.json to a secure location")
        print("2. Add your actual FMP API key to the copied file")
        print("3. Test with real API calls using your credentials")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Unexpected error during testing: {e}")
        return False


if __name__ == "__main__":
    success = test_fmp_service()
    sys.exit(0 if success else 1)