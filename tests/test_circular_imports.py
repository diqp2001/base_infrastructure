#!/usr/bin/env python3
"""
Test script to verify circular import fixes in the misbuffet service.
"""

import sys
import traceback

def test_import(module_path, class_or_function_name=None):
    """Test importing a module or specific class/function."""
    try:
        if class_or_function_name:
            print(f"Testing: from {module_path} import {class_or_function_name}")
            module = __import__(module_path, fromlist=[class_or_function_name])
            imported_item = getattr(module, class_or_function_name)
            print(f"✓ SUCCESS: {class_or_function_name} imported successfully")
            return True
        else:
            print(f"Testing: import {module_path}")
            __import__(module_path)
            print(f"✓ SUCCESS: {module_path} imported successfully")
            return True
    except ImportError as e:
        print(f"✗ IMPORT ERROR: {e}")
        print(f"  Traceback: {traceback.format_exc()}")
        return False
    except Exception as e:
        print(f"✗ UNEXPECTED ERROR: {e}")
        print(f"  Traceback: {traceback.format_exc()}")
        return False

def main():
    print("=" * 60)
    print("Testing Circular Import Fixes for Misbuffet Service")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Import Time from time_utils
    print("\n1. Testing Time import from time_utils:")
    result1 = test_import("src.application.services.misbuffet.common.time_utils", "Time")
    test_results.append(("Time from time_utils", result1))
    
    # Test 2: Import the main misbuffet module  
    print("\n2. Testing main misbuffet module import:")
    result2 = test_import("src.application.services.misbuffet")
    test_results.append(("Main misbuffet module", result2))
    
    # Test 3: Test broker-related imports
    print("\n3. Testing broker-related imports:")
    
    # Test base broker
    print("\n3a. Testing base broker import:")
    result3a = test_import("src.application.services.misbuffet.brokers.base_broker")
    test_results.append(("Base broker", result3a))
    
    # Test broker factory
    print("\n3b. Testing broker factory import:")
    result3b = test_import("src.application.services.misbuffet.brokers.broker_factory")
    test_results.append(("Broker factory", result3b))
    
    # Test IBKR broker
    print("\n3c. Testing IBKR broker import:")
    result3c = test_import("src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker")
    test_results.append(("IBKR broker", result3c))
    
    # Test 4: Additional key modules
    print("\n4. Testing additional key modules:")
    
    # Test common modules
    print("\n4a. Testing common data types:")
    result4a = test_import("src.application.services.misbuffet.common.data_types")
    test_results.append(("Common data types", result4a))
    
    # Test enums
    print("\n4b. Testing enums:")
    result4b = test_import("src.application.services.misbuffet.common.enums")
    test_results.append(("Common enums", result4b))
    
    # Test securities
    print("\n4c. Testing securities:")
    result4c = test_import("src.application.services.misbuffet.common.securities")
    test_results.append(("Common securities", result4c))
    
    # Test algorithm base
    print("\n4d. Testing algorithm base:")
    result4d = test_import("src.application.services.misbuffet.algorithm.base")
    test_results.append(("Algorithm base", result4d))
    
    # Test engine
    print("\n4e. Testing engine:")
    result4e = test_import("src.application.services.misbuffet.engine.base_engine")
    test_results.append(("Base engine", result4e))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY OF IMPORT TESTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {len(test_results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All imports working correctly! Circular import issues resolved.")
        return 0
    else:
        print(f"\n⚠️  {failed} imports still have issues that need to be fixed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())