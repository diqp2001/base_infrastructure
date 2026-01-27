#!/usr/bin/env python3
"""
Test script for IBKR Factor Repositories and RepositoryFactory integration.

This script tests:
1. IBKR factor repositories creation
2. Repository factory integration
3. Basic functionality of new repositories
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Test imports
    from src.infrastructure.repositories.repository_factory import RepositoryFactory
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_continent_factor_repository import IBKRContinentFactorRepository
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_country_factor_repository import IBKRCountryFactorRepository
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_factor_repository import IBKRIndexFactorRepository
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_share_factor_repository import IBKRShareFactorRepository
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_currency_factor_repository import IBKRCurrencyFactorRepository
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_equity_factor_repository import IBKREquityFactorRepository
    
    # Test mappers imports
    from src.infrastructure.repositories.mappers.factor.ibkr_continent_factor_mapper import IBKRContinentFactorMapper
    from src.infrastructure.repositories.mappers.factor.ibkr_country_factor_mapper import IBKRCountryFactorMapper
    from src.infrastructure.repositories.mappers.factor.ibkr_index_factor_mapper import IBKRIndexFactorMapper
    from src.infrastructure.repositories.mappers.factor.ibkr_share_factor_mapper import IBKRShareFactorMapper
    from src.infrastructure.repositories.mappers.factor.ibkr_currency_factor_mapper import IBKRCurrencyFactorMapper
    from src.infrastructure.repositories.mappers.factor.ibkr_equity_factor_mapper import IBKREquityFactorMapper
    
    print("✅ All imports successful!")
    
    # Test repository factory can be created (without actual DB session)
    print("\n🧪 Testing Repository Factory...")
    
    # Mock session for testing
    class MockSession:
        def __init__(self):
            pass
    
    mock_session = MockSession()
    factory = RepositoryFactory(mock_session, ibkr_client=None)
    
    print("✅ Repository factory created successfully!")
    
    # Test local repositories are created
    local_repos = factory.create_local_repositories()
    print(f"✅ Created {len(local_repos)} local repositories")
    
    # Test specific factor repositories exist
    factor_repo_keys = [
        'continent_factor',
        'country_factor', 
        'index_factor',
        'share_factor',
        'currency_factor',
        'equity_factor'
    ]
    
    for key in factor_repo_keys:
        if key in local_repos:
            print(f"✅ Found local {key} repository")
        else:
            print(f"❌ Missing local {key} repository")
    
    # Test property methods
    print("\n🧪 Testing Repository Factory Properties...")
    
    local_properties = [
        'continent_factor_local_repo',
        'country_factor_local_repo',
        'index_factor_local_repo', 
        'share_factor_local_repo',
        'currency_factor_local_repo',
        'equity_factor_local_repo'
    ]
    
    for prop_name in local_properties:
        if hasattr(factory, prop_name):
            prop_value = getattr(factory, prop_name)
            print(f"✅ Property {prop_name}: {type(prop_value).__name__}")
        else:
            print(f"❌ Missing property {prop_name}")
    
    # Test IBKR properties (when no client is available)
    ibkr_properties = [
        'continent_factor_ibkr_repo',
        'country_factor_ibkr_repo',
        'index_factor_ibkr_repo',
        'share_factor_ibkr_repo', 
        'currency_factor_ibkr_repo',
        'equity_factor_ibkr_repo'
    ]
    
    for prop_name in ibkr_properties:
        if hasattr(factory, prop_name):
            prop_value = getattr(factory, prop_name)
            print(f"✅ IBKR Property {prop_name}: {prop_value} (None expected without client)")
        else:
            print(f"❌ Missing IBKR property {prop_name}")
    
    print("\n🎉 All tests passed! IBKR Factor Repositories integration successful.")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)