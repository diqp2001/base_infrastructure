




from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project import config
from domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity

from infrastructure.repositories.local_repo.finance.financial_assets.company_stock_repository import CompanyStockRepository


class TestProjectManager(ProjectManager):
    """
    Project Manager for handling cross-sectional machine learning on stock returns.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_stock_repository = CompanyStockRepository(self.database_manager.session)

    def save_new_company_stock(self):
        id = 1
        ticker = 'XSU'
        exchange_id = 1
        company_id = 1
        start_date = '2016-06-06'
        end_date = None
        company_stock_entity = CompanyStockEntity(id, ticker, exchange_id, company_id,  start_date, end_date)
        
        
        #self.database_manager.db.initialize_database_and_create_all_tables()
        
        #self.database_manager.db.model_registry.base_factory.Base.metadata.tables.keys()
        
        
        self.company_stock_repository.save_list([company_stock_entity])
        t_o_n = self.company_stock_repository.exists_by_id(1)
        company_stock_entity_new = self.company_stock_repository.get_by_id(1)
        

        