#!/usr/bin/env python3
"""
Utility to fix missing financial asset ID 3 issue.

This script creates a default company share with ID 3 to resolve the factor creation dependency loop.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src.domain.database import Database
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare

def create_missing_financial_asset_id_3():
    """Create a default financial asset with ID 3 to fix the dependency loop."""
    
    print("Creating missing financial asset with ID 3...")
    
    try:
        # Setup database
        db = Database('sqlite')
        db.initialize_database_and_create_all_tables()
        session = db.SessionLocal()
        
        try:
            # Create repository factory
            factory = RepositoryFactory(session)
            
            # Check if ID 3 already exists
            existing_asset = factory.financial_asset_local_repo.get_by_id(3)
            if existing_asset:
                print(f"Financial asset with ID 3 already exists: {existing_asset}")
                return existing_asset
            
            # Create a default company share with ID 3
            # First ensure dependencies exist
            
            # Get or create default exchange
            exchange_repo = factory.exchange_local_repo
            default_exchange = exchange_repo.get_or_create("NYSE", "New York Stock Exchange")
            
            # Get or create default currency
            currency_repo = factory.currency_local_repo
            default_currency = currency_repo.get_or_create("USD", "United States Dollar")
            
            # Get or create default company
            company_repo = factory.company_local_repo
            default_company = company_repo.get_or_create(
                name="Default Test Company",
                description="Default company for factor testing",
                sector_id=1,
                industry_id=1
            )
            
            # Create the company share entity with ID 3
            company_share = CompanyShare(
                id=3,
                symbol="TESTF",  # Test Factor symbol
                name="Test Factor Share",
                description="Default financial asset for factor testing",
                exchange_id=default_exchange.id if default_exchange else 1,
                company_id=default_company.id if default_company else 1,
                currency_id=default_currency.id if default_currency else 1,
                start_date=datetime.now().date(),
                end_date=None
            )
            
            # Add to database using company share repository
            company_share_repo = factory.company_share_local_repo
            created_share = company_share_repo.add(company_share)
            
            print(f"Successfully created financial asset with ID 3: {created_share}")
            session.commit()
            
            return created_share
            
        except Exception as e:
            session.rollback()
            print(f"Error creating financial asset: {e}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        print(f"Database setup error: {e}")
        raise

def main():
    """Main function to fix the missing financial asset issue."""
    print("=== Financial Asset ID 3 Fix Utility ===")
    
    try:
        result = create_missing_financial_asset_id_3()
        if result:
            print(f"\n✅ Successfully fixed missing financial asset issue!")
            print(f"   Created/found asset: {result.symbol} (ID: {result.id})")
        else:
            print(f"\n❌ Failed to create financial asset with ID 3")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()