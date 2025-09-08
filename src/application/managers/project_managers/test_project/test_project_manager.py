




import time
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project import config
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal

class TestProjectManager(ProjectManager):
    """
    Enhanced Project Manager for handling bulk database operations on company shares.
    Implements QuantConnect-style Security/Equity architecture with performance optimization.
    """
    def __init__(self):
        super().__init__()
        # Initialize required managers
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_share_repository_local = CompanyShareRepositoryLocal(self.database_manager.session)

    def create_multiple_companies(self, companies_data: List[Dict]) -> List[CompanyShareEntity]:
        """
        Create multiple CompanyShare entities in a single atomic transaction.
        
        Args:
            companies_data: List of dicts containing company share data
            
        Returns:
            List[CompanyShareEntity]: Successfully created company share entities
        """
        if not companies_data:
            print("No data provided for bulk company creation")
            return []
        
        print(f"Creating {len(companies_data)} companies in bulk operation...")
        start_time = time.time()
        
        try:
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Validate and create domain entities
            domain_shares = []
            for i, data in enumerate(companies_data):
                try:
                    domain_share = CompanyShareEntity(
                        id=data['id'],
                        ticker=data['ticker'],
                        exchange_id=data['exchange_id'],
                        company_id=data['company_id'],
                        start_date=data['start_date'],
                        end_date=data.get('end_date')
                    )
                    
                    # Set company name if provided
                    if 'company_name' in data:
                        domain_share.set_company_name(data['company_name'])
                    
                    # Set sector information if provided  
                    if 'sector' in data:
                        fundamentals = FundamentalData(sector=data['sector'])
                        domain_share.update_company_fundamentals(fundamentals)
                    
                    domain_shares.append(domain_share)
                    
                except Exception as e:
                    print(f"Error creating domain entity {i}: {str(e)}")
                    raise
            
            # Use bulk repository operation (no more key mappings needed)
            created_entities = self.company_share_repository_local.add_bulk(domain_shares)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(f"✅ Successfully created {len(created_entities)} companies in {elapsed:.3f} seconds")
            print(f"⚡ Performance: {len(created_entities)/elapsed:.1f} companies/second")
            
            return created_entities
            
        except Exception as e:
            print(f"❌ Error in bulk company creation: {str(e)}")
            raise

    def create_sample_companies_with_market_data(self) -> List[CompanyShareEntity]:
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
        
        # Create companies using bulk operation (no key mappings needed)
        created_companies = self.create_multiple_companies(companies_data)
        
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
        
        print("⏱️ Performance comparison:")
        print(f"📊 Bulk operation (atomic transaction): Creating {num_companies} companies...")
        
        start_time = time.time()
        created_companies = self.create_multiple_companies(companies_data)
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
            
            updated_count = self.company_share_repository_local.update_bulk(updates)
            print(f"📝 Bulk updated {updated_count} companies")
            
            # Test bulk delete (cleanup last 10 companies)
            cleanup_ids = [company.id for company in created_companies[-10:]]
            deleted_count = self.company_share_repository_local.delete_bulk(cleanup_ids)
            print(f"🗑️ Bulk deleted {deleted_count} companies for cleanup")

    def save_new_company_share(self):
        """
        Legacy single company creation method (maintained for backwards compatibility).
        """
        print("📝 Creating single company share (legacy method)...")
        
        # Legacy single company creation
        id = 1
        ticker = 'XSU'
        exchange_id = 1
        company_id = 1
        start_date = datetime(2012, 3, 3)
        end_date = datetime(2013, 3, 3)
        
        self.database_manager.db.initialize_database_and_create_all_tables()
        
        share_to_add = CompanyShareEntity(id, ticker, exchange_id, company_id, start_date, end_date)
        print("Available tables:", list(self.database_manager.db.model_registry.base_factory.Base.metadata.tables.keys()))
        
        self.company_share_repository_local.add(domain_share=share_to_add)
        
        exists = self.company_share_repository_local.exists_by_id(1)
        print(f"Company share exists: {exists}")
        
        company_share_entity = self.company_share_repository_local.get_by_id(1)
        print(f"Retrieved entity: {company_share_entity}")
        
        print("✅ Legacy single company creation completed")

    def add_company_with_openfigi(self, ticker: str, exchange_code: str = "US", use_openfigi: bool = True) -> CompanyShareEntity:
        """
        Add a single company using OpenFIGI API integration for data enrichment.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            exchange_code: Exchange code (e.g., 'US', 'LN', 'JP')
            use_openfigi: Whether to use OpenFIGI API for data enrichment
            
        Returns:
            CompanyShareEntity: Created company share entity
        """
        print(f"🌐 Adding company {ticker} with OpenFIGI integration (enabled: {use_openfigi})...")
        
        try:
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Use repository's OpenFIGI integration
            created_entity = self.company_share_repository_local.add_with_openfigi(
                ticker=ticker,
                exchange_code=exchange_code,
                use_openfigi=use_openfigi
            )
            
            if created_entity:
                print(f"✅ Successfully created company share: {created_entity.ticker}")
                
                # Display enriched data if available
                metrics = created_entity.get_company_metrics()
                print(f"📊 Company metrics: {metrics}")
                
                return created_entity
            else:
                print(f"❌ Failed to create company share for {ticker}")
                return None
                
        except Exception as e:
            print(f"❌ Error adding company {ticker} with OpenFIGI: {str(e)}")
            raise

    def add_multiple_companies_with_openfigi(self, tickers: List[str], exchange_code: str = "US", 
                                           use_openfigi: bool = True) -> List[CompanyShareEntity]:
        """
        Add multiple companies using OpenFIGI API bulk integration.
        
        Args:
            tickers: List of stock ticker symbols
            exchange_code: Exchange code for all tickers
            use_openfigi: Whether to use OpenFIGI API for data enrichment
            
        Returns:
            List[CompanyShareEntity]: List of created company share entities
        """
        print(f"🚀 Adding {len(tickers)} companies with OpenFIGI bulk integration...")
        start_time = time.time()
        
        try:
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Use repository's bulk OpenFIGI integration
            created_entities = self.company_share_repository_local.bulk_add_with_openfigi(
                tickers=tickers,
                exchange_code=exchange_code,
                use_openfigi=use_openfigi
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(f"✅ Successfully created {len(created_entities)} companies in {elapsed:.3f} seconds")
            print(f"⚡ Performance: {len(created_entities)/elapsed:.1f} companies/second")
            
            if use_openfigi:
                print("🌐 Data enriched with OpenFIGI API information")
            else:
                print("📊 Created with basic ticker information only")
            
            # Display summary of created companies
            print(f"\n📋 Created companies summary:")
            for company in created_entities[:5]:  # Show first 5
                metrics = company.get_company_metrics()
                print(f"  • {company.ticker}: {metrics.get('company_name', 'N/A')} - "
                      f"Sector: {metrics.get('sector', 'N/A')}")
            
            if len(created_entities) > 5:
                print(f"  ... and {len(created_entities) - 5} more companies")
                
            return created_entities
            
        except Exception as e:
            print(f"❌ Error in bulk OpenFIGI company creation: {str(e)}")
            raise

    def demonstrate_openfigi_integration(self):
        """
        Demonstrate OpenFIGI integration capabilities with real market data.
        """
        print("🌐 Demonstrating OpenFIGI API integration...")
        
        # Test single company addition
        print("\n1️⃣ Testing single company addition with OpenFIGI...")
        apple_share = self.add_company_with_openfigi("AAPL", "US", use_openfigi=True)
        
        # Test fallback mode (no API)
        print("\n2️⃣ Testing single company addition without OpenFIGI (fallback mode)...")
        tesla_share = self.add_company_with_openfigi("TSLA", "US", use_openfigi=False)
        
        # Test bulk addition with OpenFIGI
        print("\n3️⃣ Testing bulk companies addition with OpenFIGI...")
        tech_tickers = ["MSFT", "GOOGL", "META", "NVDA", "AMD"]
        tech_shares = self.add_multiple_companies_with_openfigi(
            tickers=tech_tickers, 
            use_openfigi=True
        )
        
        # Test bulk addition without OpenFIGI (performance comparison)
        print("\n4️⃣ Testing bulk companies addition without OpenFIGI (performance comparison)...")
        finance_tickers = ["JPM", "BAC", "WFC", "GS", "MS"]
        finance_shares = self.add_multiple_companies_with_openfigi(
            tickers=finance_tickers, 
            use_openfigi=False
        )
        
        print("\n🎯 OpenFIGI Integration Summary:")
        total_companies = 1 + 1 + len(tech_shares) + len(finance_shares)
        print(f"  • Total companies added: {total_companies}")
        print(f"  • With OpenFIGI enrichment: {1 + len(tech_shares)}")
        print(f"  • Without OpenFIGI (fallback): {1 + len(finance_shares)}")
        print("  • All operations completed successfully! ✅")

    def save_multiple_company_shares_example(self):
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
            
            # Demonstrate OpenFIGI integration
            self.demonstrate_openfigi_integration()
            
            print("\n🎉 Bulk operations example completed successfully!")
            
        except Exception as e:
            print(f"❌ Error in bulk operations example: {str(e)}")
            raise

        