




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
from domain.entities.finance.financial_assets.equity import FundamentalData, Dividend
from domain.entities.finance.financial_assets.security import MarketData

# Domain factor entities
from domain.entities.factor.finance.financial_assets.share_factor import FactorShare as ShareFactorEntity
from domain.entities.factor.finance.financial_assets.share_factor_value import ShareFactorValue as ShareFactorValueEntity
from domain.entities.factor.finance.financial_assets.share_factor_rule import ShareFactorRule as ShareFactorRuleEntity

# Infrastructure repositories
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository as CurrencyRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.currency_factor_repository import CurrencyFactorRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from infrastructure.repositories.local_repo.factor.finance.financial_assets.company_share_factor_repository import CompanyShareFactorRepository

# Infrastructure models for factor operations
from infrastructure.models.factor.finance.financial_assets.currency_factors import (
    CurrencyFactor, CurrencyFactorValue, CurrencyFactorRule
)
from infrastructure.models.factor.finance.financial_assets.share_factors import (
    ShareFactor, ShareFactorValue, ShareFactorRule  
)
from infrastructure.models.factor.finance.financial_assets.company_share_factors import (
    CompanyShareFactor, CompanyShareFactorValue, CompanyShareFactorRule
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
            print(f"  • Total rules created: {factors_summary['rules_created']}")
            print(f"  • Total values calculated: {factors_summary['values_calculated']}")
            print(f"  • Total processing time: {total_elapsed:.3f} seconds")
            print("  • Factor system is fully operational! 🎉")
            print("=" * 60)
            
            return final_summary
            
        except Exception as e:
            print(f"❌ Error in complete factor setup: {str(e)}")
            return {
                'entities': {'total_entities': 0},
                'factors': {'factors_created': 0, 'rules_created': 0, 'values_calculated': 0},
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
    
    def add_shares(self):
        """
        Create multiple CompanyShare entities in a single atomic transaction.
        
        Args:
            companies_data: List of dicts containing company share data
            
        Returns:
            List[CompanyShareEntity]: Successfully created company share entities
        """
        """
        Create the 5 tech companies (AAPL, MSFT, AMZN, GOOGL) 
        and populate them with market and fundamental data loaded from CSV files.
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

        # Load actual stock data from CSV files
        stock_data_cache = {}
        for ticker in tickers:
            csv_path = os.path.join(stock_data_path, f"{ticker}.csv")
            try:
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.sort_values('Date')
                    stock_data_cache[ticker] = df
                    print(f"✅ Loaded {len(df)} data points for {ticker} from {df['Date'].min().date()} to {df['Date'].max().date()}")
                else:
                    print(f"⚠️  CSV file not found for {ticker}: {csv_path}")
                    stock_data_cache[ticker] = None
            except Exception as e:
                print(f"❌ Error loading data for {ticker}: {str(e)}")
                stock_data_cache[ticker] = None

        # Sample starting IDs and exchange/company IDs
        start_id = 1
        for i, ticker in enumerate(tickers, start=start_id):
            companies_data.append({
                'id': i,
                'ticker': ticker,
                'exchange_id': 1,
                'company_id': i,
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
            created_companies = self.company_share_repository_local.add_bulk(domain_shares)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print(f"✅ Successfully created {len(created_companies)} companies in {elapsed:.3f} seconds")
            print(f"⚡ Performance: {len(created_companies)/elapsed:.1f} companies/second")
            
            
            
        except Exception as e:
            print(f"❌ Error in bulk company creation: {str(e)}")
            raise

        if not created_companies:
            print("❌ No companies were created")
            return []

        # Step 2: Save CSV data to database and enhance with market and fundamental data
        for i, company in enumerate(created_companies):
            ticker = company.ticker
            try:
                # Get stock data for this ticker
                stock_df = stock_data_cache.get(ticker)
                
                if stock_df is not None and not stock_df.empty:
                    # Save CSV data to database for backtesting engine to use
                    table_name = f"stock_price_data_{ticker.lower()}"
                    print(f"💾 Saving {len(stock_df)} price records for {ticker} to database table '{table_name}'")
                    self.database_manager.dataframe_replace_table(stock_df, table_name)
                    
                    # Use the most recent data point for current market data
                    latest_data = stock_df.iloc[-1]
                    latest_price = Decimal(str(latest_data['Close']))
                    latest_volume = Decimal(str(latest_data['Volume']))
                    latest_date = latest_data['Date']
                    
                    # Historical data statistics for fundamental analysis
                    recent_data = stock_df.tail(252)  # Last year of data
                    avg_volume = Decimal(str(recent_data['Volume'].mean()))
                    price_52w_high = Decimal(str(recent_data['High'].max()))
                    price_52w_low = Decimal(str(recent_data['Low'].min()))
                    
                    print(f"📈 Using real data for {ticker}: Latest Close=${latest_price:.2f}, Volume={latest_volume:,}")
                else:
                    # Fallback to mock data if CSV not available
                    latest_price = Decimal(str(100 + i * 50))
                    latest_volume = Decimal(str(1_000_000 + i * 100_000))
                    latest_date = datetime.now()
                    avg_volume = latest_volume
                    price_52w_high = latest_price * Decimal('1.2')
                    price_52w_low = latest_price * Decimal('0.8')
                    print(f"⚠️  Using fallback data for {ticker}")

                # Market data (using real prices and volumes)
                market_data = MarketData(
                    timestamp=latest_date if isinstance(latest_date, datetime) else datetime.now(),
                    price=latest_price,
                    volume=latest_volume
                )
                company.update_market_data(market_data)

                # Fundamental data (mix of real-derived and estimated values)
                # Calculate approximate market cap based on real price
                estimated_shares_outstanding = Decimal(str(1_000_000_000 + i * 100_000_000))  # Estimate
                market_cap = latest_price * estimated_shares_outstanding
                
                # Estimate P/E ratio based on sector averages
                pe_ratios = {"AAPL": 25.0, "MSFT": 28.0, "AMZN": 35.0, "GOOGL": 22.0}
                pe_ratio = Decimal(str(pe_ratios.get(ticker, 25.0)))
                
                fundamentals = FundamentalData(
                    pe_ratio=pe_ratio,
                    dividend_yield=Decimal(str(1.0 + i * 0.3)),  # Estimated dividend yields
                    market_cap=market_cap,
                    shares_outstanding=estimated_shares_outstanding,
                    sector='Technology',
                    industry='Software' if ticker not in ["AMZN", "GOOGL"] else ('E-commerce' if ticker == "AMZN" else 'Internet Services')
                )
                company.update_company_fundamentals(fundamentals)

                # Sample dividend (estimated based on dividend yield)
                dividend_amount = (fundamentals.dividend_yield / 100) * latest_price / 4  # Quarterly dividend
                dividend = Dividend(
                    amount=dividend_amount,
                    ex_date=datetime(2024, 3, 15),
                    pay_date=datetime(2024, 3, 30)
                )
                company.add_dividend(dividend)

                # Print metrics for confirmation
                metrics = company.get_company_metrics()
                print(f"📊 {company.ticker}: Price=${metrics['current_price']}, "
                    f"P/E={metrics['pe_ratio']}, Market Cap=${market_cap/1_000_000_000:.1f}B, "
                    f"Div Yield={metrics['dividend_yield']}%")

            except Exception as e:
                print(f"❌ Error enhancing company {company.ticker}: {str(e)}")
                continue


    
   
    # -------------------------
    # FACTOR CREATION AND COMPUTATION METHODS
    # -------------------------

    def create_and_save_all_factors(self) -> Dict[str, Any]:
        """Create and save all factors and factor values for shares and currencies."""
        print("🔧 Creating and saving all factors...")
        start_time = time.time()
        
        # Create factor definitions and rules
        factor_summary = self.create_factor_definitions()
        
        # Calculate and save factor values from historical data
        values_summary = self.calculate_and_save_factor_values()
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        total_summary = {
            'factors_created': factor_summary['total_factors'],
            'rules_created': factor_summary['total_rules'],
            'values_calculated': values_summary['total_values'],
            'processing_time': elapsed
        }
        
        print(f"\n🎯 Complete Factor System Summary:")
        print(f"  • Factors created: {total_summary['factors_created']}")
        print(f"  • Rules created: {total_summary['total_rules']}")
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        print(f"  • Processing time: {elapsed:.3f} seconds")
        print("  • Factor system ready! ✅")
        
        return total_summary

    def create_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions and rules for shares and currencies."""
        print("📋 Creating factor definitions and rules...")
        
        shares_factors = self._create_shares_factor_definitions()
        
        return {
            'shares_factors': shares_factors['factors'],
            'shares_rules': shares_factors['rules'],
            'total_factors': len(shares_factors['factors']) ,
            'total_rules': len(shares_factors['rules']) 
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
        """Create factor definitions and rules for share entities."""
        print("  📈 Creating share factor definitions...")
        
        factors = []
        rules = []
        
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
                factor = self.share_factor_repository.add_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type='numeric',
                    source='historical_csv',
                    definition=factor_def['definition']
                )
                factors.append(factor)
                
                # Add basic validation rule
                rule = self.share_factor_repository.add_factor_rule(
                    factor_id=factor.id,
                    condition=f"{factor_def['name']} > 0" if 'price' in factor_def['name'] else f"{factor_def['name']} >= 0",
                    rule_type='validation',
                    method_ref='validate_positive_value'
                )
                rules.append(rule)
                
                print(f"    ✅ Created share factor: {factor_def['name']}")
                
            except Exception as e:
                print(f"    ❌ Error creating share factor {factor_def['name']}: {str(e)}")
        
        return {'factors': factors, 'rules': rules}

 
    def _calculate_shares_factor_values(self) -> int:
        """Calculate and save factor values for all shares."""
        print("  📈 Calculating share factor values...")
        values_count = 0
        
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
                open_factor = self.share_factor_repository.get_by_name('open_price')
                high_factor = self.share_factor_repository.get_by_name('high_price')
                low_factor = self.share_factor_repository.get_by_name('low_price')
                close_factor = self.share_factor_repository.get_by_name('close_price')
                adj_close_factor = self.share_factor_repository.get_by_name('adj_close_price')
                volume_factor = self.share_factor_repository.get_by_name('volume')
                
                # Save factor values
                for _, row in df.iterrows():
                    trade_date = row['Date'].date()
                    
                    # Save OHLCV values
                    factor_values = [
                        (open_factor.id, row['Open']),
                        (high_factor.id, row['High']),
                        (low_factor.id, row['Low']),
                        (close_factor.id, row['Close']),
                        (adj_close_factor.id, row['Adj Close']),
                        (volume_factor.id, row['Volume'])
                    ]
                    
                    for factor_id, value in factor_values:
                        self.share_factor_repository.add_factor_value(
                            factor_id=factor_id,
                            entity_id=share.id,
                            date=trade_date,
                            value=Decimal(str(value))
                        )
                        values_count += 1
                
                print(f"    ✅ Processed {share.ticker}: {len(df)} days of data")
                
        except Exception as e:
            print(f"    ❌ Error calculating share values: {str(e)}")
        
        return values_count


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
    
    