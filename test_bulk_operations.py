#!/usr/bin/env python3
"""
Simple test script to verify bulk operations implementation.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.application.managers.project_managers.test_project.test_project_manager import TestProjectManager
    
    print("Testing bulk operations implementation...")
    
    # Create manager instance
    manager = TestProjectManager()
    
    # Test bulk operations
    print("Running save_multiple_company_stocks_example...")
    result = manager.save_multiple_company_stocks_example()
    
    if result:
        print(f"✅ Success: Created {len(result)} companies using bulk operations")
    else:
        print("❌ Failed: No companies were created")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")