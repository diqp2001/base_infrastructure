#!/usr/bin/env python3
"""
Test script to verify Portfolio total_portfolio_value fix.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_portfolio_fix():
    """Test that Portfolio has total_portfolio_value property."""
    print("Testing Portfolio total_portfolio_value fix...")
    
    try:
        from domain.entities.finance.portfolio.portfolio import Portfolio
        print("✅ Portfolio imported successfully")
        
        # Create a portfolio instance
        portfolio = Portfolio(name="Test Portfolio")
        print("✅ Portfolio instance created successfully")
        
        # Test that total_portfolio_value property exists
        if hasattr(portfolio, 'total_portfolio_value'):
            print("✅ Portfolio has total_portfolio_value property")
            
            # Test the property value
            value = portfolio.total_portfolio_value
            print(f"✅ total_portfolio_value returns: {value}")
            
            # Test that it's the same as current_value
            if portfolio.total_portfolio_value == portfolio.current_value:
                print("✅ total_portfolio_value equals current_value (as expected)")
                return True
            else:
                print("❌ total_portfolio_value does not equal current_value")
                return False
        else:
            print("❌ Portfolio does not have total_portfolio_value property")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_portfolio_fix()
    if success:
        print("\n🎉 Portfolio fix is working correctly!")
    else:
        print("\n❌ Portfolio fix failed!")
    sys.exit(0 if success else 1)