#!/usr/bin/env python3
"""Simple import test for misbuffet circular import fixes."""

import sys
import os

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_time_import():
    """Test Time import from time_utils."""
    try:
        print("Testing: from src.application.services.misbuffet.common.time_utils import Time")
        from src.application.services.misbuffet.common.time_utils import Time
        print("✓ SUCCESS: Time import successful")
        
        # Test basic functionality
        time_instance = Time()
        current_time = time_instance.now()
        print(f"  Time instance created, current time: {current_time}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_misbuffet_import():
    """Test main misbuffet module import."""
    try:
        print("\nTesting: import src.application.services.misbuffet")
        import src.application.services.misbuffet
        print("✓ SUCCESS: Main misbuffet module import successful")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_base_broker_import():
    """Test base broker import."""
    try:
        print("\nTesting: from src.application.services.misbuffet.brokers.base_broker import BaseBroker")
        from src.application.services.misbuffet.brokers.base_broker import BaseBroker
        print("✓ SUCCESS: BaseBroker import successful")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_broker_factory_import():
    """Test broker factory import."""
    try:
        print("\nTesting: from src.application.services.misbuffet.brokers.broker_factory import BrokerFactory")
        from src.application.services.misbuffet.brokers.broker_factory import BrokerFactory
        print("✓ SUCCESS: BrokerFactory import successful")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ibkr_broker_import():
    """Test IBKR broker import."""
    try:
        print("\nTesting: from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker")
        from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
        print("✓ SUCCESS: InteractiveBrokersBroker import successful")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all import tests."""
    print("=" * 70)
    print("TESTING CIRCULAR IMPORT FIXES FOR MISBUFFET SERVICE")
    print("=" * 70)
    
    results = []
    
    # Test 1: Time import
    results.append(("Time from time_utils", test_time_import()))
    
    # Test 2: Main misbuffet module
    results.append(("Main misbuffet module", test_misbuffet_import()))
    
    # Test 3: Broker imports
    results.append(("Base broker", test_base_broker_import()))
    results.append(("Broker factory", test_broker_factory_import()))
    results.append(("IBKR broker", test_ibkr_broker_import()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    failed = len(results) - passed
    print(f"\nResults: {passed}/{len(results)} tests passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All imports working! Circular import issues appear to be resolved.")
    else:
        print(f"\n⚠️ {failed} import(s) still need fixing.")
    
    return failed

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)