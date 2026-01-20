#!/usr/bin/env python3
"""
Test script to validate the Repository Factory implementation.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_repository_factory_import():
    """Test that RepositoryFactory can be imported."""
    try:
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        print("✓ RepositoryFactory imported successfully")
        return True
    except Exception as e:
        print(f"✗ RepositoryFactory import failed: {e}")
        return False

def test_entity_service_factory_integration():
    """Test that EntityService works with the new factory pattern."""
    try:
        from src.application.services.data.entities.entity_service import EntityService
        from src.application.services.database_service.database_service import DatabaseService
        
        # Create EntityService with factory
        db_service = DatabaseService('sqlite')
        entity_service = EntityService(database_service=db_service)
        
        print("✓ EntityService created with factory integration")
        print(f"✓ Local repositories count: {len(entity_service.local_repositories)}")
        print(f"✓ Factory available: {entity_service.repository_factory is not None}")
        print(f"✓ IBKR repositories: {entity_service.ibkr_repositories is not None}")
        
        # Test repository access
        from src.domain.entities.finance.financial_assets.currency import Currency
        currency_repo = entity_service.get_local_repository(Currency)
        print(f"✓ Currency repository retrieved: {currency_repo is not None}")
        
        return True
    except Exception as e:
        print(f"✗ EntityService factory integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ibkr_index_repository_factory_support():
    """Test that IBKRIndexRepository supports factory injection."""
    try:
        from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        from src.application.services.database_service.database_service import DatabaseService
        
        # Create factory without IBKR client (optional)
        db_service = DatabaseService('sqlite')
        factory = RepositoryFactory(db_service.session, ibkr_client=None)
        
        # Create local repositories
        local_repos = factory.create_local_repositories()
        
        # Create IBKRIndexRepository with factory (no IBKR client)
        mock_ibkr_client = None  # Testing without IBKR client
        index_repo = IBKRIndexRepository(
            ibkr_client=mock_ibkr_client,
            local_repo=local_repos['index'],
            factory=factory
        )
        
        print("✓ IBKRIndexRepository created with factory")
        print(f"✓ Factory injected: {index_repo.factory is not None}")
        print(f"✓ Currency repo available through factory: {factory.currency_repo is not None}")
        
        return True
    except Exception as e:
        print(f"✗ IBKRIndexRepository factory support failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_currency_dependency_resolution():
    """Test currency dependency resolution through factory."""
    try:
        from src.infrastructure.repositories.ibkr_repo.finance.financial_assets.index_repository import IBKRIndexRepository
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        from src.application.services.database_service.database_service import DatabaseService
        
        # Setup
        db_service = DatabaseService('sqlite')
        factory = RepositoryFactory(db_service.session, ibkr_client=None)
        local_repos = factory.create_local_repositories()
        
        index_repo = IBKRIndexRepository(
            ibkr_client=None,  # Test without IBKR client
            local_repo=local_repos['index'],
            factory=factory
        )
        
        # Test currency creation (should work with factory fallback)
        currency = index_repo._get_or_create_currency("USD", "US Dollar")
        
        print("✓ Currency dependency resolved through factory")
        print(f"✓ Currency created: {currency.symbol} - {currency.name}")
        
        return True
    except Exception as e:
        print(f"✗ Currency dependency resolution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing Repository Factory Implementation")
    print("=" * 60)
    
    tests = [
        ("Repository Factory Import", test_repository_factory_import),
        ("EntityService Factory Integration", test_entity_service_factory_integration),
        ("IBKRIndexRepository Factory Support", test_ibkr_index_repository_factory_support),
        ("Currency Dependency Resolution", test_currency_dependency_resolution)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Repository Factory implementation is working.")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    main()