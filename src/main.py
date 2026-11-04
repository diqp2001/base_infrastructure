
import sys
# print(sys.getrecursionlimit())
# sys.setrecursionlimit(10000)

from cProfile import Profile
from pstats import SortKey, Stats
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.project_manager import SpatioTemporalMomentum10mProjectManager
from src.application.managers.project_managers.spatio_temporal_momentum_project.project_manager import SpatioTemporalMomentumProjectManager
from src.application.managers.project_managers.market_making_SPX_call_spread_project.project_manager import MarketMakingSPXCallSpreadProjectManager
from src.application.services.api_service.ibkr_service.comprehensive_market_data_examples import ComprehensiveIBMarketDataExamples
from src.application.managers.project_managers.cross_sectionnal_project.cross_sectionnal_project_manager import CrossSectionnal
from src.application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
from src.application.services.api_service.ercot_service.ercot_public_api_service import ErcotPublicApiService
from src.application.services.api_service.fmp_service.financial_modeling_prep_api_service import FMPCredentials, FinancialModelingPrepApiService
from src.application.services.api_service.fmp_service.get_equity_service import FmpEquityDataService
from src.application.services.api_service.ibkr_service.interactive_brokers_api_service import InteractiveBrokersApiService



if __name__ == '__main__':
    
    # ibkr_service = ComprehensiveIBMarketDataExamples()
    # #results_market_access = ibkr_service.test_account_access()
    # results = ibkr_service.example_fundamental_data()
    # print("")
    #ibkr_service.get_by_conid(745214300)
    #ibkr_service.vol_surf()
    
    #MarketMakingSPXCallSpreadV2ProjectManager().run()

    # --- Preload only (no backtest): the 10m project's 10-minute TRADES bars, price_history_start .. backtest_end ---
    # (run() already preloads by itself when config['preload_data'] is True; TWS client id 1 must be free)

    # import os
    # from src.application.managers.project_managers.spatio_temporal_momentum_project_10m import config as stm10m_config
    # from src.application.managers.project_managers.spatio_temporal_momentum_project_10m.models.model_trainer import PRELOAD_FILE
    # from src.application.services.data.backtest_preload.backtest_data_preload_service import BacktestDataPreloadService, PreloadSeries
    # from src.application.services.database_service.database_service import DatabaseService
    # from src.application.services.misbuffet.data.base_data_loader import BaseDataLoader
    # from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
    # cfg = stm10m_config.get_config()
    # stm = stm10m_config.build_stm_configuration(cfg)
    # database_service = DatabaseService(stm10m_config.CONFIG_TEST["DB_TYPE"])
    # database_service.set_ext_db()
    # mds = BaseDataLoader(database_service).market_data_service        # connects to TWS
    # series = [PreloadSeries(CompanyShare, t, "TRADES", cfg["bar_size_setting"]) for t in stm.universe.tickers]
    # service = BacktestDataPreloadService(mds, log=print)
    # results = service.preload(series, start=cfg["price_history_start"], end=cfg["backtest_end"])
    # os.makedirs(cfg["results_dir"], exist_ok=True)
    # service.to_frame(results).to_csv(os.path.join(cfg["results_dir"], PRELOAD_FILE), index=False)
    # mds.entity_service.repository_factory.ibkr_client.disconnect()

    # --- Preload only (no backtest): the cross-sectional project's 98 daily series, price_history_start .. backtest_end ---
    # (shares' TRADES + implied vol, SPY, IRX; CrossSectionnal().run() already preloads when config['preload_data'] is True;
    #  TWS client id 1 must be free)
    # import os
    # from src.application.managers.project_managers.cross_sectionnal_project import config as csm_project_config
    # from src.application.managers.project_managers.cross_sectionnal_project.models.model_trainer import PRELOAD_FILE as CSM_PRELOAD_FILE
    # from src.application.services.data.backtest_preload.backtest_data_preload_service import BacktestDataPreloadService
    # from src.application.services.data.entities.factor.cross_sectional_momentum.csm_preload import preload_series
    # from src.application.services.database_service.database_service import DatabaseService
    # from src.application.services.misbuffet.data.base_data_loader import BaseDataLoader
    # csm_cfg = csm_project_config.get_config()
    # csm = csm_project_config.build_csm_configuration(csm_cfg)
    # database_service = DatabaseService(csm_project_config.CONFIG_TEST["DB_TYPE"])
    # database_service.set_ext_db()
    # mds = BaseDataLoader(database_service).market_data_service        # connects to TWS
    # service = BacktestDataPreloadService(mds, log=print)
    # results = service.preload(preload_series(csm, csm_cfg["bar_size_setting"]),
    #                           start=csm_cfg["price_history_start"], end=csm_cfg["backtest_end"])
    # os.makedirs(csm_cfg["results_dir"], exist_ok=True)
    # service.to_frame(results).to_csv(os.path.join(csm_cfg["results_dir"], CSM_PRELOAD_FILE), index=False)
    # mds.entity_service.repository_factory.ibkr_client.disconnect()
    #CrossSectionnal().run()
    SpatioTemporalMomentum10mProjectManager().run()
    # import webbrowser, threading
    # from src.interfaces.flask.flask import FlaskApp
    # PORT = 5000
    # threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/dashboard")).start()
    # FlaskApp().run(debug=False, port=PORT)


    
        