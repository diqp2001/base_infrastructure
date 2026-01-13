"""
IBKR Instrument and Factor Value Usage Examples

This example demonstrates the new IBKR architecture:
IBKR Contract → Instrument → Factor Values → Financial Asset Factor Values → DB

The system maps IBKR tick data to factor values using the official IBKR tick types.
"""

from datetime import datetime
from typing import Dict, Any

# Mock IBKR client and session for demonstration
class MockIBKRClient:
    """Mock IBKR client for demonstration purposes."""
    pass

class MockSession:
    """Mock database session for demonstration purposes."""
    pass

# Example usage
def example_ibkr_instrument_factor_workflow():
    """
    Demonstrates the complete workflow from IBKR contract to factor values.
    """
    
    # Initialize repositories (in real usage, these would be injected)
    mock_ibkr_client = MockIBKRClient()
    mock_session = MockSession()
    
    # These would be your actual repository instances
    # local_instrument_repo = InstrumentRepository(mock_session)
    # local_factor_value_repo = FactorValueRepository(mock_session)
    # financial_asset_repo = CompanyShareRepository(mock_session)
    
    # ibkr_instrument_repo = IBKRInstrumentRepository(
    #     ibkr_client=mock_ibkr_client,
    #     local_instrument_repo=local_instrument_repo,
    #     local_factor_value_repo=local_factor_value_repo,
    #     financial_asset_repo=financial_asset_repo
    # )
    
    # ibkr_company_share_repo = IBKRCompanyShareRepository(
    #     ibkr_client=mock_ibkr_client,
    #     local_repo=local_company_share_repo,
    #     local_factor_value_repo=local_factor_value_repo,
    #     ibkr_instrument_repo=ibkr_instrument_repo
    # )
    
    print("=== IBKR Instrument and Factor Value Architecture ===")
    print()
    
    # Example 1: Create factor value from tick data
    print("1. Creating factor value from IBKR tick data:")
    print("   Symbol: AAPL")
    print("   Tick Type: LAST_PRICE (4)")
    print("   Tick Value: 150.25")
    print("   Date: 2025-01-13")
    print()
    
    # This would create:
    # - IBKR contract for AAPL
    # - IBKRInstrument entity from contract
    # - FactorValue from tick data (Last Price = 150.25)
    # - Mapping to CompanyShare factor value
    
    # factor_value = ibkr_company_share_repo.create_factor_value_from_tick_data(
    #     symbol="AAPL",
    #     tick_type=IBKRTickType.LAST_PRICE,
    #     tick_value=150.25,
    #     time="2025-01-13"
    # )
    
    print("   → Creates IBKR contract for AAPL stock")
    print("   → Creates IBKRInstrument entity")
    print("   → Maps tick type LAST_PRICE to 'Last Price' factor")
    print("   → Creates instrument-level factor value")
    print("   → Maps to company share factor value")
    print("   → Persists to database")
    print()
    
    # Example 2: Create multiple factor values from tick data
    print("2. Creating multiple factor values from comprehensive tick data:")
    
    # Example tick data from IBKR market data
    sample_tick_data = {
        1: 150.20,    # BID_PRICE
        2: 150.25,    # ASK_PRICE  
        4: 150.23,    # LAST_PRICE
        0: 500,       # BID_SIZE
        3: 300,       # ASK_SIZE
        5: 100,       # LAST_SIZE
        8: 1250000,   # VOLUME
        6: 151.50,    # HIGH
        7: 149.80,    # LOW
        9: 149.95,    # CLOSE_PRICE
    }
    
    print("   Tick Data:")
    tick_descriptions = {
        1: "BID_PRICE: 150.20",
        2: "ASK_PRICE: 150.25", 
        4: "LAST_PRICE: 150.23",
        0: "BID_SIZE: 500",
        3: "ASK_SIZE: 300",
        5: "LAST_SIZE: 100",
        8: "VOLUME: 1,250,000",
        6: "HIGH: 151.50",
        7: "LOW: 149.80", 
        9: "CLOSE_PRICE: 149.95"
    }
    
    for tick_id, description in tick_descriptions.items():
        print(f"     {description}")
    print()
    
    # This would create multiple factor values in one transaction
    # factor_value = ibkr_company_share_repo.get_or_create_factor_value_with_ticks(
    #     symbol_or_name="AAPL",
    #     factor_id=None,  # Resolved from tick mapping
    #     time="2025-01-13",
    #     tick_data=sample_tick_data
    # )
    
    print("   → Creates IBKRInstrument for AAPL")
    print("   → Maps each tick type to corresponding factor:")
    print("     • BID_PRICE → 'Bid Price' factor (Market/Price group)")
    print("     • ASK_PRICE → 'Ask Price' factor (Market/Price group)")
    print("     • LAST_PRICE → 'Last Price' factor (Market/Price group)")
    print("     • BID_SIZE → 'Bid Size' factor (Market/Volume group)")
    print("     • ASK_SIZE → 'Ask Size' factor (Market/Volume group)")
    print("     • LAST_SIZE → 'Last Size' factor (Market/Volume group)")
    print("     • VOLUME → 'Volume' factor (Market/Volume group)")
    print("     • HIGH → 'High Price' factor (Market/Price group)")
    print("     • LOW → 'Low Price' factor (Market/Price group)")
    print("     • CLOSE_PRICE → 'Close Price' factor (Market/Price group)")
    print()
    print("   → Creates 10 instrument factor values")
    print("   → Maps all to corresponding company share factor values")
    print("   → Single database transaction for all factor values")
    print()
    
    # Example 3: Architecture benefits
    print("3. Architecture Benefits:")
    print()
    print("   ✅ Clean Separation of Concerns:")
    print("      • IBKR repositories: Handle API integration and contract mapping")
    print("      • Local repositories: Handle SQLAlchemy and persistence")
    print("      • Mappers: Handle IBKR tick type → factor conversion")
    print()
    print("   ✅ Correct Data Flow:")
    print("      IBKR Contract → Instrument → Factor Values → Asset Factor Values → DB")
    print("      (NOT: IBKR → ORM → DB → ORM → Domain)")
    print()
    print("   ✅ IBKR Tick Type Integration:")
    print("      • Uses official IBKR tick types from TWS API documentation")
    print("      • Comprehensive mapping for price, volume, options, and status data")
    print("      • Extensible for new tick types")
    print()
    print("   ✅ Factor Value Consistency:")
    print("      • Instrument factors linked to asset factors")
    print("      • Same factor data available at both instrument and asset level")
    print("      • Supports complex factor analysis workflows")
    print()
    print("   ✅ Testability & Maintainability:")
    print("      • Mock IBKR client for unit testing")
    print("      • Swap implementations without touching business logic")
    print("      • Clear dependency injection pattern")


def example_supported_tick_types():
    """
    Show the comprehensive list of supported IBKR tick types.
    """
    
    print("=== Supported IBKR Tick Types for Factor Mapping ===")
    print()
    
    # from src.infrastructure.repositories.ibkr_repo.tick_types import IBKRTickFactorMapper
    # mapper = IBKRTickFactorMapper()
    
    # Price factors
    print("📈 Price Factors:")
    price_factors = [
        "BID_PRICE (1) → Bid Price factor",
        "ASK_PRICE (2) → Ask Price factor", 
        "LAST_PRICE (4) → Last Price factor",
        "HIGH (6) → High Price factor",
        "LOW (7) → Low Price factor",
        "CLOSE_PRICE (9) → Close Price factor",
        "OPEN_TICK (14) → Open Price factor",
        "MARK_PRICE (37) → Mark Price factor"
    ]
    
    for factor in price_factors:
        print(f"   • {factor}")
    print()
    
    # Volume factors  
    print("📊 Volume Factors:")
    volume_factors = [
        "BID_SIZE (0) → Bid Size factor",
        "ASK_SIZE (3) → Ask Size factor",
        "LAST_SIZE (5) → Last Size factor", 
        "VOLUME (8) → Volume factor",
        "AVG_VOLUME (21) → Average Volume factor"
    ]
    
    for factor in volume_factors:
        print(f"   • {factor}")
    print()
    
    # Historical factors
    print("📅 Historical Factors:")
    historical_factors = [
        "HIGH_52_WEEK (20) → 52 Week High factor",
        "LOW_52_WEEK (19) → 52 Week Low factor", 
        "HIGH_26_WEEK (18) → 26 Week High factor",
        "LOW_26_WEEK (17) → 26 Week Low factor",
        "HIGH_13_WEEK (16) → 13 Week High factor",
        "LOW_13_WEEK (15) → 13 Week Low factor"
    ]
    
    for factor in historical_factors:
        print(f"   • {factor}")
    print()
    
    # Options factors
    print("📈 Options Factors:")
    options_factors = [
        "OPTION_IMPLIED_VOL (24) → Implied Volatility factor",
        "OPTION_HISTORICAL_VOL (23) → Historical Volatility factor",
        "OPEN_INTEREST (22) → Open Interest factor"
    ]
    
    for factor in options_factors:
        print(f"   • {factor}")
    print()
    
    # Trading factors
    print("🔄 Trading Factors:")
    trading_factors = [
        "TRADE_COUNT (50) → Trade Count factor",
        "TRADE_RATE (51) → Trade Rate factor",
        "VOLUME_RATE (52) → Volume Rate factor"
    ]
    
    for factor in trading_factors:
        print(f"   • {factor}")
    print()
    
    # Status factors
    print("ℹ️ Status Factors:")
    status_factors = [
        "HALTED (49) → Halted Status factor",
        "SHORTABLE (46) → Shortable factor"
    ]
    
    for factor in status_factors:
        print(f"   • {factor}")
    print()
    
    print("Total: 30+ supported tick types mapped to factors")
    print("Extensible architecture - easy to add new tick type mappings")


if __name__ == "__main__":
    print("IBKR Instrument and Factor Value Architecture Examples")
    print("=" * 60)
    print()
    
    example_ibkr_instrument_factor_workflow()
    print()
    print("=" * 60)
    print()
    example_supported_tick_types()