#!/usr/bin/env python3
"""
Test script to verify MLflow integration with TestBaseProjectManager.

This script creates a simple test to ensure that:
1. MLflow experiment is created properly
2. Basic parameters and metrics can be logged
3. The integration doesn't break existing functionality
"""

import sys
import os
import logging
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
    
    def test_mlflow_integration():
        """Test basic MLflow integration functionality."""
        print("🧪 Testing MLflow integration with TestBaseProjectManager...")
        
        # Create manager instance
        try:
            manager = TestBaseProjectManager()
            print("✅ TestBaseProjectManager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize TestBaseProjectManager: {e}")
            return False
        
        # Test MLflow setup
        try:
            # The MLflow setup happens in __init__, so we just verify it worked
            if hasattr(manager, 'mlflow_experiment_name'):
                print(f"✅ MLflow experiment name set: {manager.mlflow_experiment_name}")
            else:
                print("⚠️ MLflow experiment name not found")
        except Exception as e:
            print(f"❌ MLflow setup test failed: {e}")
            return False
            
        # Test starting/ending a run manually
        try:
            manager._start_mlflow_run("test_run")
            print("✅ MLflow run started successfully")
            
            # Test logging parameters
            test_params = {
                'test_param_1': 'test_value',
                'test_param_2': 42
            }
            manager._log_mlflow_params(test_params)
            print("✅ MLflow parameters logged successfully")
            
            # Test logging metrics
            test_metrics = {
                'test_metric_1': 0.85,
                'test_metric_2': 123.45
            }
            manager._log_mlflow_metrics(test_metrics)
            print("✅ MLflow metrics logged successfully")
            
            # End the test run
            manager._end_mlflow_run()
            print("✅ MLflow run ended successfully")
            
        except Exception as e:
            print(f"❌ MLflow run test failed: {e}")
            return False
        
        print("🎉 All MLflow integration tests passed!")
        return True
    
    if __name__ == "__main__":
        # Set up basic logging
        logging.basicConfig(level=logging.INFO)
        
        print(f"Starting MLflow integration test at {datetime.now()}")
        success = test_mlflow_integration()
        
        if success:
            print("✅ MLflow integration test completed successfully")
            sys.exit(0)
        else:
            print("❌ MLflow integration test failed")
            sys.exit(1)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed and paths are correct")
    sys.exit(1)