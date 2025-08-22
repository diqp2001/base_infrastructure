




from datetime import datetime

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project import config
from domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity

from infrastructure.repositories.local_repo.finance.financial_assets.company_stock_repository import CompanyStockRepository as CompanyStockRepositoryLocal
from infrastructure.repositories.afl_repo.finance.financial_assets.company_stock_repository.company_stock_repository import CompanyStockRepository as CompanyStockRepositoryAFL

class TestProjectManager(ProjectManager):
    """
    Project Manager for handling cross-sectional machine learning on stock returns.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_stock_repository_local = CompanyStockRepositoryLocal(self.database_manager.session)

    def save_new_company_stock(self):
        #add openfigi in the process
        id = 1
        ticker = 'XSU'
        exchange_id = 1
        company_id = 1
        start_date = datetime(2012,3,3)#'2016-06-06'
        end_date = datetime(2013,3,3)
        key_data = {
                        "key_id": [101, 102, 103],
                        "key_value": ["ValueA", "ValueB", "ValueC"],
                    }
        key_df = pd.DataFrame(key_data)
        
        
        self.database_manager.db.initialize_database_and_create_all_tables()
        
        
        stock_to_add = CompanyStockEntity(id, ticker, exchange_id, company_id,  start_date, end_date)
        print(self.database_manager.db.model_registry.base_factory.Base.metadata.tables.keys())
        self.company_stock_repository_local.add(domain_stock=stock_to_add, key_id=1, key_value=1,repo_id=1)
        t_o_n = self.company_stock_repository_local.exists_by_id(1)
        print(t_o_n)
        company_stock_entity_new = self.company_stock_repository_local.get_by_id(1)
        print(company_stock_entity_new)
        print(self.database_manager.db.model_registry.base_factory.Base.metadata.tables.keys())

        