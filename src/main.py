

from cProfile import Profile
from pstats import SortKey, Stats


from application.managers.api_managers.api_cboe.api_cboe_manager import download_and_consolidate_csv
from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.cross_sectionnal_ML_stock_returns_project_manager import CrossSectionalMLStockReturnsProjectManager
from application.managers.project_managers.momentum_ML_project.momentum_ML_project import MomentumMLProjectManager
from application.managers.project_managers.test_base_project_2.test_base_project_manager import TestBaseProjectManager
from application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
from application.managers.project_managers.test_project_backtest_fx.fx_test_project_backtest_manager import FXTestProjectBacktestManager
from application.managers.project_managers.test_project_data.test_project_data_manager import TestProjectDataManager
from application.managers.project_managers.test_project_factor_creation.test_project_data_manager import TestProjectFactorManager
from application.managers.project_managers.test_project_live_trading.test_project_live_trading_manager import TestProjectLiveTradingManager
from application.managers.project_managers.test_project_web.test_project_web_manager import TestProjectWebManager






if __name__ == '__main__':
    #TestBaseProjectManager().web_interface.start_interface_and_open_browser()
    TestBaseProjectManager().run()
    
   


    