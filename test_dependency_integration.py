#!/usr/bin/env python3
"""
Test script to validate IndexPriceReturnFactorRepository dependency integration.
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor

def test_dependency_integration():
    """Test that IndexPriceReturnFactorRepository properly populates dependencies."""
    
    # Create database engine (using SQLite for testing)
    engine = create_engine('sqlite:///:memory:', echo=True)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create all tables
    from src.infrastructure.models import ModelBase
    ModelBase.metadata.create_all(engine)
    
    # Create repository factory
    factory = RepositoryFactory(session=session)
    
    try:
        # Get the IndexPriceReturnFactorRepository
        index_price_return_factor_repo = factory.get_local_repository(IndexPriceReturnFactor)
        
        if not index_price_return_factor_repo:
            print("ERROR: Could not get IndexPriceReturnFactorRepository from factory")
            return False
            
        print(f"✅ Got IndexPriceReturnFactorRepository: {type(index_price_return_factor_repo).__name__}")
        
        # Test creating a return_daily factor
        print("\n🔧 Testing return_daily factor creation with dependency population...")
        
        factor = index_price_return_factor_repo._create_or_get(
            entity_cls=IndexPriceReturnFactor,
            primary_key="return_daily",
            group="return",
            subgroup="daily",
            data_type="numeric",
            source="calculated"
        )
        
        if factor:
            print(f"✅ Created factor: {factor.name} (ID: {factor.id})")
            
            # Check if dependencies were created
            from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel
            dependencies = session.query(FactorDependencyModel).filter(
                FactorDependencyModel.dependent_factor_id == factor.id
            ).all()
            
            print(f"📊 Found {len(dependencies)} dependencies:")
            for dep in dependencies:
                print(f"  - Dependency: factor_id {dep.independent_factor_id}, lag: {dep.lag}")
                
            if len(dependencies) >= 2:
                print("✅ SUCCESS: Factor dependencies were properly populated!")
                return True
            else:
                print("⚠️ WARNING: Expected 2 dependencies (start_price, end_price), found {len(dependencies)}")
                return False
        else:
            print("❌ ERROR: Failed to create return_daily factor")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = test_dependency_integration()
    if success:
        print("\n🎉 Test passed: Dependency integration working correctly!")
    else:
        print("\n💥 Test failed: Dependency integration needs fixing")
    
    sys.exit(0 if success else 1)