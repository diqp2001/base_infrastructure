




import time
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_data import config
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal

class TestProjectDataManager(ProjectManager):
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

    
        