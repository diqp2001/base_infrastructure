




from datetime import datetime
from typing import List, Dict
import logging

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project import config
from domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity

logger = logging.getLogger(__name__)

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

    def create_multiple_companies(self, companies_data: List[Dict], key_mappings: List[Dict]) -> List[CompanyStockEntity]:
        """
        Create multiple companies in a single bulk operation.
        
        Args:
            companies_data: List of dictionaries with company data
            key_mappings: List of dictionaries containing key_id, key_value, and repo_id
            
        Returns:
            List of created CompanyStock domain entities
        """
        try:
            # Use bulk operation instead of individual inserts
            companies = self.company_stock_repository_local.add_bulk_from_dicts(companies_data, key_mappings)
            logger.info(f"Successfully created {len(companies)} companies in bulk")
            return companies
        except Exception as e:
            logger.error(f"Error creating multiple companies: {str(e)}")
            raise

    def save_multiple_company_stocks_example(self):
        """
        Example method showing how to save multiple company stocks using bulk operations.
        """
        # Initialize database
        self.database_manager.db.initialize_database_and_create_all_tables()
        
        # Sample company data
        companies_data = [
            {
                "id": None,  # Let database auto-assign
                "ticker": "AAPL",
                "exchange_id": 1,
                "company_id": 1,
                "start_date": datetime(2020, 1, 1),
                "end_date": datetime(2023, 12, 31)
            },
            {
                "id": None,
                "ticker": "GOOGL", 
                "exchange_id": 1,
                "company_id": 2,
                "start_date": datetime(2020, 1, 1),
                "end_date": datetime(2023, 12, 31)
            },
            {
                "id": None,
                "ticker": "MSFT",
                "exchange_id": 1, 
                "company_id": 3,
                "start_date": datetime(2020, 1, 1),
                "end_date": datetime(2023, 12, 31)
            }
        ]
        
        # Key mappings for each company
        key_mappings = [
            {"key_id": 1, "key_value": 101, "repo_id": 1},
            {"key_id": 1, "key_value": 102, "repo_id": 1}, 
            {"key_id": 1, "key_value": 103, "repo_id": 1}
        ]
        
        try:
            # Create all companies in a single bulk operation
            created_companies = self.create_multiple_companies(companies_data, key_mappings)
            
            print(f"Successfully created {len(created_companies)} companies:")
            for company in created_companies:
                print(f"- {company.ticker}: ID {company.id}")
                
            # Verify they exist
            for company in created_companies:
                exists = self.company_stock_repository_local.exists_by_id(company.id)
                print(f"Company {company.ticker} exists: {exists}")
                
            return created_companies
            
        except Exception as e:
            logger.error(f"Error in bulk company creation example: {str(e)}")
            print(f"Error: {str(e)}")
            return []

        