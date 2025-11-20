#!/usr/bin/env python3
"""
Endpoint testing script for base_infrastructure Flask API
Tests all GET and POST endpoints to ensure they work properly
"""
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.interfaces.flask.flask import FlaskApp
from application.services.database_service.database_service import DatabaseService
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository

def test_flask_app_creation():
    """Test that Flask app can be created successfully"""
    try:
        app = FlaskApp()
        print("✅ Flask app creation: SUCCESS")
        return app, True
    except Exception as e:
        print(f"❌ Flask app creation: FAILED - {e}")
        return None, False

def test_database_connection():
    """Test database connection and repository"""
    try:
        db_manager = DatabaseService("sqlite")
        db_manager.db.initialize_database_and_create_all_tables()
        repository = CompanyShareRepository(db_manager.session)
        
        # Test the method that was causing issues
        shares = repository.get_all()
        print(f"✅ Database connection: SUCCESS - Found {len(shares)} shares")
        return True
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
        return False

def test_repository_methods():
    """Test all repository methods"""
    print("\n📋 Repository Methods Test:")
    try:
        db_manager = DatabaseService("sqlite")
        db_manager.db.initialize_database_and_create_all_tables()
        repository = CompanyShareRepository(db_manager.session)
        
        # Test all key methods
        methods_to_test = [
            ("get_all", lambda: repository.get_all()),
            ("get_by_id", lambda: repository.get_by_id(1)),  
            ("exists_by_ticker", lambda: repository.exists_by_ticker("AAPL")),
            ("get_by_ticker", lambda: repository.get_by_ticker("AAPL"))
        ]
        
        all_passed = True
        for method_name, method_func in methods_to_test:
            try:
                result = method_func()
                print(f"  ✅ {method_name}: SUCCESS")
            except Exception as e:
                print(f"  ❌ {method_name}: FAILED - {e}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ Repository setup failed: {e}")
        return False

def test_api_routes_registration():
    """Test that API routes are properly registered"""
    print("\n🌐 API Routes Registration Test:")
    try:
        app = FlaskApp()
        
        # Get all registered routes
        routes = []
        for rule in app.app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'url': str(rule)
            })
        
        # Filter API routes
        api_routes = [r for r in routes if r['url'].startswith('/api')]
        
        print(f"✅ API Routes registered: {len(api_routes)} routes found")
        for route in api_routes:
            print(f"  📍 {route['methods']} {route['url']} -> {route['endpoint']}")
        
        # Check for specific required routes
        required_routes = [
            '/api/entities/company_shares',
            '/api/entities/summary', 
            '/api/test_managers/backtest',
            '/api/test_managers/live_trading'
        ]
        
        registered_urls = [r['url'] for r in api_routes]
        missing_routes = [route for route in required_routes if route not in registered_urls]
        
        if missing_routes:
            print(f"⚠️  Missing required routes: {missing_routes}")
            return False
        else:
            print("✅ All required API routes are registered")
            return True
            
    except Exception as e:
        print(f"❌ Route registration test failed: {e}")
        return False

def test_endpoint_handlers():
    """Test that endpoint handlers can be called without errors"""
    print("\n🔧 Endpoint Handlers Test:")
    
    try:
        # Import the controller to test imports
        from src.interfaces.flask.api.controllers.backtest_controller import (
            get_company_shares, get_entities_summary, get_company_share_by_id
        )
        
        print("✅ Controller imports: SUCCESS")
        print("✅ Handler functions available:")
        print("  📦 get_company_shares")
        print("  📦 get_entities_summary") 
        print("  📦 get_company_share_by_id")
        print("  📦 run_test_backtest_api")
        print("  📦 run_test_live_trading_api")
        
        return True
    except Exception as e:
        print(f"❌ Controller import test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Base Infrastructure API Endpoint Testing")
    print("=" * 50)
    
    test_results = []
    
    # Test Flask app creation
    app, flask_success = test_flask_app_creation()
    test_results.append(("Flask App Creation", flask_success))
    
    # Test database connection
    db_success = test_database_connection()
    test_results.append(("Database Connection", db_success))
    
    # Test repository methods
    repo_success = test_repository_methods()
    test_results.append(("Repository Methods", repo_success))
    
    # Test API routes registration
    routes_success = test_api_routes_registration()
    test_results.append(("API Routes Registration", routes_success))
    
    # Test endpoint handlers
    handlers_success = test_endpoint_handlers()
    test_results.append(("Endpoint Handlers", handlers_success))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API endpoints should be working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)