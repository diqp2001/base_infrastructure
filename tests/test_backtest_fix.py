#!/usr/bin/env python3
"""
Test script to verify the backtest UNIQUE constraint fix.
"""
import os
import sys

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.application.services.backtest_tracking.backtest_tracker_service import get_tracker

def test_backtest_tracker_duplicate_config():
    """Test that duplicate config_ids are handled properly."""
    
    print("Testing backtest tracker duplicate config handling...")
    
    # Get tracker instance
    tracker = get_tracker()
    
    # Create first run
    print("Creating first run...")
    run_config = {
        'algorithm': 'momentum',
        'lookback': 20,
        'initial_capital': 100000
    }
    
    try:
        run_id_1 = tracker.create_run_from_manager_config(
            experiment_name="test_experiment_duplicate_fix",
            manager_config=run_config
        )
        print(f"✅ First run created successfully: {run_id_1}")
    except Exception as e:
        print(f"❌ Error creating first run: {e}")
        return False
    
    # Create second run with same config (should not fail)
    print("Creating second run with same config...")
    try:
        run_id_2 = tracker.create_run_from_manager_config(
            experiment_name="test_experiment_duplicate_fix", 
            manager_config=run_config
        )
        print(f"✅ Second run created successfully: {run_id_2}")
        
        # Verify they have different IDs
        if run_id_1 != run_id_2:
            print(f"✅ Run IDs are unique: {run_id_1} != {run_id_2}")
        else:
            print(f"⚠️ Run IDs are the same: {run_id_1} == {run_id_2}")
            
    except Exception as e:
        print(f"❌ Error creating second run: {e}")
        return False
    
    # Try to store the same config again (should update, not fail)
    print("Testing direct config storage...")
    try:
        config = tracker.repository.get_config(run_id_1)
        if config:
            print("Re-storing existing config...")
            stored_id = tracker.repository.store_config(config)
            print(f"✅ Config re-stored successfully: {stored_id}")
        else:
            print("⚠️ Could not retrieve config for re-storage test")
            
    except Exception as e:
        print(f"❌ Error re-storing config: {e}")
        return False
    
    print("✅ All duplicate handling tests passed!")
    return True

if __name__ == "__main__":
    success = test_backtest_tracker_duplicate_config()
    sys.exit(0 if success else 1)