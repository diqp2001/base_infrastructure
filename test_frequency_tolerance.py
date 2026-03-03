#!/usr/bin/env python3
"""
Test script for dynamic frequency-based tolerance calculation in IBKRFactorValueRepository.

This script validates the _calculate_date_tolerance_seconds method works correctly
for different factor frequency values.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime
from src.infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
from src.domain.entities.factor.factor import Factor

class MockFactor:
    """Mock factor entity for testing tolerance calculation."""
    
    def __init__(self, name: str, frequency: str = None):
        self.name = name
        self.frequency = frequency
        self.id = 1

def test_frequency_tolerance():
    """Test the _calculate_date_tolerance_seconds method with different frequencies."""
    print("Testing Dynamic Frequency-Based Tolerance Calculation")
    print("=" * 60)
    
    # Create a mock IBKRFactorValueRepository instance
    repo = IBKRFactorValueRepository(ibkr_client=None, factory=None)
    
    # Test cases: (frequency, expected_tolerance_seconds, description)
    test_cases = [
        (None, 86400, "No frequency (default)"),
        ("", 86400, "Empty frequency (default)"),
        ("second", 1, "Second frequency"),
        ("minute", 60, "Minute frequency"),
        ("min", 60, "Abbreviated minute frequency"),
        ("hourly", 3600, "Hourly frequency"),
        ("hour", 3600, "Hour frequency"),
        ("daily", 86400, "Daily frequency"),
        ("day", 86400, "Day frequency"),
        ("weekly", 604800, "Weekly frequency"),
        ("week", 604800, "Week frequency"),
        ("monthly", 2592000, "Monthly frequency"),
        ("month", 2592000, "Month frequency"),
        ("yearly", 31536000, "Yearly frequency"),
        ("year", 31536000, "Year frequency"),
        ("DAILY", 86400, "Daily frequency (uppercase)"),
        ("Weekly", 604800, "Weekly frequency (mixed case)"),
        ("unknown_freq", 86400, "Unknown frequency (default)"),
    ]
    
    all_passed = True
    
    for frequency, expected_tolerance, description in test_cases:
        # Create mock factor with specific frequency
        mock_factor = MockFactor(name="test_factor", frequency=frequency)
        
        # Calculate tolerance
        actual_tolerance = repo._calculate_date_tolerance_seconds(mock_factor)
        
        # Check if result matches expected
        passed = actual_tolerance == expected_tolerance
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status} {description}")
        print(f"    Frequency: {frequency}")
        print(f"    Expected: {expected_tolerance:,} seconds")
        print(f"    Actual:   {actual_tolerance:,} seconds")
        
        # Convert to human-readable time for clarity
        if expected_tolerance == 1:
            time_desc = "1 second"
        elif expected_tolerance == 60:
            time_desc = "1 minute"
        elif expected_tolerance == 3600:
            time_desc = "1 hour"
        elif expected_tolerance == 86400:
            time_desc = "1 day"
        elif expected_tolerance == 604800:
            time_desc = "1 week"
        elif expected_tolerance == 2592000:
            time_desc = "30 days"
        elif expected_tolerance == 31536000:
            time_desc = "365 days"
        else:
            time_desc = f"{expected_tolerance} seconds"
        
        print(f"    Time:     {time_desc}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests PASSED! Dynamic tolerance calculation works correctly.")
    else:
        print("❌ Some tests FAILED! Please check the implementation.")
    
    return all_passed

def test_tolerance_examples():
    """Test tolerance calculation with realistic examples."""
    print("Testing Realistic Factor Examples")
    print("=" * 40)
    
    repo = IBKRFactorValueRepository(ibkr_client=None, factory=None)
    
    examples = [
        ("return_daily", "daily", "Daily return factor"),
        ("price_minute", "minute", "Minute price factor"),
        ("volume_weekly", "weekly", "Weekly volume factor"),
        ("earnings_monthly", "monthly", "Monthly earnings factor"),
    ]
    
    for factor_name, frequency, description in examples:
        mock_factor = MockFactor(name=factor_name, frequency=frequency)
        tolerance = repo._calculate_date_tolerance_seconds(mock_factor)
        
        print(f"Factor: {factor_name}")
        print(f"  Description: {description}")
        print(f"  Frequency: {frequency}")
        print(f"  Tolerance: {tolerance:,} seconds")
        print()

if __name__ == "__main__":
    print("IBKRFactorValueRepository Frequency Tolerance Test")
    print("=" * 60)
    print()
    
    success = test_frequency_tolerance()
    print()
    test_tolerance_examples()
    
    if success:
        print("✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test completed with failures!")
        sys.exit(1)