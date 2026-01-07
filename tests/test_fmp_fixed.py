#!/usr/bin/env python3
"""
Test script for Fixed FMP API Service

Tests the updated stable endpoints to ensure they work properly with the free tier.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.services.api_service.fmp_service.financial_modeling_prep_api_service import FinancialModelingPrepApiService

def test_stable_endpoints():
    """Test all stable/free tier endpoints"""
    
    try:
        # Initialize service (will load credentials from JSON file)
        service = FinancialModelingPrepApiService()
        print("✅ FMP API Service initialized successfully")
        
        # Test search endpoints
        print("\n🔍 Testing Search Endpoints:")
        
        # Search by symbol
        try:
            results = service.search_symbol('AAPL')
            if results:
                print(f"✅ search_symbol('AAPL') - Found {len(results)} results")
            else:
                print("❌ search_symbol('AAPL') - No results")
        except Exception as e:
            print(f"❌ search_symbol error: {e}")
        
        # Search by company name
        try:
            results = service.search_company_name('Apple')
            if results:
                print(f"✅ search_company_name('Apple') - Found {len(results)} results")
            else:
                print("❌ search_company_name('Apple') - No results")
        except Exception as e:
            print(f"❌ search_company_name error: {e}")
        
        # Search by CIK
        try:
            results = service.search_cik('320193')
            if results:
                print(f"✅ search_cik('320193') - Found results")
            else:
                print("❌ search_cik('320193') - No results")
        except Exception as e:
            print(f"❌ search_cik error: {e}")
        
        # Test new endpoints
        print("\n🆕 Testing New Stable Endpoints:")
        
        # Search by CUSIP
        try:
            results = service.search_cusip('037833100')
            if results:
                print(f"✅ search_cusip('037833100') - Found results")
            else:
                print("❌ search_cusip('037833100') - No results")
        except Exception as e:
            print(f"❌ search_cusip error: {e}")
        
        # Search by ISIN
        try:
            results = service.search_isin('US0378331005')
            if results:
                print(f"✅ search_isin('US0378331005') - Found results")
            else:
                print("❌ search_isin('US0378331005') - No results")
        except Exception as e:
            print(f"❌ search_isin error: {e}")
        
        # Company screener
        try:
            results = service.company_screener(10)
            if results:
                print(f"✅ company_screener(10) - Found {len(results)} results")
            else:
                print("❌ company_screener(10) - No results")
        except Exception as e:
            print(f"❌ company_screener error: {e}")
        
        # Exchange variants
        try:
            results = service.search_exchange_variants('AAPL')
            if results:
                print(f"✅ search_exchange_variants('AAPL') - Found {len(results)} variants")
            else:
                print("❌ search_exchange_variants('AAPL') - No results")
        except Exception as e:
            print(f"❌ search_exchange_variants error: {e}")
        
        # Test metadata endpoints
        print("\n📊 Testing Metadata Endpoints:")
        
        # Get CIK list
        try:
            results = service.get_cik_list()
            if results:
                print(f"✅ get_cik_list() - Found {len(results)} CIK entries")
            else:
                print("❌ get_cik_list() - No results")
        except Exception as e:
            print(f"❌ get_cik_list error: {e}")
        
        # Get available exchanges
        try:
            results = service.get_available_exchanges()
            if results:
                print(f"✅ get_available_exchanges() - Found {len(results)} exchanges")
            else:
                print("❌ get_available_exchanges() - No results")
        except Exception as e:
            print(f"❌ get_available_exchanges error: {e}")
        
        # Get available sectors
        try:
            results = service.get_available_sectors()
            if results:
                print(f"✅ get_available_sectors() - Found {len(results)} sectors")
            else:
                print("❌ get_available_sectors() - No results")
        except Exception as e:
            print(f"❌ get_available_sectors error: {e}")
        
        # Get available countries
        try:
            results = service.get_available_countries()
            if results:
                print(f"✅ get_available_countries() - Found {len(results)} countries")
            else:
                print("❌ get_available_countries() - No results")
        except Exception as e:
            print(f"❌ get_available_countries error: {e}")
        
        print("\n📋 Free Tier Summary:")
        summary = service.get_free_tier_summary()
        print(f"Daily Limit: {summary['free_tier_info']['daily_limit']}")
        print(f"Search Endpoints: {len(summary['available_endpoints']['search'])}")
        print(f"Metadata Endpoints: {len(summary['available_endpoints']['metadata'])}")
        
    except Exception as e:
        print(f"❌ Error initializing service: {e}")
        print("Make sure FPM_credentials.json file exists with your API key")

if __name__ == "__main__":
    print("🧪 Testing Fixed FMP API Service with Stable Endpoints")
    print("=" * 60)
    test_stable_endpoints()
    print("\n" + "=" * 60)
    print("✅ Test completed!")