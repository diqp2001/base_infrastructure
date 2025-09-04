




"""Enhanced TestProjectManager with bulk operations and improved security/equity architecture."""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project import config
from domain.entities.finance.financial_assets.company_stock import CompanyStock as CompanyStockEntity
from domain.entities.finance.financial_assets.security import MarketData
from domain.entities.finance.financial_assets.stock import Dividend, StockSplit

from infrastructure.repositories.local_repo.finance.financial_assets.company_stock_repository import CompanyStockRepository as CompanyStockRepositoryLocal
from infrastructure.repositories.afl_repo.finance.financial_assets.company_stock_repository.company_stock_repository import CompanyStockRepository as CompanyStockRepositoryAFL

logger = logging.getLogger(__name__)

class TestProjectManager(ProjectManager):
    """
    Project Manager for handling cross-sectional machine learning on stock returns.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_stock_repository_local = CompanyStockRepositoryLocal(self.database_manager.session)
        
        # Performance tracking
        self._bulk_operation_stats = {
            'total_created': 0,
            'total_updated': 0,
            'total_deleted': 0,
            'last_operation_time': None
        }

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
    
    def create_multiple_companies(self, 
                                companies_data: List[Dict[str, Any]], 
                                key_mappings: List[Dict[str, Any]]) -> List[CompanyStockEntity]:
        """
        Create multiple CompanyStock entities in a single bulk operation.
        
        Args:
            companies_data: List of dictionaries containing company stock data
            key_mappings: List of dictionaries containing key_id, key_value, repo_id
            
        Returns:
            List of created CompanyStock entities
            
        Raises:
            ValueError: If validation fails
            Exception: If bulk operation fails
        """
        if not companies_data or not key_mappings:
            raise ValueError("Companies data and key mappings cannot be empty")
            
        if len(companies_data) != len(key_mappings):
            raise ValueError("Number of companies must match number of key mappings")
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting bulk creation of {len(companies_data)} companies")
            
            # Initialize database tables if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Use bulk repository operation
            created_companies = self.company_stock_repository_local.add_bulk_from_dicts(
                companies_data, key_mappings
            )
            
            # Update performance stats
            operation_time = datetime.now() - start_time
            self._bulk_operation_stats['total_created'] += len(created_companies)
            self._bulk_operation_stats['last_operation_time'] = operation_time.total_seconds()
            
            logger.info(
                f"Successfully created {len(created_companies)} companies in "
                f"{operation_time.total_seconds():.2f} seconds"
            )
            
            return created_companies
            
        except Exception as e:
            logger.error(f"Error creating multiple companies: {str(e)}")
            raise
    
    def create_sample_companies_with_market_data(self) -> List[CompanyStockEntity]:
        """
        Create sample companies with enhanced market data following QuantConnect patterns.
        
        Returns:
            List of created CompanyStock entities with market data
        """
        # Sample companies data with enhanced attributes
        companies_data = [
            {
                'id': 1,
                'ticker': 'AAPL',
                'exchange_id': 1,
                'company_id': 1,
                'start_date': datetime(2020, 1, 1),
                'end_date': datetime(2024, 12, 31),
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'market_cap': Decimal('3000000000000'),  # $3T
                'shares_outstanding': 15000000000,  # 15B shares
                'leverage': Decimal('1.0')
            },
            {
                'id': 2,
                'ticker': 'GOOGL',
                'exchange_id': 1,
                'company_id': 2,
                'start_date': datetime(2020, 1, 1),
                'end_date': datetime(2024, 12, 31),
                'sector': 'Technology',
                'industry': 'Internet Services',
                'market_cap': Decimal('2000000000000'),  # $2T
                'shares_outstanding': 12500000000,  # 12.5B shares
                'leverage': Decimal('1.0')
            },
            {
                'id': 3,
                'ticker': 'MSFT',
                'exchange_id': 1,
                'company_id': 3,
                'start_date': datetime(2020, 1, 1),
                'end_date': datetime(2024, 12, 31),
                'sector': 'Technology',
                'industry': 'Software',
                'market_cap': Decimal('2800000000000'),  # $2.8T
                'shares_outstanding': 7400000000,  # 7.4B shares
                'leverage': Decimal('1.0')
            }
        ]
        
        # Key mappings for each company
        key_mappings = [
            {'key_id': 101, 'key_value': 'AAPL_KEY', 'repo_id': 1},
            {'key_id': 102, 'key_value': 'GOOGL_KEY', 'repo_id': 1},
            {'key_id': 103, 'key_value': 'MSFT_KEY', 'repo_id': 1}
        ]
        
        try:
            # Create companies using bulk operation
            created_companies = self.create_multiple_companies(companies_data, key_mappings)
            
            # Add sample market data and corporate actions
            self._add_sample_market_data(created_companies)
            
            logger.info(f"Created {len(created_companies)} sample companies with market data")
            return created_companies
            
        except Exception as e:
            logger.error(f"Error creating sample companies: {str(e)}")
            raise
    
    def _add_sample_market_data(self, companies: List[CompanyStockEntity]) -> None:
        """
        Add sample market data and corporate actions to companies.
        
        Args:
            companies: List of CompanyStock entities to enhance
        """
        sample_prices = {
            'AAPL': Decimal('200.50'),
            'GOOGL': Decimal('160.25'),
            'MSFT': Decimal('378.90')
        }
        
        for company in companies:
            ticker = company.ticker
            
            # Add market data
            if ticker in sample_prices:
                market_data = MarketData(
                    price=sample_prices[ticker],
                    bid=sample_prices[ticker] - Decimal('0.05'),
                    ask=sample_prices[ticker] + Decimal('0.05'),
                    volume=1000000,
                    timestamp=datetime.now()
                )
                company.update_market_data(market_data)
            
            # Add sample dividends for demonstration
            if ticker == 'AAPL':
                dividend = Dividend(
                    amount=Decimal('0.25'),
                    ex_date=datetime(2024, 2, 15),
                    pay_date=datetime(2024, 2, 28),
                    record_date=datetime(2024, 2, 16)
                )
                company.add_dividend(dividend)
            
            elif ticker == 'MSFT':
                dividend = Dividend(
                    amount=Decimal('0.75'),
                    ex_date=datetime(2024, 2, 20),
                    pay_date=datetime(2024, 3, 10),
                    record_date=datetime(2024, 2, 21)
                )
                company.add_dividend(dividend)
    
    def demonstrate_bulk_operations(self) -> Dict[str, Any]:
        """
        Demonstrate the bulk operations capabilities with performance metrics.
        
        Returns:
            Dictionary containing operation results and performance metrics
        """
        results = {
            'companies_created': [],
            'performance_metrics': {},
            'operations_performed': []
        }
        
        try:
            # Create sample companies
            start_time = datetime.now()
            companies = self.create_sample_companies_with_market_data()
            creation_time = datetime.now() - start_time
            
            results['companies_created'] = [{
                'ticker': company.ticker,
                'sector': company.sector,
                'current_price': str(company.current_price) if company.current_price else None,
                'dividend_yield': str(company.calculate_dividend_yield()),
                'market_cap': str(company.calculate_market_cap()) if company.calculate_market_cap() else None
            } for company in companies]
            
            # Performance metrics
            results['performance_metrics'] = {
                'creation_time_seconds': creation_time.total_seconds(),
                'companies_per_second': len(companies) / creation_time.total_seconds(),
                'total_created': self._bulk_operation_stats['total_created'],
                'database_operations_saved': (len(companies) * 3) - 1  # Each company would need 3 ops, now just 1
            }
            
            results['operations_performed'] = [
                'Bulk company creation with atomic transactions',
                'Market data initialization',
                'Corporate actions (dividends) setup',
                'Performance metrics calculation'
            ]
            
            logger.info(f"Bulk operations demonstration completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk operations demonstration: {str(e)}")
            results['error'] = str(e)
            return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for bulk operations.
        
        Returns:
            Dictionary containing performance statistics
        """
        return self._bulk_operation_stats.copy()
    
    def save_multiple_company_stocks_example(self) -> Dict[str, Any]:
        """
        Example method showing how to use the new bulk operations.
        
        Returns:
            Dictionary with operation results
        """
        logger.info("Running bulk company stock creation example")
        
        try:
            # Run the demonstration
            results = self.demonstrate_bulk_operations()
            
            logger.info("Bulk operations example completed successfully")
            logger.info(f"Performance: {results.get('performance_metrics', {})}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk example: {str(e)}")
            return {'error': str(e)}