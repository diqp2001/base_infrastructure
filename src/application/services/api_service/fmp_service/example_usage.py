#!/usr/bin/env python3
"""
Example usage of FMP Equity Data Service.
Demonstrates how to use the service to fetch and store equity data.
"""

import sys
import os
import logging
from typing import List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from src.application.services.api_service.fmp_service.get_equity_service import (
    FmpEquityDataService, create_fmp_equity_service
)
from src.application.services.api_service.fmp_service.config_equity_service import (
    FmpEquityServiceConfig, get_default_config
)

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def example_basic_usage():
    """Example of basic service usage."""
    print("📊 Basic FMP Equity Data Service Usage")
    print("=" * 50)
    
    try:
        # Create service with default configuration
        service = create_fmp_equity_service()
        
        print("✅ Service created successfully")
        
        # Get service status
        status = service.get_service_status()
        print(f"📈 Service status: {status['service_status']}")
        print(f"📊 Configured symbols: {status['configured_symbols'][:3]}...")  # Show first 3
        
        # Example: Fetch data for specific symbols
        test_symbols = ['AAPL', 'MSFT']
        print(f"\n🔄 Fetching data for: {test_symbols}")
        
        # This would normally fetch from API and store in DB
        # results = service.fetch_and_store_quotes(test_symbols)
        # print(f"📊 Results: {results['success_count']} success, {results['error_count']} errors")
        
        print("💡 Note: To actually fetch data, ensure FMP credentials are configured")
        
    except Exception as e:
        print(f"❌ Error in basic usage: {e}")

def example_custom_configuration():
    """Example of using custom configuration."""
    print("\n📋 Custom Configuration Example")
    print("=" * 50)
    
    try:
        # Create custom configuration
        custom_config = FmpEquityServiceConfig(
            symbols=['AAPL', 'GOOGL', 'TSLA'],
            update_interval_minutes=30,
            enable_bulk_updates=True,
            data_retention_days=180,
            batch_size=50
        )
        
        print(f"⚙️  Custom config created:")
        print(f"   Symbols: {custom_config.symbols}")
        print(f"   Update interval: {custom_config.update_interval_minutes} minutes")
        print(f"   Bulk updates: {custom_config.enable_bulk_updates}")
        print(f"   Retention: {custom_config.data_retention_days} days")
        
        # Create service with custom config
        # service = FmpEquityDataService(config=custom_config)
        # print("✅ Service created with custom configuration")
        
        print("💡 Note: Uncomment lines above to create service with custom config")
        
    except Exception as e:
        print(f"❌ Error in custom configuration: {e}")

def example_data_operations():
    """Example of data operations."""
    print("\n💾 Data Operations Example")
    print("=" * 50)
    
    try:
        # This would normally require a properly configured service
        print("📊 Data operations that would be available:")
        print("   • fetch_and_store_quotes(symbols)")
        print("   • fetch_and_store_multiple_quotes(symbols)")
        print("   • get_stored_data(symbol, limit)")
        print("   • get_latest_data(symbol)")
        print("   • get_multiple_latest_data(symbols)")
        print("   • cleanup_old_data(symbol)")
        print("   • run_update_cycle()")
        
        print("\n📈 Example workflow:")
        print("   1. service = create_fmp_equity_service()")
        print("   2. results = service.run_update_cycle()")
        print("   3. latest = service.get_latest_data('AAPL')")
        print("   4. historical = service.get_stored_data('AAPL', limit=100)")
        
    except Exception as e:
        print(f"❌ Error in data operations: {e}")

def example_configuration_from_dict():
    """Example of loading configuration from dictionary."""
    print("\n🔧 Configuration from Dictionary Example")
    print("=" * 50)
    
    try:
        from src.application.services.api_service.fmp_service.config_equity_service import load_config_from_dict
        
        # Configuration dictionary (could come from JSON file, environment, etc.)
        config_dict = {
            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN'],
            'update_interval_minutes': 15,
            'enable_real_time': False,
            'data_retention_days': 90,
            'enable_bulk_updates': True,
            'batch_size': 25
        }
        
        # Load configuration
        config = load_config_from_dict(config_dict)
        
        print(f"✅ Configuration loaded from dictionary:")
        print(f"   Symbols: {config.symbols}")
        print(f"   Update interval: {config.update_interval_minutes}")
        print(f"   Real-time: {config.enable_real_time}")
        print(f"   Retention: {config.data_retention_days} days")
        print(f"   Bulk updates: {config.enable_bulk_updates}")
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")

def main():
    """Run all examples."""
    print("🧪 FMP Equity Data Service Examples")
    print("=" * 60)
    
    setup_logging()
    
    # Run examples
    example_basic_usage()
    example_custom_configuration()
    example_data_operations()
    example_configuration_from_dict()
    
    print("\n" + "=" * 60)
    print("🎯 To use the service in production:")
    print("1. Set up FMP API credentials (fmp_credentials.json)")
    print("2. Configure database connection")
    print("3. Initialize database tables")
    print("4. Run service.run_update_cycle() or individual methods")
    print("\n📖 See CLAUDE.md for detailed documentation")

if __name__ == "__main__":
    main()