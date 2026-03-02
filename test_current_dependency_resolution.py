#!/usr/bin/env python3
"""
Test script to check current dependency resolution behavior.
Verifies if return_daily factor has proper dependencies in database.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_return_daily_dependencies():
    """Test current state of return_daily factor dependencies in database."""
    
    try:
        from src.application.services.database_service.database_service import DatabaseService
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        
        # Initialize database service and factory
        db_service = DatabaseService('sqlite')
        session = db_service.get_session()
        factory = RepositoryFactory(session)
        
        print("🔍 Testing current dependency resolution for return_daily factor...")
        
        # Find return_daily factor
        factor_repo = factory.factor_local_repo
        factors = factor_repo.get_all()
        
        return_daily = None
        for factor in factors:
            if factor.name == 'return_daily':
                return_daily = factor
                break
        
        if not return_daily:
            print("❌ return_daily factor not found in database")
            session.close()
            return False
        
        print(f"✅ Found return_daily factor: ID={return_daily.id}, group={return_daily.group}, subgroup={return_daily.subgroup}")
        
        # Check dependencies
        factor_dependency_repo = factory.factor_dependency_local_repo
        dependencies = factor_dependency_repo.get_by_dependent_factor_id(return_daily.id)
        
        print(f"📊 Dependencies found in database: {len(dependencies)}")
        
        if not dependencies:
            print("❌ No dependencies found in database for return_daily")
            print("💡 This explains why the system was only finding 'close' instead of structured dependencies")
            session.close()
            return False
        
        for dep in dependencies:
            independent_factor = factor_repo.get_by_id(dep.independent_factor_id)
            if independent_factor:
                print(f"  - {independent_factor.name} (ID: {independent_factor.id}, lag: {dep.lag})")
            else:
                print(f"  - Factor ID {dep.independent_factor_id} (lag: {dep.lag}) - MISSING!")
        
        session.close()
        
        if len(dependencies) == 2:
            print("✅ return_daily has expected 2 dependencies - system should work correctly")
            return True
        else:
            print(f"⚠️  return_daily has {len(dependencies)} dependencies, but FACTOR_LIBRARY defines 2")
            print("💡 Database needs to be populated with FACTOR_LIBRARY dependencies")
            return False
        
    except Exception as e:
        print(f"❌ Error testing dependencies: {e}")
        return False


def show_factor_library_config():
    """Show what return_daily should have according to FACTOR_LIBRARY."""
    
    try:
        from src.application.services.data.entities.factor.factor_library.finance.financial_assets.index_library import INDEX_LIBRARY
        
        return_daily_config = INDEX_LIBRARY.get('return_daily')
        if return_daily_config:
            print(f"\n📚 FACTOR_LIBRARY configuration for return_daily:")
            print(f"  Name: {return_daily_config.get('name')}")
            print(f"  Group: {return_daily_config.get('group')}")
            print(f"  Subgroup: {return_daily_config.get('subgroup')}")
            
            dependencies = return_daily_config.get('dependencies', {})
            print(f"  Dependencies ({len(dependencies)}):")
            
            for param_name, dep_config in dependencies.items():
                lag = dep_config.get('parameters', {}).get('lag')
                factor_name = dep_config.get('name')
                print(f"    - {param_name}: {factor_name} (lag: {lag})")
                
        else:
            print("❌ return_daily not found in INDEX_LIBRARY")
            
    except Exception as e:
        print(f"❌ Error showing FACTOR_LIBRARY config: {e}")


if __name__ == "__main__":
    print("🧪 Testing Current Dependency Resolution State")
    print("=" * 50)
    
    # Test current database state
    database_ok = test_return_daily_dependencies()
    
    # Show library configuration 
    show_factor_library_config()
    
    print("\n" + "=" * 50)
    if not database_ok:
        print("💡 SOLUTION: Run populate_factor_dependencies.py to sync FACTOR_LIBRARY → Database")
    else:
        print("✅ System should work correctly - dependencies are properly configured!")