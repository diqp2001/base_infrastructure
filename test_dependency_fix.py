#!/usr/bin/env python3
"""
Test script to verify factor dependency population fix
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.repositories.local_repo.factory import RepositoryFactory
from src.domain.entities.factor.factor import Factor
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.index_library import INDEX_LIBRARY

def test_dependency_fix():
    """Test the dependency population fix"""
    print("=== TESTING DEPENDENCY POPULATION FIX ===\n")
    
    try:
        # Create database session
        engine = create_engine('sqlite:///base_infra.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create repository factory
        factory = RepositoryFactory(session)
        factor_repo = factory.get_local_repository(Factor)
        
        print("1. Testing _get_factor_config_from_library method:")
        return_daily_config = factor_repo._get_factor_config_from_library("return_daily")
        if return_daily_config:
            print("   ✅ Found return_daily config in library")
            print(f"   Group: {return_daily_config.get('group')}")
            print(f"   Dependencies: {list(return_daily_config.get('dependencies', {}).keys())}")
        else:
            print("   ❌ return_daily config NOT FOUND")
        
        print("\n2. Testing _populate_single_factor_dependencies method:")
        count = factor_repo._populate_single_factor_dependencies("return_daily")
        print(f"   Created {count} dependency relationships for return_daily")
        
        if count > 0:
            print("   ✅ Dependencies populated successfully")
        else:
            print("   ❌ No dependencies were populated")
            
        print("\n3. Checking database state after population:")
        from sqlalchemy import text
        
        # Query dependencies for return_daily factor
        result = session.execute(text("""
            SELECT 
                fd.id,
                fd.dependent_factor_id,
                fd.independent_factor_id,
                fd.lag,
                f1.name as dependent_name,
                f2.name as independent_name,
                f2.group as independent_group
            FROM factor_dependencies fd
            JOIN factors f1 ON fd.dependent_factor_id = f1.id
            JOIN factors f2 ON fd.independent_factor_id = f2.id
            WHERE f1.name = 'return_daily' AND f1.factor_type = 'index_price_return_factor'
        """))
        deps = result.fetchall()
        
        print(f"   Found {len(deps)} dependencies for return_daily:")
        for dep in deps:
            print(f"      {dep[4]} -> {dep[5]} (group: {dep[6]}, lag: {dep[3]})")
            
        if len(deps) == 2:
            print("   ✅ EXPECTED: 2 dependencies found")
        else:
            print(f"   ❌ UNEXPECTED: {len(deps)} dependencies (expected 2)")
        
        session.close()
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dependency_fix()