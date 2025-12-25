

from cProfile import Profile
from pstats import SortKey, Stats


from src.application.managers.project_managers.cross_sectionnal_project.cross_sectionnal_project_manager import CrossSectionnal
from src.application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
from src.application.services.api_service.ercot_service.ercot_public_api_service import ErcotPublicApiService
from src.application.services.api_service.fmp_service.financial_modeling_prep_api_service import FMPCredentials, FinancialModelingPrepApiService
from src.application.services.api_service.fmp_service.get_equity_service import FmpEquityDataService
from src.application.services.api_service.ibkr_service.interactive_brokers_api_service import InteractiveBrokersApiService










if __name__ == '__main__':
    #TestBaseProjectManager().web_interface.start_interface_and_open_browser()
    #TestBaseProjectManager().run()
    #CrossSectionnal().run()
    ibkr_service = InteractiveBrokersApiService()
    ibkr_service.complete_pipeline()

   
    