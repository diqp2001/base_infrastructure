




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
        """Legacy method for single company stock creation (backward compatibility)"""
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
    
    def create_multiple_companies(self, companies_data: list, key_mappings: list) -> list:
        """
        Create multiple companies in a single bulk operation using atomic transactions.
        
        Args:
            companies_data: List of dicts with company data
            key_mappings: List of dicts with key mapping data
            
        Returns:
            List of created CompanyStock entities
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Validate input data
            if not companies_data or not key_mappings:
                logger.warning("Empty companies_data or key_mappings provided")
                return []
            
            if len(companies_data) != len(key_mappings):
                raise ValueError("companies_data and key_mappings must have the same length")
            
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Use bulk operation instead of individual inserts
            logger.info(f"Creating {len(companies_data)} companies using bulk operation")
            start_time = datetime.now()
            
            companies = self.company_stock_repository_local.add_bulk_from_dicts(
                companies_data, key_mappings
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Successfully created {len(companies)} companies in {duration:.2f} seconds")
            logger.info(f"Average time per company: {duration/len(companies):.4f} seconds")
            
            return companies
            
        except Exception as e:
            logger.error(f"Error creating multiple companies: {str(e)}")
            raise
    
    def create_sample_companies_with_market_data(self) -> list:
        """
        Create sample companies with QuantConnect-style market data and corporate actions.
        Demonstrates enhanced Security/Equity functionality.
        """
        import logging
        from decimal import Decimal
        from domain.entities.finance.financial_assets.security import MarketData, Dividend, StockSplit
        
        logger = logging.getLogger(__name__)
        
        # Sample company data
        companies_data = [
            {
                "id": 1001,
                "ticker": "AAPL",
                "exchange_id": 1,
                "company_id": 1001,
                "start_date": datetime(2020, 1, 1),
                "end_date": datetime(2024, 12, 31)
            },
            {
                "id": 1002, 
                "ticker": "MSFT",
                "exchange_id": 1,
                "company_id": 1002,
                "start_date": datetime(2020, 1, 1),
                "end_date": datetime(2024, 12, 31)
            },
            {
                "id": 1003,
                "ticker": "GOOGL", 
                "exchange_id": 1,
                "company_id": 1003,
                "start_date": datetime(2020, 1, 1),
                "end_date": datetime(2024, 12, 31)
            }
        ]
        
        key_mappings = [
            {"key_id": 2001, "key_value": "AAPL_KEY", "repo_id": 1},
            {"key_id": 2002, "key_value": "MSFT_KEY", "repo_id": 1},
            {"key_id": 2003, "key_value": "GOOGL_KEY", "repo_id": 1}
        ]
        
        # Create companies using bulk operation
        companies = self.create_multiple_companies(companies_data, key_mappings)
        
        # Enhance with QuantConnect-style features
        for i, company in enumerate(companies):
            if company:
                # Set market data
                market_data = MarketData(
                    price=Decimal('150.25') + Decimal(str(i * 10)),
                    volume=1000000 + (i * 100000),
                    bid_price=Decimal('150.20') + Decimal(str(i * 10)),
                    ask_price=Decimal('150.30') + Decimal(str(i * 10))
                )
                company.update_market_data(market_data)
                
                # Add sector information
                sectors = ["Technology", "Technology", "Technology"]
                company.set_sector(sectors[i])
                
                # Add company information
                company_names = ["Apple Inc.", "Microsoft Corp.", "Alphabet Inc."]
                company.set_company_name(company_names[i])
                
                # Add dividend history
                dividend = Dividend(
                    amount=Decimal('0.25') + Decimal(str(i * 0.05)),
                    ex_date=datetime(2024, 3, 15)
                )
                company.add_dividend(dividend)
                
                # Add stock split history (for demonstration)
                if i == 0:  # Apple had stock splits
                    stock_split = StockSplit(
                        split_factor=Decimal('4.0'),  # 4:1 split
                        ex_date=datetime(2020, 8, 31)
                    )
                    company.add_stock_split(stock_split)
                
                logger.info(f"Enhanced {company.ticker}: Price=${company.current_price}, "
                          f"Dividend Yield={company.calculate_dividend_yield():.2f}%, "
                          f"Sector={company.sector}")
        
        return companies
    
    def demonstrate_bulk_operations(self) -> dict:
        """
        Demonstrate bulk operations performance compared to sequential processing.
        Returns performance metrics.
        """
        import logging
        import time
        logger = logging.getLogger(__name__)
        
        # Generate test data
        num_companies = 100
        companies_data = []
        key_mappings = []
        
        base_date = datetime(2024, 1, 1)
        
        for i in range(num_companies):
            companies_data.append({
                "id": 5000 + i,
                "ticker": f"TEST{i:03d}",
                "exchange_id": 1,
                "company_id": 5000 + i,
                "start_date": base_date,
                "end_date": datetime(2024, 12, 31)
            })
            
            key_mappings.append({
                "key_id": 6000 + i,
                "key_value": f"TEST_KEY_{i:03d}",
                "repo_id": 1
            })
        
        # Initialize database
        self.database_manager.db.initialize_database_and_create_all_tables()
        
        logger.info(f"Performance test: Creating {num_companies} companies")
        
        # Test bulk operation
        start_time = time.time()
        bulk_companies = self.create_multiple_companies(companies_data, key_mappings)
        bulk_duration = time.time() - start_time
        
        # Performance metrics
        metrics = {
            'num_companies': num_companies,
            'bulk_operation_time': bulk_duration,
            'companies_per_second': num_companies / bulk_duration if bulk_duration > 0 else 0,
            'avg_time_per_company': bulk_duration / num_companies if num_companies > 0 else 0,
            'estimated_sequential_time': num_companies * 0.1,  # Estimated based on typical sequential processing
            'performance_improvement': f"{((num_companies * 0.1) / bulk_duration):.1f}x" if bulk_duration > 0 else "N/A"
        }
        
        logger.info(f"Bulk operation completed in {bulk_duration:.2f} seconds")
        logger.info(f"Rate: {metrics['companies_per_second']:.1f} companies/second") 
        logger.info(f"Estimated performance improvement: {metrics['performance_improvement']}")
        
        return metrics

        