




import time
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_data import config
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.currency import Currency as CurrencyEntity
from domain.entities.finance.financial_assets.equity import  Dividend
from domain.entities.finance.financial_assets.security import MarketData

from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository as CurrencyRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository

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
        self.currency_repository_local = CurrencyRepositoryLocal(self.database_manager.session)
        
        # Initialize factor repositories
        self.currency_factor_repository = CurrencyFactorRepository(config.CONFIG_TEST['DB_TYPE'])
        self.share_factor_repository = ShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])

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

    def import_fx_historical_data(self, data_path: str = None) -> Dict[str, Any]:
        """
        Import historical FX data from CSV and populate currency factors.
        
        Args:
            data_path: Path to FX data CSV file. If None, uses default path.
            
        Returns:
            Dict with import summary
        """
        if data_path is None:
            # Default path based on project structure
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
            data_path = os.path.join(project_root, "data", "fx_data", "currency_exchange_rates_02-01-1995_-_02-05-2018.csv")
        
        print(f"💱 Importing FX historical data from: {data_path}")
        start_time = time.time()
        
        try:
            # Initialize database
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Read CSV data
            df = pd.read_csv(data_path)
            print(f"📊 Loaded {len(df)} rows of FX data with {len(df.columns)-1} currencies")
            
            # Parse date column
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Get currency columns (all except Date)
            currency_columns = [col for col in df.columns if col != 'Date']
            
            # Create currency factors for each type (exchange_rate)
            factors_created = []
            values_imported = 0
            
            for currency_name in currency_columns:
                print(f"Processing currency: {currency_name}")
                
                # Create or get currency entity
                currency_entity = self._get_or_create_currency(currency_name)
                
                # Create factor for exchange rate
                factor = self._create_fx_factor(currency_name, "exchange_rate_usd")
                factors_created.append(factor)
                
                # Import historical values
                currency_data = df[['Date', currency_name]].dropna()
                for _, row in currency_data.iterrows():
                    value = float(row[currency_name])
                    if value > 0:  # Only valid exchange rates
                        self.currency_factor_repository.add_factor_value(
                            factor_id=factor.id,
                            entity_id=currency_entity.id,
                            date=row['Date'].date(),
                            value=Decimal(str(value))
                        )
                        values_imported += 1
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            summary = {
                'currencies_processed': len(currency_columns),
                'factors_created': len(factors_created),
                'values_imported': values_imported,
                'processing_time': elapsed,
                'data_file': data_path
            }
            
            print(f"✅ FX Data Import Complete:")
            print(f"  • Currencies processed: {summary['currencies_processed']}")
            print(f"  • Factors created: {summary['factors_created']}")
            print(f"  • Values imported: {summary['values_imported']}")
            print(f"  • Processing time: {elapsed:.3f} seconds")
            print(f"  • Rate: {values_imported/elapsed:.1f} values/second")
            
            return summary
            
        except Exception as e:
            print(f"❌ Error importing FX data: {str(e)}")
            raise

    def import_stock_historical_data(self, data_dir: str = None) -> Dict[str, Any]:
        """
        Import historical stock data from CSV files and populate share factors.
        
        Args:
            data_dir: Path to stock data directory. If None, uses default path.
            
        Returns:
            Dict with import summary
        """
        if data_dir is None:
            # Default path based on project structure
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
            data_dir = os.path.join(project_root, "data", "stock_data")
        
        print(f"📈 Importing stock historical data from: {data_dir}")
        start_time = time.time()
        
        try:
            # Initialize database
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Get all CSV files in the directory
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
            print(f"📊 Found {len(csv_files)} stock data files")
            
            factors_created = []
            values_imported = 0
            companies_processed = 0
            
            for csv_file in csv_files:
                ticker = csv_file.replace('.csv', '')
                file_path = os.path.join(data_dir, csv_file)
                
                print(f"Processing stock: {ticker}")
                
                # Read CSV data
                df = pd.read_csv(file_path)
                df['Date'] = pd.to_datetime(df['Date'])
                
                # Create or get company share entity
                share_entity = self._get_or_create_company_share(ticker)
                
                # Create factors for OHLCV data
                price_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close']
                volume_column = 'Volume'
                
                # Create price factors
                for price_type in price_columns:
                    if price_type in df.columns:
                        factor = self._create_stock_factor(ticker, price_type.lower().replace(' ', '_'))
                        factors_created.append(factor)
                        
                        # Import historical values
                        price_data = df[['Date', price_type]].dropna()
                        for _, row in price_data.iterrows():
                            self.share_factor_repository.add_factor_value(
                                factor_id=factor.id,
                                entity_id=share_entity.id,
                                date=row['Date'].date(),
                                value=Decimal(str(row[price_type]))
                            )
                            values_imported += 1
                
                # Create volume factor
                if volume_column in df.columns:
                    factor = self._create_stock_factor(ticker, 'volume')
                    factors_created.append(factor)
                    
                    # Import volume values
                    volume_data = df[['Date', volume_column]].dropna()
                    for _, row in volume_data.iterrows():
                        self.share_factor_repository.add_factor_value(
                            factor_id=factor.id,
                            entity_id=share_entity.id,
                            date=row['Date'].date(),
                            value=Decimal(str(row[volume_column]))
                        )
                        values_imported += 1
                
                companies_processed += 1
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            summary = {
                'companies_processed': companies_processed,
                'factors_created': len(factors_created),
                'values_imported': values_imported,
                'processing_time': elapsed,
                'data_directory': data_dir
            }
            
            print(f"✅ Stock Data Import Complete:")
            print(f"  • Companies processed: {summary['companies_processed']}")
            print(f"  • Factors created: {summary['factors_created']}")
            print(f"  • Values imported: {summary['values_imported']}")
            print(f"  • Processing time: {elapsed:.3f} seconds")
            print(f"  • Rate: {values_imported/elapsed:.1f} values/second")
            
            return summary
            
        except Exception as e:
            print(f"❌ Error importing stock data: {str(e)}")
            raise

    def import_all_historical_data(self) -> Dict[str, Any]:
        """
        Import both FX and stock historical data in one operation.
        
        Returns:
            Dict with combined import summary
        """
        print("🚀 Starting comprehensive historical data import...")
        total_start_time = time.time()
        
        try:
            # Import FX data
            fx_summary = self.import_fx_historical_data()
            
            # Import stock data
            stock_summary = self.import_stock_historical_data()
            
            total_end_time = time.time()
            total_elapsed = total_end_time - total_start_time
            
            combined_summary = {
                'fx_import': fx_summary,
                'stock_import': stock_summary,
                'total_factors': fx_summary['factors_created'] + stock_summary['factors_created'],
                'total_values': fx_summary['values_imported'] + stock_summary['values_imported'],
                'total_time': total_elapsed
            }
            
            print(f"\n🎯 Complete Historical Data Import Summary:")
            print(f"  • Total factors created: {combined_summary['total_factors']}")
            print(f"  • Total values imported: {combined_summary['total_values']}")
            print(f"  • Total processing time: {total_elapsed:.3f} seconds")
            print(f"  • Overall rate: {combined_summary['total_values']/total_elapsed:.1f} values/second")
            print("  • All imports completed successfully! ✅")
            
            return combined_summary
            
        except Exception as e:
            print(f"❌ Error in comprehensive data import: {str(e)}")
            raise

    def _get_or_create_currency(self, currency_name: str) -> CurrencyEntity:
        """Get existing or create new currency entity."""
        # Try to find existing currency
        existing = None
        try:
            # Search by name or ISO code
            existing = self.currency_repository_local.get_by_name(currency_name)
        except:
            pass
        
        if existing:
            return existing
        
        # Create new currency entity
        currency_entity = CurrencyEntity(
            name=currency_name,
            iso_code=currency_name[:3] if len(currency_name) >= 3 else currency_name,
            country_id=1  # Default country for now
        )
        
        return self.currency_repository_local.add(currency_entity)

    def _get_or_create_company_share(self, ticker: str) -> CompanyShareEntity:
        """Get existing or create new company share entity."""
        # Try to find existing company share
        existing = None
        try:
            existing = self.company_share_repository_local.get_by_ticker(ticker)
        except:
            pass
        
        if existing:
            return existing
        
        # Create new company share entity
        share_entity = CompanyShareEntity(
            ticker=ticker,
            exchange_id=1,  # Default exchange
            company_id=1,   # Default company
            start_date=datetime(2000, 1, 1),
            end_date=None
        )
        
        return self.company_share_repository_local.add(share_entity)

    def _create_fx_factor(self, currency_name: str, factor_type: str):
        """Create or get FX factor."""
        factor_name = f"{currency_name}_{factor_type}"
        
        # Try to get existing factor
        existing = None
        try:
            existing = self.currency_factor_repository.get_by_name(factor_name)
        except:
            pass
            
        if existing:
            return existing
        
        # Create new factor
        return self.currency_factor_repository.add_factor(
            name=factor_name,
            group="exchange_rate",
            subgroup="historical",
            data_type="numeric",
            source="historical_csv",
            definition=f"Exchange rate for {currency_name} vs USD"
        )

    def _create_stock_factor(self, ticker: str, factor_type: str):
        """Create or get stock factor."""
        factor_name = f"{ticker}_{factor_type}"
        
        # Try to get existing factor
        existing = None
        try:
            existing = self.share_factor_repository.get_by_name(factor_name)
        except:
            pass
            
        if existing:
            return existing
        
        # Create new factor
        return self.share_factor_repository.add_factor(
            name=factor_name,
            group="price" if factor_type != "volume" else "volume",
            subgroup="historical",
            data_type="numeric",
            source="historical_csv",
            definition=f"{factor_type.title()} data for {ticker}"
        )

    
        