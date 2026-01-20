#!/usr/bin/env python3
"""
Test script to validate the new get_or_create functionality across repositories.
This script performs basic syntax validation and import checks.
"""

import sys
import traceback
from typing import List

def test_repository_imports() -> List[str]:
    """Test that all enhanced repositories can be imported successfully."""
    results = []
    
    repositories_to_test = [
        # Enhanced repositories
        ('OptionsRepository', 'src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.options_repository'),
        ('CountryRepository', 'src.infrastructure.repositories.local_repo.geographic.country_repository'),
        ('BondRepository', 'src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository'),
        ('IndexRepository', 'src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository'),
        ('PortfolioRepository', 'src.infrastructure.repositories.local_repo.finance.portfolio_repository'),
        ('CommodityRepository', 'src.infrastructure.repositories.local_repo.finance.financial_assets.commodity_repository'),
        
        # Existing repositories (for validation)
        ('CurrencyRepository', 'src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository'),
        ('CompanyRepository', 'src.infrastructure.repositories.local_repo.finance.company_repository'),
        ('ExchangeRepository', 'src.infrastructure.repositories.local_repo.finance.exchange_repository'),
        ('CompanyShareRepository', 'src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository'),
    ]
    
    for repo_name, module_path in repositories_to_test:
        try:
            module = __import__(module_path, fromlist=[repo_name])
            repo_class = getattr(module, repo_name)
            
            # Check if get_or_create method exists
            if hasattr(repo_class, 'get_or_create'):
                results.append(f"✅ {repo_name}: Import successful, get_or_create method found")
            else:
                results.append(f"❌ {repo_name}: Import successful, but get_or_create method MISSING")
                
        except Exception as e:
            results.append(f"❌ {repo_name}: Import failed - {str(e)}")
            
    return results

def test_method_signatures() -> List[str]:
    """Test that get_or_create methods have reasonable signatures."""
    results = []
    
    try:
        # Test OptionsRepository enhanced signature
        from src.infrastructure.repositories.local_repo.finance.financial_assets.derivatives.options_repository import OptionsRepository
        import inspect
        
        sig = inspect.signature(OptionsRepository.get_or_create)
        params = list(sig.parameters.keys())
        
        if 'underlying_asset_id' in params:
            results.append("✅ OptionsRepository.get_or_create has underlying_asset_id parameter")
        else:
            results.append("❌ OptionsRepository.get_or_create missing underlying_asset_id parameter")
            
    except Exception as e:
        results.append(f"❌ OptionsRepository signature test failed: {str(e)}")
    
    try:
        # Test BondRepository signature
        from src.infrastructure.repositories.local_repo.finance.financial_assets.bond_repository import BondRepository
        import inspect
        
        sig = inspect.signature(BondRepository.get_or_create)
        params = list(sig.parameters.keys())
        
        expected_params = ['isin', 'cusip', 'ticker', 'currency_code']
        found_params = [p for p in expected_params if p in params]
        
        if len(found_params) >= 3:
            results.append(f"✅ BondRepository.get_or_create has expected parameters: {found_params}")
        else:
            results.append(f"❌ BondRepository.get_or_create missing expected parameters")
            
    except Exception as e:
        results.append(f"❌ BondRepository signature test failed: {str(e)}")
        
    return results

def test_documentation() -> List[str]:
    """Test that documentation files were created."""
    results = []
    
    try:
        with open('GET_OR_CREATE_STATUS.md', 'r') as f:
            content = f.read()
            if 'get_or_create functionality' in content:
                results.append("✅ GET_OR_CREATE_STATUS.md created with valid content")
            else:
                results.append("❌ GET_OR_CREATE_STATUS.md content validation failed")
    except FileNotFoundError:
        results.append("❌ GET_OR_CREATE_STATUS.md file not found")
    except Exception as e:
        results.append(f"❌ GET_OR_CREATE_STATUS.md validation failed: {str(e)}")
        
    return results

def main():
    """Run all tests and print results."""
    print("🧪 Testing get_or_create enhancements...")
    print("=" * 60)
    
    all_results = []
    
    # Test imports
    print("\n📦 Testing Repository Imports:")
    import_results = test_repository_imports()
    all_results.extend(import_results)
    for result in import_results:
        print(f"  {result}")
    
    # Test method signatures  
    print("\n🔍 Testing Method Signatures:")
    signature_results = test_method_signatures()
    all_results.extend(signature_results)
    for result in signature_results:
        print(f"  {result}")
    
    # Test documentation
    print("\n📚 Testing Documentation:")
    doc_results = test_documentation()
    all_results.extend(doc_results)
    for result in doc_results:
        print(f"  {result}")
    
    # Summary
    print("\n" + "=" * 60)
    success_count = len([r for r in all_results if r.startswith("✅")])
    total_count = len(all_results)
    
    print(f"📊 Test Summary: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All tests passed! get_or_create enhancements are ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())