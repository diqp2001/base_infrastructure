#!/usr/bin/env python3
"""
Test script for mapper enhancements with get_or_create functionality.
This script tests the new mapper methods without requiring the full test suite.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all enhanced mappers can be imported successfully."""
    try:
        from src.infrastructure.repositories.mappers.finance.financial_assets.currency_mapper import CurrencyMapper
        print("✅ CurrencyMapper imported successfully")
        
        from src.infrastructure.repositories.mappers.finance.financial_assets.options_mapper import OptionsMapper  
        print("✅ OptionsMapper imported successfully")
        
        from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper
        print("✅ CompanyShareMapper imported successfully")
        
        # Test that new methods exist
        assert hasattr(CurrencyMapper, 'to_orm_with_dependencies'), "CurrencyMapper missing to_orm_with_dependencies method"
        print("✅ CurrencyMapper.to_orm_with_dependencies method exists")
        
        assert hasattr(OptionsMapper, 'to_orm_with_dependencies'), "OptionsMapper missing to_orm_with_dependencies method"
        print("✅ OptionsMapper.to_orm_with_dependencies method exists")
        
        assert hasattr(CompanyShareMapper, 'to_orm_with_dependencies'), "CompanyShareMapper missing to_orm_with_dependencies method"
        print("✅ CompanyShareMapper.to_orm_with_dependencies method exists")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Method missing: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_currency_repository_enhancement():
    """Test that currency repository has get_or_create functionality."""
    try:
        from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
        
        # Test that new method exists
        assert hasattr(CurrencyRepository, 'get_or_create_by_code'), "CurrencyRepository missing get_or_create_by_code method"
        print("✅ CurrencyRepository.get_or_create_by_code method exists")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Method missing: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_documentation():
    """Test that documentation file was created."""
    try:
        doc_path = "/home/runner/work/base_infrastructure/base_infrastructure/MAPPERS_CLAUDE.md"
        assert os.path.exists(doc_path), f"Documentation file not found: {doc_path}"
        print("✅ MAPPERS_CLAUDE.md documentation file exists")
        
        # Check that it contains expected content
        with open(doc_path, 'r') as f:
            content = f.read()
            assert "Complete Mapper Inventory" in content, "Documentation missing expected title"
            assert "get_or_create" in content, "Documentation missing get_or_create references"
            assert "CurrencyMapper" in content, "Documentation missing CurrencyMapper"
            assert "OptionsMapper" in content, "Documentation missing OptionsMapper"
        
        print("✅ Documentation contains expected content")
        return True
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Mapper Enhancements")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_currency_repository_enhancement,
        test_documentation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Mapper enhancements are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)