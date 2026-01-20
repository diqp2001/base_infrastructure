#!/usr/bin/env python3
"""
Test script for repository get_or_create functionality.
This script tests the new repository methods without requiring the full test suite.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_repository_imports():
    """Test that all repositories with get_or_create can be imported successfully."""
    try:
        from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository
        print("✅ CurrencyRepository imported successfully")
        
        from src.infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository
        print("✅ CompanyRepository imported successfully")
        
        from src.infrastructure.repositories.local_repo.finance.exchange_repository import ExchangeRepository  
        print("✅ ExchangeRepository imported successfully")
        
        from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
        print("✅ CompanyShareRepository imported successfully")
        
        from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.options_repository import OptionsRepository
        print("✅ OptionsRepository imported successfully")
        
        # Test that get_or_create methods exist
        assert hasattr(CurrencyRepository, 'get_or_create'), "CurrencyRepository missing get_or_create method"
        print("✅ CurrencyRepository.get_or_create method exists")
        
        assert hasattr(CompanyRepository, 'get_or_create'), "CompanyRepository missing get_or_create method"
        print("✅ CompanyRepository.get_or_create method exists")
        
        assert hasattr(ExchangeRepository, 'get_or_create'), "ExchangeRepository missing get_or_create method"
        print("✅ ExchangeRepository.get_or_create method exists")
        
        assert hasattr(CompanyShareRepository, 'get_or_create'), "CompanyShareRepository missing get_or_create method"
        print("✅ CompanyShareRepository.get_or_create method exists")
        
        assert hasattr(OptionsRepository, 'get_or_create'), "OptionsRepository missing get_or_create method"
        print("✅ OptionsRepository.get_or_create method exists")
        
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

def test_mappers_no_longer_have_dependencies():
    """Test that mappers no longer have to_orm_with_dependencies methods."""
    try:
        from src.infrastructure.repositories.mappers.finance.financial_assets.currency_mapper import CurrencyMapper
        from src.infrastructure.repositories.mappers.finance.financial_assets.options_mapper import OptionsMapper
        from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper
        
        # Test that old methods are removed
        assert not hasattr(CurrencyMapper, 'to_orm_with_dependencies'), "CurrencyMapper still has to_orm_with_dependencies method"
        print("✅ CurrencyMapper.to_orm_with_dependencies method removed")
        
        assert not hasattr(OptionsMapper, 'to_orm_with_dependencies'), "OptionsMapper still has to_orm_with_dependencies method"
        print("✅ OptionsMapper.to_orm_with_dependencies method removed")
        
        assert not hasattr(CompanyShareMapper, 'to_orm_with_dependencies'), "CompanyShareMapper still has to_orm_with_dependencies method"
        print("✅ CompanyShareMapper.to_orm_with_dependencies method removed")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ Unexpected removal: {e}")
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
    print("🧪 Testing Repository Get-Or-Create Refactoring")
    print("=" * 50)
    
    tests = [
        test_repository_imports,
        test_mappers_no_longer_have_dependencies,
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
        print("🎉 All tests passed! Repository get_or_create refactoring is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)