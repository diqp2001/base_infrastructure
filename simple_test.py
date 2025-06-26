#!/usr/bin/env python3
"""
Simple test to verify the algorithm framework imports and basic functionality.
"""

import sys
from datetime import datetime

# Test imports
try:
    from src.application.services.back_testing.algorithm.base import QCAlgorithm
    from src.application.services.back_testing.algorithm.symbol import Symbol
    from src.application.services.back_testing.algorithm.enums import SecurityType, Resolution
    from src.application.services.back_testing.algorithm.data_handlers import TradeBar, Slice
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test basic functionality
try:
    # Test Symbol creation
    symbol = Symbol.create_equity("AAPL", "NASDAQ")
    print(f"✅ Symbol created: {symbol}")
    
    # Test QCAlgorithm instantiation
    algorithm = QCAlgorithm()
    print("✅ QCAlgorithm instantiated")
    
    # Test adding equity
    security = algorithm.add_equity("AAPL", Resolution.DAILY)
    print(f"✅ Equity added: {security.symbol}")
    
    # Test TradeBar creation
    bar = TradeBar(
        symbol=symbol,
        time=datetime.now(),
        end_time=datetime.now(),
        open=150.0,
        high=155.0,
        low=149.0,
        close=153.0,
        volume=1000000
    )
    print(f"✅ TradeBar created: OHLC = {bar.open}/{bar.high}/{bar.low}/{bar.close}")
    
    # Test order placement
    ticket = algorithm.market_order("AAPL", 100)
    print(f"✅ Market order placed: {ticket.quantity} shares")
    
    print("\n🎉 All basic tests passed! The QuantConnect-style framework is working correctly.")
    
except Exception as e:
    print(f"❌ Runtime error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)