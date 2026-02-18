#!/usr/bin/env python3
"""
Test script to verify IndexFactor import and repository registration fix.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all fixed imports work correctly."""
    print("Testing imports...")
    
    try:
        # Test IndexFactor import
        from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
        print("✓ IndexFactor import successful")
        
        # Test IBKR IndexFactor Repository import
        from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.ibkr_index_factor_repository import IBKRIndexFactorRepository
        print("✓ IBKRIndexFactorRepository import successful")
        
        # Test repository factory
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        print("✓ RepositoryFactory import successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_repository_registration():
    """Test that IndexFactor repository is properly registered."""
    print("\nTesting repository registration...")
    
    try:
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
        from unittest.mock import Mock
        
        # Create mock session
        mock_session = Mock()
        
        # Create factory without IBKR client first
        factory = RepositoryFactory(mock_session, None)
        
        # Test local repository registration
        local_repo = factory.get_local_repository(IndexFactor)
        if local_repo is not None:
            print("✓ IndexFactor local repository found")
        else:
            print("✗ IndexFactor local repository not found")
            return False
        
        # Test IBKR repository registration (should be None without client)
        ibkr_repo = factory.get_ibkr_repository(IndexFactor)
        if ibkr_repo is None:
            print("✓ IndexFactor IBKR repository correctly returns None without client")
        else:
            print("✗ IndexFactor IBKR repository should be None without client")
            return False
        
        # Test with mock IBKR client
        mock_client = Mock()
        factory_with_client = RepositoryFactory(mock_session, mock_client)
        
        ibkr_repo_with_client = factory_with_client.get_ibkr_repository(IndexFactor)
        if ibkr_repo_with_client is not None:
            print("✓ IndexFactor IBKR repository found with client")
        else:
            print("✗ IndexFactor IBKR repository not found with client")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Repository registration test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running IndexFactor repository fix verification...\n")
    
    success = True
    success &= test_imports()
    success &= test_repository_registration()
    
    if success:
        print("\n🎉 All tests passed! IndexFactor repository registration fix is working.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)