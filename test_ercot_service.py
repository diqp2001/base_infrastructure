#!/usr/bin/env python3
"""
Quick test script for ERCOT Public API Service
"""

import sys
import os
import datetime

# Add src to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.application.services.ercot_service import ErcotPublicApiService

def test_ercot_service():
    print("=== ERCOT Public API Service Test ===\n")
    
    # Initialize service
    print("1. Initializing ErcotPublicApiService...")
    service = ErcotPublicApiService()
    print("✓ Service initialized successfully\n")
    
    # Check API health
    print("2. Checking API health...")
    health = service.check_api_health()
    print(f"   Status: {health['status']}")
    print(f"   API Responsive: {health['api_responsive']}")
    print(f"   Base URL: {health['base_url']}")
    if 'error' in health:
        print(f"   Error: {health['error']}")
    print()
    
    # Get settlement points info
    print("3. Getting settlement points information...")
    points = service.get_settlement_points_info()
    print(f"   Major Hubs: {points['hubs']}")
    print(f"   Load Zones: {points['load_zones'][:3]}...")  # Show first 3
    print()
    
    # Get date range info
    print("4. Getting recommended date ranges...")
    date_info = service.get_date_range_info()
    print(f"   Recommended start date: {date_info['recommended_start_date']}")
    print(f"   Recommended end date: {date_info['recommended_end_date']}")
    print(f"   Note: {date_info['note']}")
    print()
    
    # Test day-ahead prices (small date range to avoid too much data)
    print("5. Testing day-ahead prices (last 2 days)...")
    try:
        start_date = date_info['recommended_end_date']  # Yesterday
        end_date = date_info['recommended_end_date']    # Yesterday
        
        dam_response = service.get_day_ahead_prices(
            start_date=start_date,
            end_date=end_date,
            settlement_point='HB_HOUSTON',
            page_size=5  # Limit to 5 records for testing
        )
        
        if dam_response and 'data' in dam_response:
            print(f"   ✓ Retrieved {len(dam_response['data'])} DAM price records")
            if dam_response['data']:
                sample = dam_response['data'][0]
                print(f"   Sample: {sample.get('settlementPoint', 'N/A')} - ${sample.get('settlementPointPrice', 'N/A')}/MWh")
        else:
            print("   ✗ No DAM data retrieved (may be normal for recent dates)")
    except Exception as e:
        print(f"   ✗ DAM test failed: {e}")
    print()
    
    # Test physical prices
    print("6. Testing physical/RTM prices...")
    try:
        rtm_response = service.get_physical_prices(
            start_date=start_date,
            end_date=end_date,
            settlement_point='HB_HOUSTON',
            page_size=5  # Limit to 5 records for testing
        )
        
        if rtm_response and 'data' in rtm_response:
            print(f"   ✓ Retrieved {len(rtm_response['data'])} RTM price records")
            if rtm_response['data']:
                sample = rtm_response['data'][0]
                print(f"   Sample: {sample.get('settlementPoint', 'N/A')} - ${sample.get('settlementPointPrice', 'N/A')}/MWh")
        else:
            print("   ✗ No RTM data retrieved (may be normal for recent dates)")
    except Exception as e:
        print(f"   ✗ RTM test failed: {e}")
    print()
    
    print("=== Test Complete ===")
    print("\nNote: Data may not be available for very recent dates.")
    print("ERCOT typically has a 1-2 hour delay for real-time data.")

if __name__ == "__main__":
    test_ercot_service()