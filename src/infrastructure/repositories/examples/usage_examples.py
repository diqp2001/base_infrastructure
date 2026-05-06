"""
Usage Examples - Demonstrates the new repository factory pattern.

This shows how to use the new type-based repository factory instead of
the old string-based approach.
"""

from sqlalchemy.orm import Session
from typing import Optional

# New factory
from ..new_repository_factory import RepositoryFactory, create_repository_factory

# Domain ports (interfaces)
from src.domain.ports.finance.instrument_port import InstrumentPort
from src.domain.ports.finance.financial_assets.financial_asset_port import FinancialAssetPort

# Concrete repository classes
from ..local_repo.finance.instrument_repository import InstrumentRepository
from ..local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from ..ibkr_repo.finance.instrument_repository import IBKRInstrumentRepository


def example_basic_usage(session: Session, ibkr_client=None):
    """Example of basic repository factory usage."""
    
    # Create factory
    factory = create_repository_factory(session, ibkr_client)
    
    # Get repositories by interface (recommended)
    instrument_repo = factory.get(InstrumentPort)
    financial_asset_repo = factory.get(FinancialAssetPort)
    
    # Get repositories by concrete class
    company_share_repo = factory.get(CompanyShareRepository)
    
    # Use repositories
    if instrument_repo:
        instruments = instrument_repo.get_all()
        print(f"Found {len(instruments)} instruments")
    
    if financial_asset_repo:
        assets = financial_asset_repo.get_all()
        print(f"Found {len(assets)} financial assets")
    
    return factory


def example_data_source_specific_usage(session: Session, ibkr_client):
    """Example of data source specific repository access."""
    
    factory = RepositoryFactory(session, ibkr_client)
    
    # Get local (SQLAlchemy) repositories
    local_instrument_repo = factory.get_local(InstrumentRepository)
    
    # Get IBKR repositories
    ibkr_instrument_repo = factory.get_ibkr(IBKRInstrumentRepository)
    
    # Check availability
    if factory.has_ibkr_client():
        print("IBKR repositories available")
    else:
        print("Only local repositories available")
    
    return factory


def example_migration_from_old_factory():
    """Example showing migration from old string-based factory."""
    
    # OLD WAY (what you want to replace):
    # factory = OldRepositoryFactory(session, ibkr_client)
    # instrument_repo = factory.instrument_local_repo
    # factor_repo = factory.factor_local_repo
    
    # NEW WAY:
    session = None  # Your SQLAlchemy session
    ibkr_client = None  # Your IBKR client
    
    factory = RepositoryFactory(session, ibkr_client)
    
    # Type-safe repository access
    instrument_repo = factory.get(InstrumentPort)
    company_share_repo = factory.get(CompanyShareRepository)
    
    # Clean, no string keys, no property boilerplate
    print(f"Available repository types: {len(factory.list_available_types())}")
    
    return factory


def example_adding_new_repository():
    """Example of how easy it is to add new repositories."""
    
    # To add a new repository, you only need to:
    # 1. Add import to the appropriate provider
    # 2. Add one line in provider._create_repositories()
    
    # That's it! No:
    # - String key mapping
    # - Property method creation  
    # - Manual instantiation in factory
    # - Duplication between local/IBKR
    
    print("Adding new repositories is now trivial!")


def example_service_layer_usage(session: Session):
    """Example of how services would use the new factory."""
    
    class TradingService:
        """Example service using repository factory."""
        
        def __init__(self, repository_factory: RepositoryFactory):
            self.factory = repository_factory
        
        def get_portfolio_instruments(self, portfolio_id: int):
            """Get all instruments for a portfolio."""
            # Type-safe repository access
            instrument_repo = self.factory.get(InstrumentPort)
            if not instrument_repo:
                return []
            
            # Use repository methods
            return instrument_repo.get_all()
        
        def create_instrument_from_ibkr(self, symbol: str):
            """Create instrument using IBKR data."""
            # Get IBKR-specific repository
            ibkr_repo = self.factory.get(IBKRInstrumentRepository)
            if not ibkr_repo:
                print("IBKR not available")
                return None
            
            return ibkr_repo._create_or_get(symbol)
    
    # Usage
    factory = RepositoryFactory(session)
    service = TradingService(factory)
    
    instruments = service.get_portfolio_instruments(1)
    print(f"Portfolio has {len(instruments)} instruments")
    
    return service


if __name__ == "__main__":
    # Demo the new factory pattern
    print("=== New Repository Factory Examples ===")
    
    # Mock session for demo
    session = None
    ibkr_client = None
    
    print("\n1. Basic Usage:")
    try:
        factory = example_basic_usage(session, ibkr_client)
        print("✓ Basic usage example completed")
    except Exception as e:
        print(f"⚠ Basic usage example failed: {e}")
    
    print("\n2. Migration Example:")
    try:
        factory = example_migration_from_old_factory()
        print("✓ Migration example completed")
    except Exception as e:
        print(f"⚠ Migration example failed: {e}")
    
    print("\n3. Adding New Repositories:")
    example_adding_new_repository()
    
    print(f"\n4. Service Layer Usage:")
    try:
        service = example_service_layer_usage(session)
        print("✓ Service layer example completed")
    except Exception as e:
        print(f"⚠ Service layer example failed: {e}")
    
    print("\n=== Summary ===")
    print("✓ Type-based dependency resolution")
    print("✓ No string keys")
    print("✓ Clean provider pattern")
    print("✓ Easy extensibility")
    print("✓ DDD-compliant design")