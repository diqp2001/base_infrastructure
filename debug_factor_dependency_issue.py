#!/usr/bin/env python3
"""
Debug Factor Dependency Issue
Investigate why return_daily factor only has 1 dependency instead of 2 structured dependencies
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel
from src.application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY
from src.application.services.data.entities.factor.factor_library.finance.financial_assets.index_library import INDEX_LIBRARY

def debug_factor_dependencies():
    """Debug current state of factor dependencies"""
    print("=== DEBUGGING FACTOR DEPENDENCY ISSUE ===\n")
    
    # 1. Check INDEX_LIBRARY configuration for return_daily
    print("1. INDEX_LIBRARY Configuration for return_daily:")
    return_daily_config = INDEX_LIBRARY.get('return_daily')
    if return_daily_config:
        print(f"   Factor: {return_daily_config.get('name')}")
        print(f"   Group: {return_daily_config.get('group')}")
        print(f"   Subgroup: {return_daily_config.get('subgroup')}")
        print(f"   Dependencies: {return_daily_config.get('dependencies')}")
        
        deps = return_daily_config.get('dependencies', {})
        for param_name, dep_config in deps.items():
            print(f"      {param_name}: {dep_config.get('name')} (lag: {dep_config.get('parameters', {}).get('lag')})")
    else:
        print("   return_daily NOT FOUND in INDEX_LIBRARY")
    
    print("\n2. FACTOR_LIBRARY Structure:")
    for lib_name, lib_content in FACTOR_LIBRARY.items():
        print(f"   {lib_name}: {type(lib_content)}")
        if lib_name == "index_library" and hasattr(lib_content, '__len__'):
            print(f"      Contains {len(lib_content)} factors")
    
    # 3. Check database schema
    try:
        engine = create_engine('sqlite:///base_infra.db')
        with engine.connect() as conn:
            print("\n3. Database Schema Check:")
            
            # Check factor_dependencies table structure
            result = conn.execute(text("PRAGMA table_info(factor_dependencies)"))
            columns = result.fetchall()
            print("   factor_dependencies table columns:")
            for col in columns:
                print(f"      {col[1]} ({col[2]}) - nullable: {col[3] == 0}")
            
            # Check current dependencies for factor ID 14
            print("\n4. Current Dependencies for Factor ID 14 (return_daily):")
            result = conn.execute(text("""
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
                WHERE fd.dependent_factor_id = 14
            """))
            deps = result.fetchall()
            
            if deps:
                for dep in deps:
                    print(f"   Dependency {dep[0]}: {dep[4]} -> {dep[5]} (group: {dep[6]}, lag: {dep[3]})")
            else:
                print("   No dependencies found for factor ID 14")
            
            # Check all factors with return group
            print("\n5. All Factors in 'return' Group:")
            result = conn.execute(text("""
                SELECT id, name, subgroup, factor_type 
                FROM factors 
                WHERE [group] = 'return' 
                ORDER BY id
            """))
            factors = result.fetchall()
            for factor in factors:
                print(f"   ID {factor[0]}: {factor[1]} ({factor[2]}) - {factor[3]}")
                
            # Check close price factors (potential dependencies)
            print("\n6. Potential Dependency Factors (close, price group):")
            result = conn.execute(text("""
                SELECT id, name, [group], subgroup, factor_type 
                FROM factors 
                WHERE name = 'close' OR [group] = 'price'
                ORDER BY id
            """))
            price_factors = result.fetchall()
            for factor in price_factors:
                print(f"   ID {factor[0]}: {factor[1]} ({factor[2]}.{factor[3]}) - {factor[4]}")
                
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    debug_factor_dependencies()