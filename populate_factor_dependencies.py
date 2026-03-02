#!/usr/bin/env python3
"""
Script to populate FactorDependencyModel with dependencies from FACTOR_LIBRARY.
This creates a single source of truth in the database for factor dependency resolution.
"""

import sys
import os
from datetime import timedelta
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.services.data.entities.factor.factor_library.factor_definition_config import FACTOR_LIBRARY
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.application.services.database_service.database_service import DatabaseService


def get_factor_by_name_and_group(factory: RepositoryFactory, name: str, group: str, subgroup: str = None) -> Any:
    """Find factor in database by name, group, and optionally subgroup."""
    try:
        factor_repo = factory.factor_local_repo
        all_factors = factor_repo.get_all()
        
        for factor in all_factors:
            if (factor.name == name and 
                factor.group == group and 
                (subgroup is None or factor.subgroup == subgroup)):
                return factor
        return None
    except Exception as e:
        print(f"Error finding factor {name}/{group}/{subgroup}: {e}")
        return None


def populate_dependencies_from_library():
    """Populate FactorDependencyModel from FACTOR_LIBRARY configuration."""
    
    try:
        # Initialize database service and get session
        db_service = DatabaseService('sqlite')
        session = db_service.get_session()
        
        # Initialize repository factory
        factory = RepositoryFactory(session)
        factor_dependency_repo = factory.factor_dependency_local_repo
        
        print("🔄 Populating factor dependencies from FACTOR_LIBRARY...")
        
        # Track statistics
        total_processed = 0
        dependencies_created = 0
        errors = 0
        
        # Process each library section
        for library_name, library_data in FACTOR_LIBRARY.items():
            print(f"\n📚 Processing {library_name}...")
            
            if not isinstance(library_data, dict):
                continue
                
            for factor_name, factor_config in library_data.items():
                total_processed += 1
                print(f"  🔍 Processing factor: {factor_name}")
                
                try:
                    # Get factor dependencies from config
                    dependencies_config = factor_config.get('dependencies', {})
                    
                    if not dependencies_config:
                        print(f"    ⚪ No dependencies for {factor_name}")
                        continue
                    
                    # Find the dependent factor in database
                    dependent_factor = get_factor_by_name_and_group(
                        factory, 
                        factor_config.get('name', factor_name),
                        factor_config.get('group', ''),
                        factor_config.get('subgroup', '')
                    )
                    
                    if not dependent_factor:
                        print(f"    ❌ Dependent factor not found in database: {factor_name}")
                        errors += 1
                        continue
                    
                    print(f"    ✅ Found dependent factor: {dependent_factor.name} (ID: {dependent_factor.id})")
                    
                    # Process each dependency
                    for param_name, dep_config in dependencies_config.items():
                        try:
                            # Find the independent factor in database
                            independent_factor = get_factor_by_name_and_group(
                                factory,
                                dep_config.get('name', ''),
                                dep_config.get('group', ''),
                                dep_config.get('subgroup', '')
                            )
                            
                            if not independent_factor:
                                print(f"      ❌ Independent factor not found: {dep_config}")
                                errors += 1
                                continue
                            
                            # Extract lag from parameters
                            lag = None
                            parameters = dep_config.get('parameters', {})
                            if 'lag' in parameters:
                                lag = parameters['lag']
                                if isinstance(lag, timedelta):
                                    print(f"      ⏰ Found lag: {lag}")
                                else:
                                    print(f"      ⚠️  Invalid lag type: {type(lag)} - {lag}")
                                    lag = None
                            
                            # Check if dependency already exists
                            existing_deps = factor_dependency_repo.get_by_dependent_factor_id(dependent_factor.id)
                            dependency_exists = any(
                                dep.independent_factor_id == independent_factor.id and dep.lag == lag
                                for dep in existing_deps
                            )
                            
                            if dependency_exists:
                                print(f"      ⚪ Dependency already exists: {dependent_factor.name} → {independent_factor.name}")
                                continue
                            
                            # Create new dependency
                            from src.domain.entities.factor.factor_dependency import FactorDependency
                            
                            new_dependency = FactorDependency(
                                dependent_factor_id=dependent_factor.id,
                                independent_factor_id=independent_factor.id,
                                lag=lag
                            )
                            
                            # Save to database
                            saved_dependency = factor_dependency_repo.create(new_dependency)
                            dependencies_created += 1
                            
                            print(f"      ✅ Created dependency: {dependent_factor.name} → {independent_factor.name} (lag: {lag})")
                            
                        except Exception as dep_error:
                            print(f"      ❌ Error processing dependency {param_name}: {dep_error}")
                            errors += 1
                            continue
                    
                except Exception as factor_error:
                    print(f"    ❌ Error processing factor {factor_name}: {factor_error}")
                    errors += 1
                    continue
        
        # Print summary
        print(f"\n📊 Summary:")
        print(f"  Total factors processed: {total_processed}")
        print(f"  Dependencies created: {dependencies_created}")
        print(f"  Errors: {errors}")
        print(f"  Success rate: {((total_processed - errors) / max(total_processed, 1) * 100):.1f}%")
        
        if dependencies_created > 0:
            print(f"\n✅ Successfully populated {dependencies_created} factor dependencies!")
            
            # Test the return_daily factor specifically
            test_return_daily_dependencies(factory)
        else:
            print(f"\n⚠️  No new dependencies were created.")
            
        # Close the session
        session.close()
        
    except Exception as e:
        print(f"❌ Fatal error during population: {e}")
        session.close()
        sys.exit(1)


def test_return_daily_dependencies(factory: RepositoryFactory):
    """Test that return_daily factor dependencies were created correctly."""
    print(f"\n🧪 Testing return_daily factor dependencies...")
    
    try:
        # Find return_daily factor
        return_daily_factor = get_factor_by_name_and_group(factory, 'return_daily', 'return', 'daily')
        
        if not return_daily_factor:
            print("❌ return_daily factor not found in database")
            return
        
        print(f"✅ Found return_daily factor (ID: {return_daily_factor.id})")
        
        # Get its dependencies
        factor_dependency_repo = factory.factor_dependency_local_repo
        dependencies = factor_dependency_repo.get_by_dependent_factor_id(return_daily_factor.id)
        
        print(f"📋 Found {len(dependencies)} dependencies for return_daily:")
        
        for dep in dependencies:
            independent_factor = factory.factor_local_repo.get_by_id(dep.independent_factor_id)
            if independent_factor:
                print(f"  - {independent_factor.name} (lag: {dep.lag})")
            else:
                print(f"  - Factor ID {dep.independent_factor_id} (lag: {dep.lag})")
        
        # Expected: 2 dependencies (start_price and end_price)
        if len(dependencies) == 2:
            print("✅ return_daily has expected 2 dependencies")
        else:
            print(f"⚠️  return_daily has {len(dependencies)} dependencies, expected 2")
        
    except Exception as e:
        print(f"❌ Error testing return_daily dependencies: {e}")


if __name__ == "__main__":
    populate_dependencies_from_library()