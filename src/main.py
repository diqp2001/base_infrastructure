

from cProfile import Profile
from pstats import SortKey, Stats


from application.managers.api_managers.api_cboe.api_cboe_manager import download_and_consolidate_csv
from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.cross_sectionnal_ML_stock_returns_project_manager import CrossSectionalMLStockReturnsProjectManager
from application.managers.project_managers.momentum_ML_project.momentum_ML_project import MomentumMLProjectManager
from application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
from application.managers.project_managers.test_project_data.test_project_data_manager import TestProjectDataManager
from application.managers.project_managers.test_project_live_trading.test_project_live_trading_manager import TestProjectLiveTradingManager






if __name__ == '__main__':
    
    
    #consolidated_df = download_and_consolidate_csv()
    #CrossSectionalMLStockReturnsProjectManager().execute_database_management_tasks()
    #
    
    # Example usage of the centralized BackTesting class
    #bt = BackTesting()
    #results = bt.run_vx_csv_backtest()
    #print(f"Backtest completed with return: {results['backtest_results'].get('total_return', 0):.2%}")
    
    # Example usage of the Black-Litterman Portfolio Optimization backtest
    # Uncomment the lines below to run the Black-Litterman backtest
    #bl_results = bt.run_black_litterman_backtest()
    #print(f"Black-Litterman backtest completed with return: {bl_results['backtest_results'].get('total_return', 0):.2%}")
    #manager = TestProjectBacktestManager()
    manager = TestProjectLiveTradingManager()
    
    manager.run()
    
    """    with Profile() as profile:
    #MomentumMLProjectManager().test_single_future()
    #manager = TestProjectDataManager()
    # This now uses the new share-based terminology
    
    (
        Stats(profile).strip_dirs().sort_stats(SortKey.CALLS).print_stats()
    )"""
   


    