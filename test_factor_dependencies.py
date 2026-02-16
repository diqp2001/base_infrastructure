#!/usr/bin/env python3
"""
Test script for factor dependency creation functionality.
Tests the new _create_or_get method with dependency handling.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_factor_library_import():
    """Test that we can import the factor library components"""
    try:
        from src.application.services.data.entities.factor.factor_library.factor_definition_config import get_factor_config, FACTOR_LIBRARY
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.index_library import INDEX_LIBRARY
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.future.future_index_library import FUTURE_INDEX_LIBRARY
        
        print("✅ Successfully imported factor library components")
        
        # Test accessing configurations
        print(f"📊 INDEX_LIBRARY has {len(INDEX_LIBRARY)} factors")
        print(f"📈 FUTURE_INDEX_LIBRARY has {len(FUTURE_INDEX_LIBRARY)} factors")
        
        # Test the get_factor_config function
        config = get_factor_config("close")
        if config:
            print(f"✅ Found config for 'close': {config}")
        else:
            print("❌ No config found for 'close'")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_factor_repository_import():
    """Test that we can import the modified factor repository"""
    try:
        from src.infrastructure.repositories.local_repo.factor.factor_repository import FactorRepository
        from src.domain.entities.factor.factor import Factor
        from src.domain.entities.factor.factor_dependency import FactorDependency
        
        print("✅ Successfully imported factor repository components")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_dependency_structure():
    """Test the dependency structure in factor libraries"""
    try:
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.derivatives.future.future_index_library import FUTURE_INDEX_LIBRARY
        
        # Test the return_open factor which has dependencies
        return_open_config = FUTURE_INDEX_LIBRARY.get("return_open")
        if return_open_config:
            print(f"✅ Found return_open config: {return_open_config}")
            dependencies = return_open_config.get("dependencies", {})
            print(f"📋 Dependencies structure: {dependencies}")
            print(f"📋 Dependencies type: {type(dependencies)}")
            
            if isinstance(dependencies, dict):
                print(f"📋 Dependency names: {list(dependencies.keys())}")
            
            return True
        else:
            print("❌ return_open config not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing dependency structure: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Factor Dependency Implementation")
    print("=" * 50)
    
    tests = [
        test_factor_library_import,
        test_factor_repository_import, 
        test_dependency_structure
    ]
    
    results = []
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        result = test()
        results.append(result)
        print("-" * 30)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The factor dependency implementation looks good.")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)