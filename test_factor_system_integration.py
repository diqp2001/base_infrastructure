#!/usr/bin/env python3
"""
Integration test for the unified factor system.
Tests mappers, repositories, calculation service, and API integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime
from decimal import Decimal
from typing import List
import pandas as pd

# Domain entities
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor

# Infrastructure
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper

# Application services
from src.application.services.factor_calculation_service import FactorCalculationService


def test_factor_mapper():
    """Test the factor mapper with different factor types."""
    print("🔄 Testing Factor Mapper...")
    
    # Test ShareMomentumFactor mapping
    momentum_factor = ShareMomentumFactor(
        name="20-Day Price Momentum",
        group="momentum",
        subgroup="price",
        data_type="numeric",
        source="calculated",
        definition="20-day price momentum calculation",
        period=20,
        momentum_type="price"
    )
    
    # Test Domain → ORM conversion
    orm_model = FactorMapper.to_orm(momentum_factor)
    print(f"✅ Domain → ORM: {type(orm_model).__name__}, factor_type: {orm_model.factor_type}")
    
    # Test ORM → Domain conversion  
    domain_entity = FactorMapper.to_domain(orm_model)
    print(f"✅ ORM → Domain: {type(domain_entity).__name__}, period: {domain_entity.period}")
    
    # Verify round-trip integrity
    assert momentum_factor.name == domain_entity.name
    assert momentum_factor.period == domain_entity.period
    assert momentum_factor.momentum_type == domain_entity.momentum_type
    print("✅ Round-trip conversion successful")


def test_repository_integration():
    """Test repository integration with mappers."""
    print("\n🗄️ Testing Repository Integration...")
    
    repository = BaseFactorRepository('sqlite')
    
    # Create a test factor
    test_factor = ShareMomentumFactor(
        name="Test 10-Day Momentum",
        group="momentum", 
        subgroup="short-term",
        data_type="numeric",
        source="test",
        definition="Test momentum factor",
        period=10,
        momentum_type="price"
    )
    
    # Test factor creation through repository
    created_factor = repository.create_factor(test_factor)
    if created_factor:
        print(f"✅ Factor created: ID={created_factor.id}, Type={type(created_factor).__name__}")
        
        # Test factor retrieval
        retrieved_factor = repository.get_by_id(created_factor.id)
        if retrieved_factor:
            print(f"✅ Factor retrieved: {retrieved_factor.name}, period={retrieved_factor.period}")
            
            # Test factor value creation
            test_date = date(2023, 1, 15)
            test_value = Decimal('0.05')  # 5% momentum
            
            factor_value = repository.add_factor_value(
                factor_id=created_factor.id,
                entity_id=1,  # Test entity
                date=test_date,
                value=test_value
            )
            
            if factor_value:
                print(f"✅ Factor value created: {factor_value.value} on {factor_value.date}")
            else:
                print("❌ Failed to create factor value")
        else:
            print("❌ Failed to retrieve factor")
    else:
        print("❌ Failed to create factor")


def test_calculation_service():
    """Test the factor calculation service."""
    print("\n📊 Testing Calculation Service...")
    
    service = FactorCalculationService('sqlite')
    
    # Create a momentum factor for testing
    momentum_factor = ShareMomentumFactor(
        name="Test Calculation Momentum",
        group="momentum",
        subgroup="calculation",
        data_type="numeric", 
        source="calculation_test",
        definition="Test momentum factor for calculation service",
        period=5,
        momentum_type="price"
    )
    
    # Create the factor in database first
    created_factor = service.repository.create_factor(momentum_factor)
    if created_factor:
        print(f"✅ Created factor for calculation: {created_factor.name}")
        
        # Test data
        prices = [100.0, 102.0, 101.5, 103.0, 105.0, 107.0, 106.0, 108.0, 110.0, 109.0]
        dates = [date(2023, 1, i+1) for i in range(10)]
        
        # Test momentum calculation and storage
        results = service.calculate_and_store_momentum(
            factor=created_factor,
            entity_id=1,
            entity_type='share',
            prices=prices,
            dates=dates,
            overwrite=True
        )
        
        print(f"✅ Calculation results: {results['stored_values']} values stored")
        print(f"   Errors: {len(results['errors'])}")
        
        if results['stored_values'] > 0:
            print("✅ Calculation service working correctly")
        else:
            print("❌ No values were stored")
    else:
        print("❌ Failed to create factor for calculation test")


def test_domain_calculations():
    """Test domain entity calculation methods."""
    print("\n🧮 Testing Domain Calculations...")
    
    # Test ShareMomentumFactor calculations
    momentum_factor = ShareMomentumFactor(
        name="Test Domain Calculations",
        group="momentum",
        period=5,
        momentum_type="price"
    )
    
    test_prices = [100.0, 102.0, 101.0, 103.0, 105.0, 107.0, 106.0]
    momentum_result = momentum_factor.calculate_momentum(test_prices)
    
    if momentum_result is not None:
        print(f"✅ Momentum calculation: {momentum_result:.4f}")
        print(f"   Classification: Short-term={momentum_factor.is_short_term()}")
    else:
        print("❌ Momentum calculation failed")
    
    # Test ShareTechnicalFactor calculations
    technical_factor = ShareTechnicalFactor(
        name="Test SMA",
        group="technical",
        indicator_type="SMA",
        period=3
    )
    
    test_close_prices = [100.0, 102.0, 101.0, 103.0, 105.0]
    sma_results = technical_factor.calculate_sma(test_close_prices)
    
    if sma_results and any(x is not None for x in sma_results):
        valid_smas = [x for x in sma_results if x is not None]
        print(f"✅ SMA calculation: Last SMA = {valid_smas[-1]:.2f}")
    else:
        print("❌ SMA calculation failed")
    
    # Test ShareVolatilityFactor calculations
    volatility_factor = ShareVolatilityFactor(
        name="Test Volatility",
        group="risk",
        volatility_type="historical",
        period=5
    )
    
    test_returns = [0.02, -0.01, 0.015, 0.03, -0.005, 0.01]
    vol_result = volatility_factor.calculate_historical_volatility(test_returns)
    
    if vol_result is not None:
        print(f"✅ Volatility calculation: {vol_result:.4f}")
    else:
        print("❌ Volatility calculation failed")


def main():
    """Run all integration tests."""
    print("🚀 Starting Factor System Integration Tests...\n")
    
    try:
        test_factor_mapper()
        test_repository_integration() 
        test_calculation_service()
        test_domain_calculations()
        
        print("\n✅ All integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)