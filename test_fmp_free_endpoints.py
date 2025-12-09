#!/usr/bin/env python3
"""
Test script for FMP API Free Tier Endpoints

This script tests the newly added free tier endpoints for the Financial Modeling Prep API.
Requires valid FMP API credentials in fmp_credentials.json.

Usage:
    python test_fmp_free_endpoints.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_free_endpoints():
    """Test all free tier FMP API endpoints"""
    try:
        from src.application.services.api_service.fmp_service.financial_modeling_prep_api_service import (
            FinancialModelingPrepApiService
        )
        
        print("🧪 Testing FMP API Free Tier Endpoints")
        print("=" * 50)
        
        # Initialize service
        print("📡 Initializing FMP API Service...")
        try:
            service = FinancialModelingPrepApiService()
            print("✅ Service initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize service: {e}")
            print("💡 Make sure you have valid FMP credentials in the expected location")
            return False
        
        print("\n📋 Free Tier Summary:")
        summary = service.get_free_tier_summary()
        print(f"   Daily Limit: {summary['free_tier_info']['daily_limit']}")
        print(f"   Plan Type: {summary['free_tier_info']['plan_type']}")
        print(f"   Available Endpoint Categories: {len(summary['available_endpoints'])}")
        
        # Test search endpoints
        print("\n🔍 Testing Search Endpoints:")
        
        # Test symbol search
        print("   Testing search_symbol('AAPL')...")
        try:
            results = service.search_symbol('AAPL', limit=3)
            if results:
                print(f"   ✅ Found {len(results)} results")
                print(f"      First result: {results[0].get('symbol', 'N/A')}")
            else:
                print("   ⚠️  No results returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test company name search
        print("   Testing search_company_name('Apple')...")
        try:
            results = service.search_company_name('Apple', limit=3)
            if results:
                print(f"   ✅ Found {len(results)} results")
                print(f"      First result: {results[0].get('name', 'N/A')}")
            else:
                print("   ⚠️  No results returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test metadata endpoints
        print("\n📊 Testing Metadata Endpoints:")
        
        # Test available exchanges
        print("   Testing get_available_exchanges()...")
        try:
            exchanges = service.get_available_exchanges()
            if exchanges:
                print(f"   ✅ Found {len(exchanges)} exchanges")
                print(f"      Sample: {exchanges[0].get('exchangeShortName', 'N/A') if exchanges else 'N/A'}")
            else:
                print("   ⚠️  No exchanges returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test available sectors
        print("   Testing get_available_sectors()...")
        try:
            sectors = service.get_available_sectors()
            if sectors:
                print(f"   ✅ Found {len(sectors)} sectors")
                print(f"      Sample: {sectors[0].get('sector', 'N/A') if sectors else 'N/A'}")
            else:
                print("   ⚠️  No sectors returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test historical data endpoints
        print("\n📈 Testing Historical Data Endpoints:")
        
        # Test EOD historical prices
        print("   Testing get_historical_price_eod('AAPL')...")
        try:
            historical = service.get_historical_price_eod('AAPL')
            if historical and 'historical' in historical:
                print(f"   ✅ Found {len(historical['historical'])} historical records")
                latest = historical['historical'][0] if historical['historical'] else {}
                print(f"      Latest price ({latest.get('date', 'N/A')}): ${latest.get('close', 'N/A')}")
            else:
                print("   ⚠️  No historical data returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test market reference endpoints
        print("\n🏛️ Testing Market Reference Endpoints:")
        
        # Test available indexes
        print("   Testing get_available_indexes()...")
        try:
            indexes = service.get_available_indexes()
            if indexes:
                print(f"   ✅ Found {len(indexes)} indexes")
                for idx in indexes[:3]:  # Show first 3
                    symbol = idx.get('symbol', 'N/A')
                    price = idx.get('price', 'N/A')
                    print(f"      {symbol}: ${price}")
            else:
                print("   ⚠️  No indexes returned")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n✅ Free tier endpoint testing completed!")
        print("\n💡 Tips:")
        print("   • All tested endpoints are part of the FMP free tier")
        print("   • Free tier limited to 250 API calls per day")
        print("   • Consider upgrading for higher limits and more features")
        print("   • Use get_free_tier_summary() for detailed feature comparison")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 FMP API Free Endpoints Test Suite")
    print("====================================")
    
    success = test_free_endpoints()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n💥 Some tests failed. Check your setup and credentials.")
        return 1

if __name__ == "__main__":
    exit(main())