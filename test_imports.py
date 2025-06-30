#!/usr/bin/env python3
"""
Test script to verify that all imports work correctly after fixes.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("Testing import fixes...")
    
    try:
        # Test main module import
        print("Testing back_testing module import...")
        from application.services.back_testing import common
        print("✅ Common module imported successfully")
        
        from application.services.back_testing import data
        print("✅ Data module imported successfully")
        
        from application.services.back_testing import engine
        print("✅ Engine module imported successfully")
        
        from application.services.back_testing import algorithm_factory
        print("✅ Algorithm Factory module imported successfully")
        
        from application.services.back_testing import api
        print("✅ API module imported successfully")
        
        from application.services.back_testing import launcher
        print("✅ Launcher module imported successfully")
        
        from application.services.back_testing import optimizer
        print("✅ Optimizer module imported successfully")
        
        from application.services.back_testing import optimizer_launcher
        print("✅ Optimizer Launcher module imported successfully")
        
        # Test specific classes
        print("\nTesting specific class imports...")
        from application.services.back_testing.common import IAlgorithm, Symbol, Resolution
        print("✅ Common classes imported successfully")
        
        from application.services.back_testing.engine import LeanEngine
        print("✅ Engine classes imported successfully")
        
        print("\n🎉 All imports successful! Import fixes are working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)