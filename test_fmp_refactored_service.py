#!/usr/bin/env python3
"""
Test script for the refactored FMP API service that uses existing domain entities.

This script verifies that:
1. FMP API service connects properly
2. FMP repository translates data to existing domain entities
3. Service integrates with existing repository infrastructure
4. Configuration system works correctly
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    from src.application.services.api_service.fmp_service.get_equity_service import (
        FmpEquityDataService, create_fmp_equity_service
    )
    from src.application.services.api_service.fmp_service.config_equity_service import (
        FmpEquityServiceConfig, get_minimal_config
    )
    from src.application.services.api_service.fmp_service.financial_modeling_prep_api_service import (
        FinancialModelingPrepApiService
    )
    from infrastructure.repositories.fmp_repo.fmp_repository import FmpRepository
    
    print("✅ All imports successful")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease ensure:")
    print("1. You have FMP credentials file in the correct location")
    print("2. All dependencies are installed")
    print("3. The project structure is correct")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_fmp_api_service():
    """Test basic FMP API service functionality"""
    print("\n🧪 Testing FMP API Service...")
    
    try:
        # Initialize FMP API service
        service = FinancialModelingPrepApiService()
        
        # Test API health
        health = service.check_api_health()
        print(f"API Health: {health['status']}")
        
        # Test quote retrieval
        quote = service.get_quote('AAPL')
        if quote:
            print(f"✅ Successfully retrieved quote for AAPL: ${quote.get('price', 'N/A')}")
            return True
        else:
            print("❌ Failed to retrieve quote for AAPL")
            return False
            
    except Exception as e:
        print(f"❌ FMP API service error: {e}")
        return False


def test_fmp_repository():
    """Test FMP repository translation functionality"""
    print("\n🧪 Testing FMP Repository...")
    
    try:
        # Create in-memory database for testing
        engine = create_engine('sqlite:///:memory:', echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Initialize repository
        fmp_repo = FmpRepository(session)
        
        # Mock FMP quote data for testing
        mock_quote = {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'price': 195.89,
            'changesPercentage': 1.23,
            'change': 2.37,
            'marketCap': 3010590924800,
            'volume': 52164471,
            'eps': 6.13,
            'pe': 31.96,
            'exchange': 'NASDAQ',
            'timestamp': 1699632000
        }
        
        # Test translation to CompanyShare
        company_share = fmp_repo.translate_quote_to_company_share(mock_quote)
        if company_share:
            print(f"✅ Successfully translated quote to CompanyShare: {company_share.ticker}")
        else:
            print("❌ Failed to translate quote to CompanyShare")
            return False
        
        # Test translation to ShareFactors
        share_factors = fmp_repo.translate_quote_to_share_factors(mock_quote)
        if share_factors:
            print(f"✅ Successfully translated quote to {len(share_factors)} ShareFactors")
        else:
            print("❌ Failed to translate quote to ShareFactors")
            return False
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ FMP Repository error: {e}")
        return False


def test_configuration():
    """Test configuration system"""
    print("\n🧪 Testing Configuration...")
    
    try:
        # Test default configuration
        default_config = FmpEquityServiceConfig.get_default_config()
        print(f"✅ Default config loaded with {len(default_config.symbols)} symbols")
        
        # Test minimal configuration
        minimal_config = get_minimal_config()
        print(f"✅ Minimal config loaded with {len(minimal_config.symbols)} symbols")
        
        # Test configuration validation
        errors = default_config.validate()
        if not errors:
            print("✅ Default configuration is valid")
        else:
            print(f"❌ Default configuration has errors: {errors}")
            return False
        
        # Test configuration to/from dict
        config_dict = default_config.to_dict()
        restored_config = FmpEquityServiceConfig.from_dict(config_dict)
        if restored_config.symbols == default_config.symbols:
            print("✅ Configuration serialization works correctly")
        else:
            print("❌ Configuration serialization failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_equity_service_integration():
    """Test full FMP equity service integration"""
    print("\n🧪 Testing FMP Equity Service Integration...")
    
    try:
        # Create in-memory database for testing
        engine = create_engine('sqlite:///:memory:', echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Use minimal configuration for testing
        config = get_minimal_config()
        
        # Create service
        service = FmpEquityDataService(session, config)
        print("✅ FMP Equity Service initialized")
        
        # Test service status
        status = service.get_service_status()
        if status.get('service_status') == 'operational':
            print("✅ Service status is operational")
        else:
            print(f"❌ Service status issue: {status}")
            return False
        
        # Note: We won't test actual API calls in this integration test
        # to avoid hitting API limits, but the structure is verified
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Equity Service Integration error: {e}")
        return False


def test_factory_function():
    """Test service factory function"""
    print("\n🧪 Testing Service Factory Function...")
    
    try:
        # Create in-memory database
        engine = create_engine('sqlite:///:memory:', echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Test factory function
        service = create_fmp_equity_service(session)
        print("✅ Factory function created service successfully")
        
        # Verify service properties
        if hasattr(service, 'config') and hasattr(service, 'fmp_api_service'):
            print("✅ Service has required attributes")
        else:
            print("❌ Service missing required attributes")
            return False
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Factory function error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Starting FMP Service Integration Tests")
    print("=" * 60)
    
    tests = [
        ("FMP API Service", test_fmp_api_service),
        ("FMP Repository", test_fmp_repository),
        ("Configuration System", test_configuration),
        ("Equity Service Integration", test_equity_service_integration),
        ("Service Factory Function", test_factory_function),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The FMP service refactoring is successful.")
        print("\nThe service now:")
        print("- Uses existing CompanyShare and ShareFactor domain entities")
        print("- Translates FMP API data via FmpRepository")
        print("- Integrates with existing repository infrastructure")
        print("- Provides comprehensive configuration management")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)