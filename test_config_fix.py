#!/usr/bin/env python3
"""
Simple test script to verify test_base_project configuration setup works properly.
"""

import sys
import os
sys.path.append('/home/runner/work/base_infrastructure/base_infrastructure')

from datetime import datetime
from application.managers.database_managers.database_manager import DatabaseManager
from src.application.managers.project_managers.test_base_project.config import CONFIG_TEST, get_config
from src.application.managers.project_managers.test_base_project.backtesting.backtest_runner import BacktestRunner

def test_config_setup():
    """Test that configuration setup works without errors."""
    try:
        print("🧪 Testing configuration setup...")
        
        # Test 1: Load configuration
        print("  - Loading test configuration...")
        config = get_config('test')
        print(f"  ✅ Config loaded with keys: {list(config.keys())}")
        
        # Test 2: Check BACKTEST section exists
        if 'BACKTEST' not in config:
            raise Exception("BACKTEST configuration missing")
        print(f"  ✅ BACKTEST config found with keys: {list(config['BACKTEST'].keys())}")
        
        # Test 3: Create database manager
        print("  - Creating database manager...")
        db_manager = DatabaseManager(CONFIG_TEST['DB_TYPE'])
        print("  ✅ Database manager created")
        
        # Test 4: Create BacktestRunner
        print("  - Creating BacktestRunner...")
        runner = BacktestRunner(db_manager)
        print("  ✅ BacktestRunner created")
        
        # Test 5: Setup components with proper config
        print("  - Testing component setup...")
        test_tickers = ['AAPL', 'MSFT']
        config['DATA']['DEFAULT_UNIVERSE'] = test_tickers
        
        success = runner.setup_components(config)
        if success:
            print("  ✅ Component setup successful")
        else:
            print("  ❌ Component setup failed")
            return False
            
        print("\n🎉 All configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config_setup()
    sys.exit(0 if success else 1)