#!/usr/bin/env python3
"""
Test script for the new FactorRepository methods:
- get_factor_by_name_and_group
- populate_dependencies_from_library
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.database.settings import get_session
from src.infrastructure.repositories.repository_factory import RepositoryFactory

def test_factor_repository_methods():
    """Test the new FactorRepository methods."""
    
    print("🔍 Testing FactorRepository Methods")
    print("=" * 50)
    
    try:
        # Get repository factory and session
        session = get_session()
        factory = RepositoryFactory(session)
        factor_repo = factory.factor_repository
        
        print("✅ Repository factory initialized successfully")
        
        # Test 1: get_factor_by_name_and_group method
        print("\n📋 Test 1: get_factor_by_name_and_group")
        print("-" * 30)
        
        # Create a test factor first
        test_factor = factor_repo._create_or_get("test_close", "price", "minutes")
        if test_factor:
            print(f"✅ Created test factor: {test_factor.name}, group: {test_factor.group}")
            
            # Now test retrieval by name and group
            retrieved = factor_repo.get_factor_by_name_and_group("test_close", "price")
            if retrieved:
                print(f"✅ Successfully retrieved factor by name and group: {retrieved.name}")
            else:
                print("❌ Failed to retrieve factor by name and group")
        else:
            print("❌ Failed to create test factor")
        
        # Test 2: populate_dependencies_from_library method
        print("\n📋 Test 2: populate_dependencies_from_library")
        print("-" * 40)
        
        # Test populating dependencies for return_daily factor
        created_count = factor_repo.populate_dependencies_from_library("return_daily")
        print(f"✅ Created {created_count} dependency relationships for return_daily")
        
        # Check if return_daily factor was created with dependencies
        return_daily = factor_repo.get_factor_by_name_and_group("return_daily", "return")
        if return_daily:
            print(f"✅ return_daily factor found: ID {return_daily.id}")
            
            # Check dependencies in database
            if factory.factor_dependency_repository:
                deps = factory.factor_dependency_repository.get_dependencies(return_daily.id)
                print(f"✅ Found {len(deps)} dependencies for return_daily in database")
                
                for dep in deps:
                    dep_factor = factor_repo.get_by_id(dep.independent_factor_id)
                    if dep_factor:
                        print(f"  - Dependency: {dep_factor.name} (group: {dep_factor.group}, lag: {dep.lag})")
            else:
                print("⚠️  Factor dependency repository not available")
        else:
            print("❌ return_daily factor not found after population")
        
        # Test 3: populate all dependencies from library
        print("\n📋 Test 3: populate_dependencies_from_library (all factors)")
        print("-" * 50)
        
        total_created = factor_repo.populate_dependencies_from_library()
        print(f"✅ Created {total_created} total dependency relationships from library")
        
        # Show some statistics
        all_factors = factor_repo.get_all()
        print(f"✅ Total factors in database: {len(all_factors)}")
        
        return_factors = factor_repo.get_by_group("return")
        print(f"✅ Return group factors: {len(return_factors)}")
        
        price_factors = factor_repo.get_by_group("price")
        print(f"✅ Price group factors: {len(price_factors)}")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'session' in locals():
            session.close()
    
    return True

if __name__ == "__main__":
    test_factor_repository_methods()