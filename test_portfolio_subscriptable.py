#!/usr/bin/env python3
"""Test script to verify Portfolio subscriptable functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from decimal import Decimal
from src.domain.entities.finance.portfolio.portfolio import Portfolio, SecurityHoldings
from src.domain.entities.finance.financial_assets.security import Symbol, SecurityType

def test_portfolio_subscriptable():
    """Test that Portfolio supports subscript access."""
    print("Testing Portfolio subscriptable functionality...")
    
    # Create a portfolio
    portfolio = Portfolio(name="Test Portfolio")
    
    # Create a Symbol for testing
    symbol = Symbol(ticker="AAPL", exchange="NASDAQ", security_type=SecurityType.EQUITY)
    
    # Create a holding
    holding = SecurityHoldings(
        symbol=symbol,
        quantity=Decimal('100'),
        average_cost=Decimal('150.00'),
        market_value=Decimal('15000.00')
    )
    
    # Add holding to portfolio
    portfolio.add_security_holding(holding)
    
    # Test subscript access with Symbol object
    retrieved_holding_by_symbol = portfolio[symbol]
    print(f"Retrieved holding by Symbol: {retrieved_holding_by_symbol}")
    assert retrieved_holding_by_symbol is not None, "Should retrieve holding by Symbol object"
    assert retrieved_holding_by_symbol.quantity == Decimal('100'), f"Expected 100, got {retrieved_holding_by_symbol.quantity}"
    
    # Test subscript access with string ticker
    retrieved_holding_by_string = portfolio["AAPL"]
    print(f"Retrieved holding by string: {retrieved_holding_by_string}")
    assert retrieved_holding_by_string is not None, "Should retrieve holding by string ticker"
    assert retrieved_holding_by_string.quantity == Decimal('100'), f"Expected 100, got {retrieved_holding_by_string.quantity}"
    
    # Test access to non-existent holding (should return empty holding)
    empty_holding = portfolio["MSFT"]
    print(f"Empty holding for MSFT: {empty_holding}")
    assert empty_holding is not None, "Should return empty holding for non-existent ticker"
    assert empty_holding.quantity == Decimal('0'), f"Expected 0, got {empty_holding.quantity}"
    
    # Test __contains__ functionality
    assert "AAPL" in portfolio, "Portfolio should contain AAPL"
    assert "MSFT" not in portfolio, "Portfolio should not contain MSFT"
    assert symbol in portfolio, "Portfolio should contain the Symbol object"
    
    print("✅ All Portfolio subscriptable tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_portfolio_subscriptable()
        print("✅ Portfolio subscriptable functionality working correctly!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)