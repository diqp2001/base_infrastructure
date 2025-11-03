

from cProfile import Profile
from pstats import SortKey, Stats


from application.managers.api_managers.api_cboe.api_cboe_manager import download_and_consolidate_csv
from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.cross_sectionnal_ML_stock_returns_project_manager import CrossSectionalMLStockReturnsProjectManager
from application.managers.project_managers.momentum_ML_project.momentum_ML_project import MomentumMLProjectManager
from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
from application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
from application.managers.project_managers.test_project_backtest_fx.fx_test_project_backtest_manager import FXTestProjectBacktestManager
from application.managers.project_managers.test_project_data.test_project_data_manager import TestProjectDataManager
from application.managers.project_managers.test_project_factor_creation.test_project_data_manager import TestProjectFactorManager
from application.managers.project_managers.test_project_live_trading.test_project_live_trading_manager import TestProjectLiveTradingManager
from application.managers.project_managers.test_project_web.test_project_web_manager import TestProjectWebManager






if __name__ == '__main__':
    # Web-Only Interface Launch
    # Changed as per request - only launch web interface, no automatic pipeline execution
    
    from src.interfaces.flask.flask import FlaskApp
    import webbrowser
    import time
    import threading
    
    print("🚀 Starting Web-Only Trading Interface...")
    print("📊 Access the dashboard at: http://localhost:5000/dashboard")
    
    # Create Flask app
    app = FlaskApp()
    
    def open_browser():
        """Open browser to dashboard after a short delay"""
        time.sleep(1.5)  # Wait for server to start
        try:
            webbrowser.open('http://localhost:5000/dashboard')
            print("🌐 Browser opened to Trading Dashboard")
        except Exception as e:
            print(f"⚠️  Could not auto-open browser: {e}")
    
    # Start browser in background thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run Flask app
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down web interface...")
    except Exception as e:
        print(f"❌ Error running web interface: {e}")
    
    """    with Profile() as profile:
    #MomentumMLProjectManager().test_single_future()
    #manager = TestProjectDataManager()
    # This now uses the new share-based terminology
    
    (
        Stats(profile).strip_dirs().sort_stats(SortKey.CALLS).print_stats()
    )
    """
   


    