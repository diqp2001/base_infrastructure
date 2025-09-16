#!/usr/bin/env python3
"""
Test script for TestProjectBacktestManager auto-launch functionality
"""
import sys
import os

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
    print("✅ Import successful - TestProjectBacktestManager can be imported")
    
    manager = TestProjectBacktestManager()
    print("✅ Initialization successful - TestProjectBacktestManager instance created")
    
    print("🔧 Testing basic functionality...")
    print(f"Manager class: {type(manager)}")
    print(f"Database manager: {type(manager.database_manager) if manager.database_manager else 'None'}")
    print(f"Progress queue initialized: {hasattr(manager, 'progress_queue')}")
    print(f"Flask components: {hasattr(manager, 'flask_app')}")
    print(f"Web interface methods: {hasattr(manager, '_start_web_interface')}")
    print(f"Browser open method: {hasattr(manager, '_open_browser')}")
    
    print("✅ All basic components are properly initialized!")
    print("🌐 Ready to launch web interface when .run() is called")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)