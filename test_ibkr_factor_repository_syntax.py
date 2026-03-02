#!/usr/bin/env python3
"""
Test script to validate the IBKRFactorValueRepository syntax changes.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Try to import the modified module
    from infrastructure.repositories.ibkr_repo.factor.ibkr_factor_value_repository import IBKRFactorValueRepository
    print("✅ IBKRFactorValueRepository imported successfully")
    print("✅ Syntax validation passed")
    
    # Check if the method exists
    if hasattr(IBKRFactorValueRepository, '_handle_factor_with_dependencies'):
        print("✅ _handle_factor_with_dependencies method found")
    else:
        print("❌ _handle_factor_with_dependencies method not found")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")