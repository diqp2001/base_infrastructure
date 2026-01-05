"""
IBKR Repository Usage Examples

This file demonstrates how to use the IBKR repository architecture pattern
in different configurations: local-only and IBKR-backed.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from composition.repository_factory import RepositoryFactory
from application.services.database_service.database_service import DatabaseService


def example_local_configuration():
    """
    Example of local-only configuration.
    
    In this setup, all data comes from the local database.
    No external API calls are made.
    """
    print("=== Local-only Configuration ===")
    
    # Setup database
    database_service = DatabaseService('sqlite')  # or 'sqlserver'
    session = database_service.session
    
    try:
        # Create financial asset service with local repositories
        service = RepositoryFactory.create_financial_asset_service(
            session=session,
            use_ibkr=False  # Local-only
        )
        
        print("Service created with local repositories")
        
        # Test operations
        print("\n--- Testing local operations ---")
        
        # Try to get/create an index future
        future = service.get_or_create_index_future("ESZ25")
        if future:
            print(f"Created/retrieved future: {future.symbol}")
        else:
            print("Failed to create/retrieve future (expected with stub implementation)")
        
        # Get portfolio summary
        summary = service.get_portfolio_summary()
        print(f"Portfolio summary: {summary}")
        
        print("Local configuration test completed successfully")
        
    except Exception as e:
        print(f"Error in local configuration: {e}")
    finally:
        session.close()


def example_ibkr_configuration():
    """
    Example of IBKR-backed configuration.
    
    In this setup, data acquisition comes from IBKR API,
    but persistence is handled by local repositories.
    """
    print("\n=== IBKR-backed Configuration ===")
    
    # Setup database
    database_service = DatabaseService('sqlite')
    session = database_service.session
    
    # Mock IBKR client (in real implementation, you'd use actual IBKR client)
    class MockIBKRClient:
        def __init__(self):
            self.connected = False
        
        def connect(self):
            self.connected = True
            print("Connected to IBKR (mock)")
        
        def disconnect(self):
            self.connected = False
            print("Disconnected from IBKR (mock)")
    
    ibkr_client = MockIBKRClient()
    
    try:
        # Connect to IBKR
        ibkr_client.connect()
        
        # Create financial asset service with IBKR repositories
        service = RepositoryFactory.create_financial_asset_service(
            session=session,
            use_ibkr=True,  # IBKR-backed
            ibkr_client=ibkr_client
        )
        
        print("Service created with IBKR-backed repositories")
        
        # Test operations
        print("\n--- Testing IBKR operations ---")
        
        # Try to get/create an index future (will use IBKR repository)
        future = service.get_or_create_index_future("ESZ25")
        if future:
            print(f"Created/retrieved future via IBKR: {future.symbol}")
        else:
            print("Future creation/retrieval completed (check implementation)")
        
        # Test different symbols
        symbols = ["NQH25", "RTYH25", "YMZ25"]
        for symbol in symbols:
            print(f"Processing {symbol}...")
            result = service.get_or_create_index_future(symbol)
            if result:
                print(f"  Success: {result.symbol}")
            else:
                print(f"  Completed processing for {symbol}")
        
        # Get portfolio summary
        summary = service.get_portfolio_summary()
        print(f"Portfolio summary: {summary}")
        
        print("IBKR configuration test completed successfully")
        
    except Exception as e:
        print(f"Error in IBKR configuration: {e}")
    finally:
        if ibkr_client.connected:
            ibkr_client.disconnect()
        session.close()


def example_service_layer_independence():
    """
    Demonstrate that the service layer code never changes,
    regardless of the repository implementation.
    """
    print("\n=== Service Layer Independence Demonstration ===")
    
    database_service = DatabaseService('sqlite')
    session = database_service.session
    
    # Mock IBKR client
    class MockIBKRClient:
        pass
    
    try:
        # Same service interface, different implementations
        print("\n1. Creating service with LOCAL repositories...")
        local_service = RepositoryFactory.create_financial_asset_service(
            session=session,
            use_ibkr=False
        )
        
        print("2. Creating service with IBKR repositories...")
        ibkr_service = RepositoryFactory.create_financial_asset_service(
            session=session,
            use_ibkr=True,
            ibkr_client=MockIBKRClient()
        )
        
        # The EXACT SAME service methods work with both implementations
        print("\n3. Testing identical service calls on both services...")
        
        test_symbol = "ESZ25"
        
        print(f"\nLocal service - get_or_create_index_future('{test_symbol}'):")
        local_result = local_service.get_or_create_index_future(test_symbol)
        print(f"Result: {local_result}")
        
        print(f"\nIBKR service - get_or_create_index_future('{test_symbol}'):")
        ibkr_result = ibkr_service.get_or_create_index_future(test_symbol)
        print(f"Result: {ibkr_result}")
        
        print("\n✅ Service layer code is IDENTICAL - implementations differ only at composition root")
        print("✅ The service does NOT know where data comes from")
        print("✅ The service does NOT know how creation rules differ")
        print("✅ This is intentional and correct!")
        
    except Exception as e:
        print(f"Error in service independence demonstration: {e}")
    finally:
        session.close()


def example_portfolio_operations():
    """
    Demonstrate portfolio-level operations that combine multiple asset types.
    """
    print("\n=== Portfolio Operations Example ===")
    
    database_service = DatabaseService('sqlite')
    session = database_service.session
    
    try:
        service = RepositoryFactory.create_financial_asset_service(
            session=session,
            use_ibkr=False  # Using local for this example
        )
        
        print("Creating diversified portfolio...")
        
        portfolio = service.create_diversified_portfolio(
            equity_symbols=['AAPL', 'TSLA', 'MSFT'],
            future_symbols=['ESZ25', 'NQH25'],
            currency_symbols=['USD', 'EUR', 'GBP'],
            bond_symbols=['US10Y', 'DE10Y']
        )
        
        print(f"Portfolio created:")
        for asset_type, assets in portfolio.items():
            if asset_type != 'errors':
                print(f"  {asset_type}: {len(assets)} assets")
            else:
                print(f"  {asset_type}: {assets}")
        
        # Search operations
        print("\nTesting search operations...")
        
        search_results = service.search_assets_by_criteria('futures', 'ESZ25')
        print(f"Search for futures 'ESZ25': {len(search_results)} results")
        
        search_results = service.search_assets_by_criteria('shares', 'AAPL')
        print(f"Search for shares 'AAPL': {len(search_results)} results")
        
    except Exception as e:
        print(f"Error in portfolio operations: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("IBKR Repository Architecture Pattern - Usage Examples")
    print("=" * 60)
    
    # Run all examples
    example_local_configuration()
    example_ibkr_configuration()
    example_service_layer_independence()
    example_portfolio_operations()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("\nKey Takeaways:")
    print("1. Service layer code NEVER changes between local and IBKR implementations")
    print("2. Repository choice is made ONCE at application startup (composition root)")
    print("3. IBKR repositories handle data acquisition, local repositories handle persistence")
    print("4. The service layer remains infrastructure-agnostic")
    print("5. Testing is simplified through port mocking")
    print("\nThis architecture provides clean separation of concerns and easy maintainability.")