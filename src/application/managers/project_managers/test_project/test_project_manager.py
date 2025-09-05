




import time
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project import config
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.company_share import CompanyStock as CompanyStockEntity  # Legacy compatibility
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_stock_repository import CompanyStockRepository as CompanyStockRepositoryLocal
from infrastructure.repositories.afl_repo.finance.financial_assets.company_stock_repository.company_stock_repository import CompanyStockRepository as CompanyStockRepositoryAFL

class TestProjectManager(ProjectManager):
    """
    Enhanced Project Manager for handling bulk database operations on company stocks.
    Implements QuantConnect-style Security/Equity architecture with performance optimization.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_stock_repository_local = CompanyStockRepositoryLocal(self.database_manager.session)

    def create_multiple_companies(self, companies_data: List[Dict], key_mappings: List[Dict]) -> List[CompanyStockEntity]:
        """
        Create multiple CompanyStock entities in a single atomic transaction.
        
        Args:
            companies_data: List of dicts containing company stock data
            key_mappings: List of dicts with key mapping information
            
        Returns:
            List[CompanyStockEntity]: Successfully created company stock entities
        """
        if not companies_data or not key_mappings:
            print("No data provided for bulk company creation")
            return []
            
        if len(companies_data) != len(key_mappings):
            raise ValueError("companies_data and key_mappings must have the same length")
        
        print(f"Creating {len(companies_data)} companies in bulk operation...")
        start_time = time.time()
        
        try:
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Validate and create domain entities
            domain_stocks = []
            for i, data in enumerate(companies_data):
                try:
                    domain_stock = CompanyStockEntity(
                        id=data['id'],
                        ticker=data['ticker'],
                        exchange_id=data['exchange_id'],
                        company_id=data['company_id'],
                        start_date=data['start_date'],
                        end_date=data.get('end_date')
                    )
                    
                    # Set company name if provided
                    if 'company_name' in data:
                        domain_stock.set_company_name(data['company_name'])
                    
                    # Set sector information if provided  
                    if 'sector' in data:
                        fundamentals = FundamentalData(sector=data['sector'])
                        domain_stock.update_company_fundamentals(fundamentals)
                    
                    domain_stocks.append(domain_stock)
                    
                except Exception as e:
                    print(f"Error creating domain entity {i}: {str(e)}")
                    raise
            
            # Use bulk repository operation
            created_entities = self.company_stock_repository_local.add_bulk(domain_stocks, key_mappings)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(f"✅ Successfully created {len(created_entities)} companies in {elapsed:.3f} seconds")
            print(f"⚡ Performance: {len(created_entities)/elapsed:.1f} companies/second")
            
            return created_entities
            
        except Exception as e:
            print(f"❌ Error in bulk company creation: {str(e)}")
            raise

    def create_sample_companies_with_market_data(self) -> List[CompanyStockEntity]:
        """
        Create sample companies with QuantConnect-style market data and fundamentals.
        Demonstrates the Security/Equity architecture implementation.
        """
        print("🏗️ Creating sample companies with QuantConnect-style architecture...")
        
        # Sample company data
        companies_data = [
            {
                'id': 1, 'ticker': 'AAPL', 'exchange_id': 1, 'company_id': 1,
                'start_date': datetime(2020, 1, 1), 'company_name': 'Apple Inc.',
                'sector': 'Technology'
            },
            {
                'id': 2, 'ticker': 'MSFT', 'exchange_id': 1, 'company_id': 2,
                'start_date': datetime(2020, 1, 1), 'company_name': 'Microsoft Corp.',
                'sector': 'Technology'
            },
            {
                'id': 3, 'ticker': 'GOOGL', 'exchange_id': 1, 'company_id': 3,
                'start_date': datetime(2020, 1, 1), 'company_name': 'Alphabet Inc.',
                'sector': 'Technology'
            }
        ]
        
        key_mappings = [
            {'key_id': i+1, 'key_value': f'KEY_{i+1}', 'repo_id': 1}
            for i in range(len(companies_data))
        ]
        
        # Create companies using bulk operation
        created_companies = self.create_multiple_companies(companies_data, key_mappings)
        
        if not created_companies:
            print("No companies were created")
            return []
        
        print(f"📊 Enhancing {len(created_companies)} companies with market data...")
        
        # Enhance companies with QuantConnect-style features
        for i, company in enumerate(created_companies):
            try:
                # Add market data
                market_data = MarketData(
                    timestamp=datetime.now(),
                    price=Decimal(str(100.0 + i * 10)),  # Sample prices
                    volume=1000000 + i * 100000
                )
                company.update_market_data(market_data)
                
                # Add fundamental data
                fundamentals = FundamentalData(
                    pe_ratio=Decimal(str(15.0 + i * 2)),
                    dividend_yield=Decimal(str(1.5 + i * 0.5)),
                    market_cap=Decimal(str(1000000000000 + i * 100000000000)),  # $1T+
                    shares_outstanding=1000000000 + i * 100000000,
                    sector=companies_data[i]['sector'],
                    industry='Software' if i < 2 else 'Internet Services'
                )
                company.update_company_fundamentals(fundamentals)
                
                # Add sample dividend
                dividend = Dividend(
                    amount=Decimal(str(0.25 + i * 0.1)),
                    ex_date=datetime(2024, 3, 15),
                    pay_date=datetime(2024, 3, 30)
                )
                company.add_dividend(dividend)
                
                # Print company metrics
                metrics = company.get_company_metrics()
                print(f"📈 {company.ticker}: Price=${metrics['current_price']}, "
                      f"P/E={metrics['pe_ratio']}, Div Yield={metrics['dividend_yield']}%")
                
            except Exception as e:
                print(f"Error enhancing company {company.ticker}: {str(e)}")
                continue
        
        return created_companies

    def demonstrate_bulk_operations(self, num_companies: int = 100) -> None:
        """
        Demonstrate bulk operations performance with configurable company count.
        Shows the performance difference between single and bulk operations.
        """
        print(f"🚀 Demonstrating bulk operations with {num_companies} companies...")
        
        # Generate test data
        companies_data = [
            {
                'id': i,
                'ticker': f'STOCK{i:03d}',
                'exchange_id': 1,
                'company_id': i,
                'start_date': datetime(2024, 1, 1),
                'company_name': f'Company {i}',
                'sector': 'Technology' if i % 3 == 0 else 'Healthcare' if i % 3 == 1 else 'Finance'
            }
            for i in range(1, num_companies + 1)
        ]
        
        key_mappings = [
            {'key_id': i, 'key_value': f'BULK_KEY_{i}', 'repo_id': 1}
            for i in range(1, num_companies + 1)
        ]
        
        print("⏱️ Performance comparison:")
        print(f"📊 Bulk operation (atomic transaction): Creating {num_companies} companies...")
        
        start_time = time.time()
        created_companies = self.create_multiple_companies(companies_data, key_mappings)
        end_time = time.time()
        
        bulk_time = end_time - start_time
        
        print(f"✅ Bulk operation completed in {bulk_time:.3f} seconds")
        print(f"⚡ Performance: {len(created_companies)/bulk_time:.1f} companies/second")
        print(f"🎯 Database operations: ~3 (vs {num_companies * 3} for sequential)")
        print(f"💾 Transaction overhead: 1 commit (vs {num_companies} commits for sequential)")
        
        # Demonstrate additional bulk features
        if created_companies:
            print("\n🔧 Testing additional bulk operations...")
            
            # Test bulk update
            updates = [
                {'id': company.id, 'ticker': f'UPD_{company.ticker}'}
                for company in created_companies[:5]
            ]
            
            updated_count = self.company_stock_repository_local.update_bulk(updates)
            print(f"📝 Bulk updated {updated_count} companies")
            
            # Test bulk delete (cleanup last 10 companies)
            cleanup_ids = [company.id for company in created_companies[-10:]]
            deleted_count = self.company_stock_repository_local.delete_bulk(cleanup_ids)
            print(f"🗑️ Bulk deleted {deleted_count} companies for cleanup")

    def save_new_company_stock(self):
        """
        Legacy single company creation method (maintained for backwards compatibility).
        """
        print("📝 Creating single company stock (legacy method)...")
        
        # Legacy single company creation
        id = 1
        ticker = 'XSU'
        exchange_id = 1
        company_id = 1
        start_date = datetime(2012, 3, 3)
        end_date = datetime(2013, 3, 3)
        
        self.database_manager.db.initialize_database_and_create_all_tables()
        
        stock_to_add = CompanyStockEntity(id, ticker, exchange_id, company_id, start_date, end_date)
        print("Available tables:", list(self.database_manager.db.model_registry.base_factory.Base.metadata.tables.keys()))
        
        self.company_stock_repository_local.add(domain_stock=stock_to_add, key_id=1, key_value=1, repo_id=1)
        
        exists = self.company_stock_repository_local.exists_by_id(1)
        print(f"Company stock exists: {exists}")
        
        company_stock_entity = self.company_stock_repository_local.get_by_id(1)
        print(f"Retrieved entity: {company_stock_entity}")
        
        print("✅ Legacy single company creation completed")

    def save_multiple_company_stocks_example(self):
        """
        Example demonstrating complete bulk operation workflow.
        Shows integration of bulk operations with QuantConnect-style architecture.
        """
        print("🌟 Running complete bulk operations example...")
        
        try:
            # Initialize database
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Create sample companies with full QuantConnect features
            companies = self.create_sample_companies_with_market_data()
            
            if companies:
                print(f"\n📋 Summary of created companies:")
                for company in companies:
                    trading_info = company.get_trading_period()
                    print(f"  • {company} - Active: {trading_info['is_active']}")
            
            # Demonstrate bulk operations performance
            self.demonstrate_bulk_operations(50)  # Test with 50 companies
            
            print("\n🎉 Bulk operations example completed successfully!")
            
        except Exception as e:
            print(f"❌ Error in bulk operations example: {str(e)}")
            raise

        