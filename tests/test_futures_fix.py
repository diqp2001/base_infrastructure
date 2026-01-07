#!/usr/bin/env python3
"""
Test script to validate the futures historical data fix.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.services.api_service.ibkr_service.comprehensive_market_data_examples import ComprehensiveIBMarketDataExamples

def test_futures_historical_data():
    """Test the futures historical data functionality."""
    print("🧪 Testing ES futures historical data fix...")
    
    # Create examples instance
    examples = ComprehensiveIBMarketDataExamples()
    
    try:
        # Connect to IB
        if not examples.ib_broker.connect():
            print("❌ Failed to connect to Interactive Brokers")
            return False
            
        print("✅ Connected to Interactive Brokers")
        
        # Test the specific method that was failing
        print("\n📊 Testing example_sp500_future_historical_data()...")
        examples.example_sp500_future_historical_data()
        
        print("\n✅ Test completed - check logs above for detailed results")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            examples.ib_broker.disconnect()
            print("🔌 Disconnected from IB")
        except:
            pass

if __name__ == "__main__":
    success = test_futures_historical_data()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed!")
    sys.exit(0 if success else 1)