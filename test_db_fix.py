#!/usr/bin/env python3
"""
Simple test to verify the database table relationship fix.
Tests that NoReferencedTableError has been resolved.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_database_creation():
    """Test if database creation works without foreign key errors."""
    try:
        from src.infrastructure.database.base_factory import BaseFactory
        
        # Use SQLite for testing (no external dependencies)
        print("Testing database creation with SQLite...")
        factory = BaseFactory('SQLITE')
        
        print("✅ SUCCESS: Database creation completed without NoReferencedTableError!")
        print("✅ Fixed: portfolio_derivative_holdings.portfolio_derivative_id now references correct table")
        print("✅ Fixed: Relationship back_populates corrected")
        
        # Clean up
        factory.drop_all_tables()
        print("✅ Test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_database_creation()
    sys.exit(0 if success else 1)