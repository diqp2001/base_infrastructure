#!/usr/bin/env python3
"""
Test script to verify the value sanitization function handles all data types correctly.
"""

import pandas as pd
from decimal import Decimal
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository

class TestSanitization:
    def __init__(self):
        # We'll just use a mock repository to test the sanitization method
        self.repo = BaseFactorRepository('sqlite')
    
    def test_sanitize_factor_value(self):
        """Test the sanitization function with various input types."""
        
        # Test cases: (input_value, expected_output_type, should_be_none)
        test_cases = [
            # Valid numeric values
            (123, Decimal, False),
            (123.45, Decimal, False),
            ("123", Decimal, False),
            ("123.45", Decimal, False),
            (Decimal("123.45"), Decimal, False),
            
            # Invalid string values (should return None)
            ("N/A", type(None), True),
            ("n/a", type(None), True),
            ("null", type(None), True),
            ("NULL", type(None), True),
            ("", type(None), True),
            ("   ", type(None), True),
            ("-", type(None), True),
            ("--", type(None), True),
            ("nan", type(None), True),
            ("NaN", type(None), True),
            ("inf", type(None), True),
            ("-inf", type(None), True),
            
            # None and NaN values
            (None, type(None), True),
            (pd.NA, type(None), True),
            (float('nan'), type(None), True),
            (float('inf'), type(None), True),
            (float('-inf'), type(None), True),
            
            # Edge cases
            ("0", Decimal, False),
            ("-123.45", Decimal, False),
            ("1.23e-4", Decimal, False),  # Scientific notation
        ]
        
        print("Testing value sanitization...")
        failed_tests = 0
        
        for i, (input_value, expected_type, should_be_none) in enumerate(test_cases):
            try:
                result = self.repo._sanitize_factor_value(input_value)
                
                if should_be_none:
                    if result is not None:
                        print(f"❌ Test {i+1} FAILED: Expected None for '{input_value}', got {result}")
                        failed_tests += 1
                    else:
                        print(f"✅ Test {i+1} PASSED: '{input_value}' -> None")
                else:
                    if result is None:
                        print(f"❌ Test {i+1} FAILED: Expected {expected_type} for '{input_value}', got None")
                        failed_tests += 1
                    elif not isinstance(result, expected_type):
                        print(f"❌ Test {i+1} FAILED: Expected {expected_type} for '{input_value}', got {type(result)}")
                        failed_tests += 1
                    else:
                        print(f"✅ Test {i+1} PASSED: '{input_value}' -> {result} ({type(result).__name__})")
                        
            except Exception as e:
                print(f"❌ Test {i+1} ERROR: Exception for '{input_value}': {e}")
                failed_tests += 1
        
        print(f"\nTest Summary: {len(test_cases) - failed_tests}/{len(test_cases)} tests passed")
        return failed_tests == 0

if __name__ == "__main__":
    tester = TestSanitization()
    success = tester.test_sanitize_factor_value()
    exit(0 if success else 1)