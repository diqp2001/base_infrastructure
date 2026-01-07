#!/usr/bin/env python3
"""
Test script to verify metaclass conflicts are resolved.
"""

def test_imports():
    """Test that we can import models without metaclass conflicts."""
    print("Testing imports...")
    
    try:
        # Test domain entities import
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare as DomainCompanyShare
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyStock as DomainCompanyStock
        print("✅ Domain entities import successfully")
        
        # Test ORM models import
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare as ORMCompanyShare
        from src.infrastructure.models.finance.financial_assets.company_stock import CompanyStock as ORMCompanyStock
        print("✅ ORM models import successfully")
        
        # Test mapper import
        from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper, CompanyStockMapper
        print("✅ Mappers import successfully")
        
        # Test that they are different classes
        print(f"Domain CompanyShare: {DomainCompanyShare}")
        print(f"ORM CompanyShare: {ORMCompanyShare}")
        print(f"Are they the same class? {DomainCompanyShare is ORMCompanyShare}")
        
        if DomainCompanyShare is ORMCompanyShare:
            print("❌ ERROR: Domain and ORM classes are the same - metaclass issue not fixed!")
            return False
        else:
            print("✅ Domain and ORM classes are separate - metaclass issue resolved!")
            
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        return False

def test_mapper_conversion():
    """Test mapper conversion between domain and ORM."""
    print("\nTesting mapper conversion...")
    
    try:
        from datetime import datetime
        from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare as DomainCompanyShare
        from src.infrastructure.models.finance.financial_assets.company_share import CompanyShare as ORMCompanyShare
        from src.infrastructure.repositories.mappers.finance.financial_assets.company_share_mapper import CompanyShareMapper
        
        # Create a domain entity
        domain_entity = DomainCompanyShare(
            id=1,
            ticker="AAPL",
            exchange_id=1,
            company_id=1,
            start_date=datetime(2020, 1, 1),
            end_date=None
        )
        print(f"✅ Created domain entity: {domain_entity}")
        
        # Convert to ORM
        orm_entity = CompanyShareMapper.to_orm(domain_entity)
        print(f"✅ Converted to ORM: {orm_entity}")
        
        # Convert back to domain
        domain_entity_2 = CompanyShareMapper.to_domain(orm_entity)
        print(f"✅ Converted back to domain: {domain_entity_2}")
        
        # Verify round-trip consistency
        if (domain_entity.id == domain_entity_2.id and 
            domain_entity.ticker == domain_entity_2.ticker and
            domain_entity.exchange_id == domain_entity_2.exchange_id):
            print("✅ Round-trip conversion successful!")
            return True
        else:
            print("❌ Round-trip conversion failed - data mismatch!")
            return False
            
    except Exception as e:
        print(f"❌ Mapper test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("METACLASS CONFLICT FIX VERIFICATION")
    print("=" * 50)
    
    success1 = test_imports()
    success2 = test_mapper_conversion()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED - Metaclass conflicts resolved!")
    else:
        print("❌ SOME TESTS FAILED - Check implementation")
    print("=" * 50)