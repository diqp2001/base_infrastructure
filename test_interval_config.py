#!/usr/bin/env python3
"""
Test script to demonstrate different backtesting interval configurations.
This script shows examples of how to use the new configurable time intervals.
"""

from datetime import datetime
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def show_example_configurations():
    """Display example configurations for different backtesting intervals."""
    
    print("🔧 Backtesting Time Interval Configuration Examples")
    print("=" * 60)
    
    examples = [
        {
            "name": "Daily (Default)",
            "config": {
                "backtest_interval": "daily"
            },
            "description": "Process data every day (traditional backtesting)"
        },
        {
            "name": "Weekly",
            "config": {
                "backtest_interval": "weekly"
            },
            "description": "Process data every 7 days"
        },
        {
            "name": "Monthly", 
            "config": {
                "backtest_interval": "monthly"
            },
            "description": "Process data every month (requires dateutil)"
        },
        {
            "name": "Quarterly",
            "config": {
                "backtest_interval": "quarterly"
            },
            "description": "Process data every 3 months"
        },
        {
            "name": "Semi-Yearly",
            "config": {
                "backtest_interval": "semi_yearly"
            },
            "description": "Process data every 6 months"
        },
        {
            "name": "Custom 3-Day Interval",
            "config": {
                "custom_interval_days": 3
            },
            "description": "Process data every 3 days"
        },
        {
            "name": "Hourly",
            "config": {
                "custom_interval_hours": 1
            },
            "description": "Process data every hour"
        },
        {
            "name": "30-Minute Intervals",
            "config": {
                "custom_interval_minutes": 30
            },
            "description": "Process data every 30 minutes"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['name']}")
        print(f"   Description: {example['description']}")
        print(f"   Configuration:")
        for key, value in example['config'].items():
            print(f"     \"{key}\": \"{value}\" if isinstance(value, str) else {value}")
        print("   " + "-" * 50)
    
    print("\n📝 How to Use:")
    print("1. Open: src/application/managers/project_managers/test_project_backtest/engine_config.py")
    print("2. Modify the MISBUFFET_ENGINE_CONFIG dictionary")
    print("3. Set your desired interval configuration")
    print("4. Run your backtest as usual")
    
    print("\n⚙️  Priority Order:")
    print("1. custom_interval_minutes (highest priority)")
    print("2. custom_interval_hours") 
    print("3. custom_interval_days")
    print("4. backtest_interval (lowest priority)")
    
    print("\n📊 Supported backtest_interval values:")
    print("   • 'daily' - Every day")
    print("   • 'weekly' - Every 7 days") 
    print("   • 'monthly' - Every month (calendar month)")
    print("   • 'quarterly' - Every 3 months")
    print("   • 'semi_yearly' - Every 6 months")
    print("   • 'seconds' - Every second (for very granular testing)")
    print("   • 'minutes' - Every minute")

def test_interval_calculation():
    """Test the interval calculation logic."""
    print("\n🧪 Testing Interval Calculation Logic")
    print("=" * 40)
    
    try:
        from application.services.misbuffet.engine.misbuffet_engine import MisbuffetEngine, MisbuffetEngineConfig
        
        # Create engine with default configuration
        engine_config = MisbuffetEngineConfig()
        engine = MisbuffetEngine(engine_config)
        
        test_configs = [
            {"backtest_interval": "daily"},
            {"backtest_interval": "weekly"},
            {"backtest_interval": "monthly"},
            {"custom_interval_days": 5},
            {"custom_interval_hours": 6},
            {"custom_interval_minutes": 15}
        ]
        
        print("Testing different configurations:")
        for i, config in enumerate(test_configs, 1):
            try:
                interval = engine._get_time_interval(config)
                print(f"{i}. {config} → {interval['type']}: {interval['value']}")
            except Exception as e:
                print(f"{i}. {config} → ERROR: {e}")
                
    except ImportError as e:
        print(f"Could not import engine for testing: {e}")
        print("This is expected if dependencies are not installed.")

if __name__ == "__main__":
    show_example_configurations()
    test_interval_calculation()