#!/usr/bin/env python3
"""
Simple test script for the new Treasury 10-Year futures function.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.services.api_service.ibkr_service.comprehensive_market_data_examples import ComprehensiveIBMarketDataExamples

def test_treasury_function():
    """Test the new Treasury 10-Year futures function."""
    print("🧪 Testing US Treasury 10-Year Futures Historical Data Function")
    print("=" * 60)
    
    # Create instance
    examples = ComprehensiveIBMarketDataExamples()
    
    # Test connection (mock - won't actually connect in test)
    examples.connected = False  # Simulate no connection for safety
    
    # Try to run the function (should handle no connection gracefully)
    try:
        examples.example_TR_10_YR_future_historical_data()
        print("✅ Function executed successfully (no connection test)")
    except Exception as e:
        print(f"❌ Function failed: {e}")
        return False
    
    print("\n✅ Test completed successfully!")
    print("\n📝 Function Details:")
    print("   - Symbol: ZN (10-Year U.S. Treasury Note)")
    print("   - Exchange: CBOT")
    print("   - Security Type: FUT (Futures)")
    print("   - Duration: 6 months of historical data")
    print("   - Bar Size: 5 minutes")
    print("   - Currency: USD")
    
    return True

if __name__ == "__main__":
    test_treasury_function()