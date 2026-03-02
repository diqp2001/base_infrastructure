#!/usr/bin/env python3
"""
Script to manually populate return_daily dependencies with proper lag values
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import timedelta
from src.infrastructure.repositories.local_repo.factory import RepositoryFactory
from src.domain.entities.factor.factor import Factor
from src.infrastructure.models.factor.factor_dependency import FactorDependencyModel

def populate_return_daily_dependencies():
    """Manually populate return_daily dependencies with proper lag values"""
    print("=== POPULATING RETURN_DAILY DEPENDENCIES ===\n")
    
    try:
        # Create database session
        engine = create_engine('sqlite:///base_infra.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create repository factory
        factory = RepositoryFactory(session)
        factor_repo = factory.get_local_repository(Factor)
        
        print("1. Populating dependencies for return_daily factor:")
        count = factor_repo.populate_dependencies_from_library("return_daily")
        
        print(f"\n2. Total dependencies created: {count}")
        
        print("\n3. Verifying database state:")
        # Query all dependencies with lag information
        result = session.execute(text("""
            SELECT 
                fd.id,
                fd.dependent_factor_id,
                fd.independent_factor_id,
                fd.lag,
                f1.name as dependent_name,
                f1.factor_type as dependent_type,
                f2.name as independent_name,
                f2.group as independent_group,
                f2.subgroup as independent_subgroup
            FROM factor_dependencies fd
            JOIN factors f1 ON fd.dependent_factor_id = f1.id
            JOIN factors f2 ON fd.independent_factor_id = f2.id
            WHERE f1.name = 'return_daily' AND f1.factor_type = 'index_price_return_factor'
            ORDER BY fd.id
        """))
        deps = result.fetchall()
        
        print(f"   Found {len(deps)} dependencies for return_daily:")
        for dep in deps:
            print(f"      ID {dep[0]}: {dep[4]} -> {dep[6]} ({dep[7]}.{dep[8]}) - lag: {dep[3]}")
            
        # Expected: 2 dependencies (start_price with 2-day lag, end_price with 1-day lag)
        if len(deps) == 2:
            print("\n✅ SUCCESS: 2 dependencies found as expected")
            # Check if lags are properly set
            lags_found = [dep[3] for dep in deps if dep[3] is not None]
            print(f"   Lag values: {lags_found}")
        elif len(deps) == 1:
            print(f"\n❌ ISSUE: Only 1 dependency found (was {deps[0][6]})")
        else:
            print(f"\n❌ ISSUE: {len(deps)} dependencies found (expected 2)")
        
        print("\n4. All factor dependencies in database:")
        result = session.execute(text("""
            SELECT 
                fd.dependent_factor_id,
                f1.name as dependent_name,
                COUNT(*) as dependency_count
            FROM factor_dependencies fd
            JOIN factors f1 ON fd.dependent_factor_id = f1.id
            GROUP BY fd.dependent_factor_id, f1.name
            ORDER BY fd.dependent_factor_id
        """))
        all_deps = result.fetchall()
        
        for dep in all_deps:
            print(f"   Factor ID {dep[0]} ({dep[1]}): {dep[2]} dependencies")
        
        session.close()
        print("\n=== DONE ===")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    populate_return_daily_dependencies()