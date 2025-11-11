




import time
import os
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional

import pandas as pd
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager
from application.managers.project_managers.test_project_data import config
from application.services.misbuffet.data.factor_factory.factor_factory import FactorFactory
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from domain.entities.finance.financial_assets.currency import Currency as CurrencyEntity
from domain.entities.finance.financial_assets.equity import Dividend
from domain.entities.finance.financial_assets.security import MarketData

# Domain factor entities
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import FactorShare as ShareFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor.share_factor_value import ShareFactorValue as ShareFactorValueEntity

# Infrastructure repositories
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository as CurrencyRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_factor_repository import CompanyShareFactorRepository

# Infrastructure models for factor operations
from infrastructure.models.factor.finance.financial_assets.currency_factors import (
    CurrencyFactor, CurrencyFactorValue, 
)
from infrastructure.models.factor.finance.financial_assets.share_factors import (
    ShareFactor, ShareFactorValue,   
)
from infrastructure.models.factor.finance.financial_assets.company_share_factors import (
    CompanyShareFactor, CompanyShareFactorValue, 
)

# Note: Using repositories directly without mappers for this implementation

class TestProjectFactorManager(ProjectManager):
    """
    Test project data manager.
    Handles entity creation (shares, currencies) and factor computation using the FactorFactory.
    """

    def __init__(self):
        super().__init__()

        # Initialize database manager and repositories
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        self.company_share_repository_local = CompanyShareRepositoryLocal(self.database_manager.session)

        # Initialize factor repositories
        self.share_factor_repository = ShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])
        self.company_share_factor_repository = CompanyShareFactorRepository(config.CONFIG_TEST['DB_TYPE'])

        # Initialize the factor factory
        self.factor_factory = FactorFactory()
        
        # Note: Working directly with repositories for this implementation
        
        # Data paths
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
        self.fx_data_path = os.path.join(self.project_root, "data", "fx_data", "currency_exchange_rates_02-01-1995_-_02-05-2018.csv")
        self.stock_data_dir = os.path.join(self.project_root, "data", "stock_data")

    # -------------------------
    # ENTITY CREATION METHODS
    # -------------------------

    def run_complete_factor_setup(self) -> Dict[str, Any]:
        """Run the complete factor creation and population process."""
        print("🚀 Starting Complete Factor Setup Process...")
        print("=" * 60)
        total_start_time = time.time()
        
        try:
            # Step 1: Create entities
            print("\n📋 Step 1: Creating Entities")
            entities_summary = self.add_entities()
            
            # Step 2: Create factors and calculate values
            print("\n📋 Step 2: Creating Factors and Calculating Values")
            factors_summary = self.create_and_save_all_factors()
            
            total_end_time = time.time()
            total_elapsed = total_end_time - total_start_time
            
            # Final summary
            final_summary = {
                'entities': entities_summary,
                'factors': factors_summary,
                'total_processing_time': total_elapsed,
                'system_ready': True
            }
            
            print("\n" + "=" * 60)
            print("🎯 COMPLETE FACTOR SETUP SUMMARY:")
            print(f"  • Total entities created: {entities_summary['total_entities']}")
            print(f"  • Total factors created: {factors_summary['factors_created']}")
            print(f"  • Total values calculated: {factors_summary['values_calculated']}")
            print(f"  • Total processing time: {total_elapsed:.3f} seconds")
            print("  • Factor system is fully operational! 🎉")
            print("=" * 60)
            
            return final_summary
            
        except Exception as e:
            print(f"❌ Error in complete factor setup: {str(e)}")
            return {
                'entities': {'total_entities': 0},
                'factors': {'factors_created': 0,  'values_calculated': 0},
                'total_processing_time': 0,
                'system_ready': False,
                'error': str(e)
            }
    
    def add_entities(self) -> Dict[str, Any]:
        """Create base entities (shares, currencies) for testing."""
        print("🚀 Creating base entities (shares and currencies)...")
        
        # Initialize database
        self.database_manager.db.initialize_database_and_create_all_tables()
        
        # Create entities
        shares_summary = self.add_shares()
        
        total_summary = {
            'shares': shares_summary,
            'total_entities': shares_summary['count'] 
        }
        
        print(f"✅ Entity creation complete:")
        print(f"  • Shares created: {shares_summary['count']}")
        print(f"  • Total entities: {total_summary['total_entities']}")
        
        return total_summary
    
    def add_shares(self) -> Dict[str, Any]:
        """
        Create multiple CompanyShare entities from CSV data source.
        Focus on entity creation only - market data enhancement is handled via factors.
        
        Returns:
            Dict[str, Any]: Summary of created shares
        """
        tickers = ["AAPL", "MSFT", "AMZN", "GOOGL"]
        companies_data = []

        # Path to stock data directory - find project root and build absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        
        # Navigate up to find the project root (where data/ folder is located)
        while not os.path.exists(os.path.join(project_root, 'data', 'stock_data')) and project_root != os.path.dirname(project_root):
            project_root = os.path.dirname(project_root)
        
        stock_data_path = os.path.join(project_root, "data", "stock_data")
        print(f"📁 Loading stock data from: {stock_data_path}")
        
        # Verify the path exists before proceeding
        if not os.path.exists(stock_data_path):
            print(f"❌ Stock data directory not found at: {stock_data_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"File location: {current_dir}")
            print("Available directories in project root:")
            if os.path.exists(project_root):
                for item in os.listdir(project_root):
                    if os.path.isdir(os.path.join(project_root, item)):
                        print(f"  - {item}/")
        else:
            print(f"✅ Stock data directory found with {len(os.listdir(stock_data_path))} files")

        # Verify CSV data availability for entity identification
        available_tickers = []
        for ticker in tickers:
            csv_path = os.path.join(stock_data_path, f"{ticker}.csv")
            if os.path.exists(csv_path):
                available_tickers.append(ticker)
                print(f"✅ CSV data available for {ticker}")
            else:
                print(f"⚠️  CSV file not found for {ticker}: {csv_path}")

        # Create basic company entity data (CSV source identification only)
        # Check for existing entities to avoid duplicates
        new_tickers = []
        existing_tickers = []
        
        for ticker in available_tickers:
            if self.company_share_repository_local.exists_by_ticker(ticker):
                existing_tickers.append(ticker)
                print(f"    ♻️  Company share already exists: {ticker}")
            else:
                new_tickers.append(ticker)
        
        # Only create entities for new tickers
        for ticker in new_tickers:
            companies_data.append({
                'id': None,  # Will be assigned sequentially by repository
                'ticker': ticker,
                'exchange_id': 1,
                'company_id': None,  # Will be same as entity ID
                'start_date': datetime(2020, 1, 1),
                'company_name': f"{ticker} Inc." if ticker != "GOOGL" else "Alphabet Inc.",
                'sector': 'Technology'
            })

        print(f"Creating {len(companies_data)} companies in bulk operation...")
        start_time = time.time()
        
        try:
            # Initialize database if needed
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Validate and create domain entities
            domain_shares = []
            for i, data in enumerate(companies_data):
                try:
                    # Company ID will be same as share ID (assigned by repository)
                    domain_share = CompanyShareEntity(
                        id=data['id'],
                        ticker=data['ticker'],
                        exchange_id=data['exchange_id'],
                        company_id=data['id'],  # Will be set to the same as entity ID
                        start_date=data['start_date'],
                        end_date=data.get('end_date')
                    )
                    
                    # Set company name if provided
                    if 'company_name' in data:
                        domain_share.set_company_name(data['company_name'])
                    
                    # Set sector information if provided  
                    if 'sector' in data:
                        domain_share.update_sector_industry(data.get('sector'), data.get('industry'))
                    
                    domain_shares.append(domain_share)
                    
                except Exception as e:
                    print(f"Error creating domain entity {i}: {str(e)}")
                    raise
            
            # Use bulk repository operation
            created_companies = self.company_share_repository_local.add_bulk(domain_shares)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(f"✅ Successfully created {len(created_companies)} new companies in {elapsed:.3f} seconds")
            if len(created_companies) > 0:
                print(f"⚡ Performance: {len(created_companies)/elapsed:.1f} companies/second")
            
            # Return summary including both new and existing
            shares_summary = {
                'count': len(available_tickers),  # Total count including existing
                'tickers': available_tickers,
                'new_entities': len(created_companies),
                'existing_entities': len(existing_tickers),
                'processing_time': elapsed,
                'csv_data_available': len(available_tickers),
                'created_entities': len(created_companies)
            }
            
            print(f"📋 Share creation summary: {shares_summary['new_entities']} new + {shares_summary['existing_entities']} existing = {shares_summary['count']} total entities from {shares_summary['csv_data_available']} CSV sources")
            return shares_summary
            
        except Exception as e:
            print(f"❌ Error in bulk company creation: {str(e)}")
            return {
                'count': 0,
                'tickers': [],
                'processing_time': 0,
                'csv_data_available': len(available_tickers),
                'created_entities': 0,
                'error': str(e)
            }


    
   
    # -------------------------
    # FACTOR CREATION AND COMPUTATION METHODS
    # -------------------------

    def create_and_save_all_factors(self) -> Dict[str, Any]:
        """Create and save all factors and factor values for shares and currencies."""
        print("🔧 Creating and saving all factors...")
        start_time = time.time()
        
        # Create factor definitions 
        factor_summary = self.create_factor_definitions()
        
        # Calculate and save factor values from historical data
        values_summary = self.calculate_and_save_factor_values()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        total_summary = {
            'factors_created': factor_summary['total_factors'],
            'values_calculated': values_summary['total_values'],
            'processing_time': elapsed
        }
        
        print(f"\n🎯 Complete Factor System Summary:")
        print(f"  • Factors created: {total_summary['factors_created']}")
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        print(f"  • Processing time: {elapsed:.3f} seconds")
        print("  • Factor system ready! ✅")
        
        return total_summary

    def create_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions  for shares and currencies."""
        print("📋 Creating factor definitions ")
        
        shares_factors = self._create_shares_factor_definitions()
        
        return {
            'shares_factors': shares_factors['factors'],
            'total_factors': len(shares_factors['factors']) 
        }

    def calculate_and_save_factor_values(self) -> Dict[str, Any]:
        """Calculate and save factor values from historical data."""
        print("📊 Calculating and saving factor values...")
        
        shares_values = self._calculate_shares_factor_values()
        
        return {
            'shares_values': shares_values,
            'total_values': shares_values 
        }

    # -------------------------
    # INTERNAL FACTOR DEFINITION METHODS
    # -------------------------

    def _create_shares_factor_definitions(self) -> Dict[str, List]:
        """Create factor definitions  for share entities."""
        print("  📈 Creating share factor definitions...")
        
        factors = []
        
        # Price factors (OHLCV)
        price_factors = [
            {'name': 'open_price', 'group': 'price', 'subgroup': 'ohlc', 'definition': 'Opening price of the trading session'},
            {'name': 'high_price', 'group': 'price', 'subgroup': 'ohlc', 'definition': 'Highest price during the trading session'},
            {'name': 'low_price', 'group': 'price', 'subgroup': 'ohlc', 'definition': 'Lowest price during the trading session'},
            {'name': 'close_price', 'group': 'price', 'subgroup': 'ohlc', 'definition': 'Closing price of the trading session'},
            {'name': 'adj_close_price', 'group': 'price', 'subgroup': 'adjusted', 'definition': 'Dividend and split-adjusted closing price'},
            {'name': 'volume', 'group': 'volume', 'subgroup': 'trading', 'definition': 'Number of shares traded during the session'}
        ]
        
        for factor_def in price_factors:
            try:
                # Check if factor already exists
                existing_factor = self.share_factor_repository.get_by_name(factor_def['name'])
                if existing_factor:
                    factor = existing_factor
                    print(f"    ♻️  Factor already exists: {factor_def['name']} (ID: {factor.id})")
                else:
                    # Create new factor with sequential ID system
                    factor = self.share_factor_repository.add_factor(
                        name=factor_def['name'],
                        group=factor_def['group'],
                        subgroup=factor_def['subgroup'],
                        data_type='numeric',
                        source='historical_csv',
                        definition=factor_def['definition']
                    )
                    print(f"    ✅ Created share factor: {factor_def['name']} (ID: {factor.id})")
                    
                factors.append(factor)
                
                
                
            except Exception as e:
                print(f"    ❌ Error creating share factor {factor_def['name']}: {str(e)}")
        
        return {'factors': factors}

 
    def _calculate_shares_factor_values(self) -> int:
        """Calculate and save factor values for all shares, skipping existing values."""
        print("  📈 Calculating share factor values...")
        values_count = 0
        skipped_count = 0
        
        try:
            shares = self.company_share_repository_local.get_all()
            
            for share in shares:
                # Load historical data for this share
                csv_file = os.path.join(self.stock_data_dir, f"{share.ticker}.csv")
                if not os.path.exists(csv_file):
                    continue
                
                df = pd.read_csv(csv_file)
                df['Date'] = pd.to_datetime(df['Date'])
                
                # Get factors for shares
                factors = {
                    'open_price': self.share_factor_repository.get_by_name('open_price'),
                    'high_price': self.share_factor_repository.get_by_name('high_price'),
                    'low_price': self.share_factor_repository.get_by_name('low_price'),
                    'close_price': self.share_factor_repository.get_by_name('close_price'),
                    'adj_close_price': self.share_factor_repository.get_by_name('adj_close_price'),
                    'volume': self.share_factor_repository.get_by_name('volume')
                }
                
                # Get existing dates for each factor to optimize duplicate checking
                existing_dates = {}
                for factor_name, factor in factors.items():
                    if factor:
                        existing_dates[factor.id] = self.share_factor_repository.get_existing_value_dates(
                            factor.id, share.id
                        )
                
                share_new_values = 0
                share_skipped_values = 0
                
                # Save factor values, skipping existing ones
                for _, row in df.iterrows():
                    trade_date = row['Date'].date()
                    
                    # Prepare OHLCV values
                    factor_values = [
                        (factors['open_price'].id, 'Open', row['Open']),
                        (factors['high_price'].id, 'High', row['High']),
                        (factors['low_price'].id, 'Low', row['Low']),
                        (factors['close_price'].id, 'Close', row['Close']),
                        (factors['adj_close_price'].id, 'Adj Close', row['Adj Close']),
                        (factors['volume'].id, 'Volume', row['Volume'])
                    ]
                    
                    for factor_id, column_name, value in factor_values:
                        # Check if this value already exists
                        if trade_date in existing_dates.get(factor_id, set()):
                            share_skipped_values += 1
                            skipped_count += 1
                            continue
                        
                        # Add new factor value
                        try:
                            self.share_factor_repository.add_factor_value(
                                factor_id=factor_id,
                                entity_id=share.id,
                                date=trade_date,
                                value=Decimal(str(value))
                            )
                            share_new_values += 1
                            values_count += 1
                            
                            # Update our local cache to avoid future duplicates
                            if factor_id not in existing_dates:
                                existing_dates[factor_id] = set()
                            existing_dates[factor_id].add(trade_date)
                            
                        except Exception as e:
                            print(f"    ⚠️  Error adding {column_name} value for {share.ticker} on {trade_date}: {str(e)}")
                
                # Report results for this share
                if share_new_values > 0 or share_skipped_values > 0:
                    status_msg = f"    ✅ Processed {share.ticker}: {share_new_values} new values"
                    if share_skipped_values > 0:
                        status_msg += f", ♻️  {share_skipped_values} existing values skipped"
                    print(status_msg)
                else:
                    print(f"    ♻️  {share.ticker}: All values already exist")
                
        except Exception as e:
            print(f"    ❌ Error calculating share values: {str(e)}")
        
        if skipped_count > 0:
            print(f"  📊 Summary: {values_count} new values added, {skipped_count} existing values skipped")
        
        return values_count


    # -------------------------
    # FACTOR CRUD METHODS
    # -------------------------

    def add_factor(self, name: str, group: str, subgroup: str, data_type: str, source: str, definition: str, repository=None):
        """
        Add a new factor using the specified repository.
        
        Args:
            name: Factor name
            group: Factor group
            subgroup: Factor subgroup
            data_type: Data type (e.g., 'numeric', 'string')
            source: Data source
            definition: Factor definition/description
            repository: Repository to use (defaults to share_factor_repository)
        
        Returns:
            Created factor entity or None if failed
        """
        if repository is None:
            repository = self.share_factor_repository
        
        try:
            return repository.add_factor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type=data_type,
                source=source,
                definition=definition
            )
        except Exception as e:
            print(f"❌ Error adding factor {name}: {str(e)}")
            return None

    def add_factor_value(self, factor_id: int, entity_id: int, date: date, value: Decimal, repository=None):
        """
        Add a new factor value using the specified repository.
        
        Args:
            factor_id: ID of the factor
            entity_id: ID of the entity
            date: Date of the value
            value: Factor value
            repository: Repository to use (defaults to share_factor_repository)
        
        Returns:
            Created factor value entity or None if failed
        """
        if repository is None:
            repository = self.share_factor_repository
        
        try:
            return repository.add_factor_value(
                factor_id=factor_id,
                entity_id=entity_id,
                date=date,
                value=value
            )
        except Exception as e:
            print(f"❌ Error adding factor value for factor {factor_id}: {str(e)}")
            return None

   
    # -------------------------
    # UTILITY METHODS
    # -------------------------

    def _get_iso_code(self, currency_name: str) -> str:
        """Get ISO code for currency name."""
        iso_mapping = {
            'Algerian Dinar': 'DZD',
            'Australian Dollar': 'AUD',
            'Bahrain Dinar': 'BHD',
            'Bolivar Fuerte': 'VEF',
            'Botswana Pula': 'BWP',
            'Brazilian Real': 'BRL',
            'Brunei Dollar': 'BND',
            'Canadian Dollar': 'CAD',
            'Chilean Peso': 'CLP',
            'Chinese Yuan': 'CNY',
            'Colombian Peso': 'COP',
            'Czech Koruna': 'CZK',
            'Danish Krone': 'DKK',
            'Euro': 'EUR',
            'Hungarian Forint': 'HUF',
            'Icelandic Krona': 'ISK',
            'Indian Rupee': 'INR',
            'Indonesian Rupiah': 'IDR',
            'Iranian Rial': 'IRR',
            'Israeli New Sheqel': 'ILS',
            'Japanese Yen': 'JPY',
            'Kazakhstani Tenge': 'KZT',
            'Korean Won': 'KRW',
            'Kuwaiti Dinar': 'KWD',
            'Libyan Dinar': 'LYD',
            'Malaysian Ringgit': 'MYR',
            'Mauritian Rupee': 'MUR',
            'Mexican Peso': 'MXN',
            'Nepalese Rupee': 'NPR',
            'New Zealand Dollar': 'NZD',
            'Norwegian Krone': 'NOK',
            'Nuevo Sol': 'PEN',
            'Pakistani Rupee': 'PKR',
            'Peso Uruguayo': 'UYU',
            'Philippine Peso': 'PHP',
            'Polish Zloty': 'PLN',
            'Qatar Riyal': 'QAR',
            'Rial Omani': 'OMR',
            'Russian Ruble': 'RUB',
            'Saudi Arabian Riyal': 'SAR',
            'Singapore Dollar': 'SGD',
            'South African Rand': 'ZAR',
            'Sri Lanka Rupee': 'LKR',
            'Swedish Krona': 'SEK',
            'Swiss Franc': 'CHF',
            'Thai Baht': 'THB',
            'Trinidad And Tobago Dollar': 'TTD',
            'Tunisian Dinar': 'TND',
            'U.A.E. Dirham': 'AED',
            'U.K. Pound Sterling': 'GBP',
            'U.S. Dollar': 'USD'
        }
        return iso_mapping.get(currency_name, currency_name[:3].upper())

    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the factor system."""
        try:
            shares = self.company_share_repository_local.get_all()
            
            share_factors = self.share_factor_repository.list_all()
            
            return {
                'entities': {
                    'shares': len(shares)
                },
                'factors': {
                    'share_factors': len(share_factors),
                    'total_factors': len(share_factors) 
                },
                'status': 'ready'
            }
        except Exception as e:
            return {
                'entities': {'shares': 0, 'currencies': 0},
                'factors': {'share_factors': 0, 'currency_factors': 0, 'total_factors': 0},
                'status': f'error: {str(e)}'
            }

    def _get_market_data(self, entity):
        """
        Placeholder method to fetch a market data series for an entity.
        Replace this with real data retrieval logic.
        """
        print(f"Fetching price data for {entity.name}")
        # Example: use MarketData or repo to get a pandas.Series of prices
        return MarketData(entity).get_price_series()
    
    