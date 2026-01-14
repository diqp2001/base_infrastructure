"""
Test script for the new dependency resolution system.

This demonstrates automatic foreign key dependency resolution when creating SPX entities.
"""

from datetime import date, datetime
from src.application.services.database_service.database_service import DatabaseService
from src.infrastructure.repositories.dependency_registry import DependencyRegistry
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.index_repository import IndexRepository
from infrastructure.repositories.local_repo.finance.financial_assets.derivatives.future.future_repository import FutureRepository


def test_dependency_resolution():
    """Test the dependency resolution system with SPX entities."""
    print("Testing Dependency Resolution System")
    print("=" * 50)
    
    # Initialize database and repositories
    database_service = DatabaseService('sqlite')
    dependency_registry = DependencyRegistry(database_service.session)
    
    print("\n1. Testing SPX Index Creation with Auto-Dependency Resolution")
    print("-" * 60)
    
    try:
        # Test SPX Index creation
        spx_index = dependency_registry.create_or_get_with_dependencies(
            'index',
            symbol='SPX',
            name='S&P 500 Index',
            index_type='Stock',
            currency='USD',
            exchange='CBOE'
        )
        
        if spx_index:
            print(f"✅ SPX Index created successfully:")
            print(f"   ID: {spx_index.id}")
            print(f"   Symbol: {spx_index.symbol}")
            print(f"   Name: {spx_index.name}")
        else:
            print("❌ Failed to create SPX Index")
            
    except Exception as e:
        print(f"❌ Error creating SPX Index: {str(e)}")
    
    print("\n2. Testing SPX Future Creation with Auto-Dependency Resolution")
    print("-" * 60)
    
    try:
        # Test SPX Future creation
        spx_future = dependency_registry.create_or_get_with_dependencies(
            'future',
            symbol='ESZ5',
            contract_name='E-mini S&P 500 December 2025',
            future_type='INDEX',
            underlying_asset='SPX',
            exchange='CME',
            currency='USD'
        )
        
        if spx_future:
            print(f"✅ SPX Future created successfully:")
            print(f"   ID: {spx_future.id}")
            print(f"   Symbol: {spx_future.symbol}")
            print(f"   Contract Name: {spx_future.contract_name}")
            print(f"   Underlying Asset: {spx_future.underlying_asset}")
        else:
            print("❌ Failed to create SPX Future")
            
    except Exception as e:
        print(f"❌ Error creating SPX Future: {str(e)}")
    
    print("\n3. Testing CompanyShare Creation with Full Dependency Cascade")
    print("-" * 60)
    
    try:
        # Test creating a company share for SPX (hypothetical)
        company_share_repo = CompanyShareRepository(database_service.session)
        
        spx_share = company_share_repo._create_or_get(
            ticker='SPX',
            company_name='Standard & Poor\'s Corporation',
            exchange_name='CBOE',
            country_name='United States',
            industry_name='Financial Services',
            start_date=date.today()
        )
        
        if spx_share:
            print(f"✅ SPX CompanyShare created successfully:")
            print(f"   ID: {spx_share.id}")
            print(f"   Ticker: {spx_share.ticker}")
            print(f"   Exchange ID: {spx_share.exchange_id}")
            print(f"   Company ID: {spx_share.company_id}")
        else:
            print("❌ Failed to create SPX CompanyShare")
            
    except Exception as e:
        print(f"❌ Error creating SPX CompanyShare: {str(e)}")
    
    print("\n4. Testing Dependency Existence Verification")
    print("-" * 60)
    
    try:
        # Check that dependencies were created correctly
        country_repo = dependency_registry.get_repository('country')
        industry_repo = dependency_registry.get_repository('industry')
        company_repo = dependency_registry.get_repository('company')
        exchange_repo = dependency_registry.get_repository('exchange')
        
        # Verify Country exists
        usa_country = country_repo.get_by_name('United States')
        if usa_country:
            print(f"✅ Country dependency created: {usa_country.name} (ID: {usa_country.id})")
        
        # Verify Industry exists
        tech_industry = industry_repo.get_by_name('Technology')
        if tech_industry:
            print(f"✅ Industry dependency created: {tech_industry.name} (ID: {tech_industry.id})")
        
        # Verify Company exists
        spx_company = company_repo.get_by_name('SPX Inc.')
        if spx_company and len(spx_company) > 0:
            print(f"✅ Company dependency created: {spx_company[0].name} (ID: {spx_company[0].id})")
        
        # Verify Exchange exists
        cboe_exchange = exchange_repo.get_by_name('CBOE')
        if cboe_exchange and len(cboe_exchange) > 0:
            print(f"✅ Exchange dependency created: {cboe_exchange[0].name} (ID: {cboe_exchange[0].id})")
            
    except Exception as e:
        print(f"❌ Error verifying dependencies: {str(e)}")
    
    print("\n5. Testing Duplicate Entity Prevention")
    print("-" * 60)
    
    try:
        # Try creating the same entities again - should return existing ones
        spx_index_2 = dependency_registry.create_or_get_with_dependencies(
            'index',
            symbol='SPX',
            name='S&P 500 Index'
        )
        
        spx_future_2 = dependency_registry.create_or_get_with_dependencies(
            'future',
            symbol='ESZ5'
        )
        
        if spx_index and spx_index_2 and spx_index.id == spx_index_2.id:
            print(f"✅ Duplicate prevention working for Index: Same ID {spx_index.id}")
        
        if spx_future and spx_future_2 and spx_future.id == spx_future_2.id:
            print(f"✅ Duplicate prevention working for Future: Same ID {spx_future.id}")
            
    except Exception as e:
        print(f"❌ Error testing duplicates: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Dependency Resolution Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    test_dependency_resolution()