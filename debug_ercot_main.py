#!/usr/bin/env python3
"""
ERCOT Debug Main Script

This script uses the debug service to replicate exact Postman requests
and identify issues with the ERCOT API authentication and calls.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

from src.application.services.api_service.ercot_service.ercot_debug_service import (
    ErcotDebugService, ERCOTDebugCredentials
)


def main():
    """Main debug function"""
    print("🔬 ERCOT API Debug Script")
    print("=" * 50)
    
    # For now, create credentials directly (user will replace with actual values)
    print("\n⚠️  USING TEMPLATE CREDENTIALS - REPLACE WITH ACTUAL VALUES")
    print("The credentials template shows the expected format.")
    print("You'll need to:")
    print("1. Copy ercot_credentials_template.json to outside the repository")
    print("2. Fill in your actual password and subscription_key")
    print("3. Update this script to load from your credentials file")
    print()
    
    # Template credentials (will fail but shows the structure)
    template_creds = ERCOTDebugCredentials(
        username="philippe.di.quinzio@usherbrooke.ca",
        password="***",  # Replace with actual password
        subscription_key="***"  # Replace with actual subscription key
    )
    
    # Create debug service
    debug_service = ErcotDebugService(template_creds)
    
    print("📋 Credential Summary:")
    print(f"  Username: {template_creds.username}")
    print(f"  Password: {'***' if template_creds.password != '***' else 'TEMPLATE VALUE - NEEDS REPLACEMENT'}")
    print(f"  Subscription Key: {'***' if template_creds.subscription_key != '***' else 'TEMPLATE VALUE - NEEDS REPLACEMENT'}")
    print()
    
    if template_creds.password == "***" or template_creds.subscription_key == "***":
        print("❌ Cannot proceed with template credentials.")
        print("Please update this script with actual credentials or load from external file.")
        print("\nExample of loading from file:")
        print("  creds = ERCOTDebugCredentials.from_file('/path/to/your/ercot_credentials.json')")
        return
    
    # Test 1: Token acquisition
    print("🔐 TEST 1: Token Acquisition")
    print("-" * 30)
    token_result = debug_service.get_token_postman_style()
    
    if token_result.get('success'):
        print("✅ Token acquisition successful!")
    else:
        print("❌ Token acquisition failed!")
        print(f"Error: {token_result.get('error', 'Unknown error')}")
        return
    
    # Test 2: Basic API call
    print("\n🌐 TEST 2: Basic API Call")
    print("-" * 30)
    api_result = debug_service.call_api_postman_style()
    
    if api_result.get('success'):
        print("✅ API call successful!")
    else:
        print("❌ API call failed!")
        print(f"Error: {api_result.get('error', 'Unknown error')}")
        print(f"Status: {api_result.get('status_code', 'Unknown')}")
    
    # Test 3: Full workflow with specific endpoint
    print("\n🚀 TEST 3: Full Workflow with Energy Demand Curves")
    print("-" * 50)
    endpoint = "/np3-907-ex/2d_agg_edc?deliveryDateFrom=2024-12-05&deliveryDateTo=2024-12-06&page=1&size=10"
    workflow_result = debug_service.full_debug_workflow(endpoint)
    
    if workflow_result.get('success'):
        print("✅ Full workflow successful!")
    else:
        print("❌ Full workflow failed!")
        print(f"Failed at step: {workflow_result.get('step_failed', 'Unknown')}")
    
    # Test 4: Comparison with existing service
    print("\n🔍 TEST 4: Comparison with Existing Service")
    print("-" * 40)
    try:
        comparison = debug_service.compare_with_existing_service()
        print(f"Debug service success: {comparison['debug_service']['success']}")
        print(f"Existing service success: {comparison['existing_service']['success']}")
        
        if comparison['debug_service']['success'] != comparison['existing_service']['success']:
            print("⚠️  Services have different success rates - this indicates the issue!")
        else:
            print("✅ Both services have same success rate")
            
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
    
    print("\n🏁 Debug complete!")
    print("Check the output above to identify differences from your working Postman setup.")


if __name__ == "__main__":
    main()