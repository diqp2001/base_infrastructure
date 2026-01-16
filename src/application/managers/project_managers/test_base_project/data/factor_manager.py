"""
Factor management component combining factor creation capabilities
with spatiotemporal feature storage and retrieval.

Integrates the factor system from test_project_factor_creation with 
the advanced feature engineering from spatiotemporal models.
"""

import os
import time
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path



from src.application.services.database_service.database_service import DatabaseService
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare as CompanyShareEntity
from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
# ShareFactorValueMapper removed - using FactorValueMapper instead
from src.infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper

from .feature_engineer import SpatiotemporalFeatureEngineer
from ..config import DEFAULT_CONFIG


class FactorEnginedDataManager:
    """
    Manages factor creation, storage, and retrieval for spatiotemporal models.
    
    Combines the entity/factor management from test_project_factor_creation
    with the advanced feature engineering from spatiotemporal_momentum_manager.
    """
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.config = DEFAULT_CONFIG
        
        # Initialize services with clear separation of responsibilities
        self.factor_creation_service = FactorCreationService(self.database_service, self.config['DATABASE']['DB_TYPE'])  # For factor definition creation/storage
        self.factor_calculation_service = FactorCalculationService(self.database_service, self.config['DATABASE']['DB_TYPE'])  # For factor value calculation/storage
        self.factor_data_service = FactorDataService(self.database_service, self.config['DATABASE']['DB_TYPE'])  # For all data operations
        self.entity_existence_service = EntityExistenceService(self.database_service)
        # Initialize feature engineer
        self.feature_engineer = SpatiotemporalFeatureEngineer(self.database_service)
        
        # Data paths - find project root by looking for data/stock_data directory
        current_path = Path(__file__).resolve()
        self.project_root = current_path
        
        # Walk up the directory tree to find the project root
        while not (self.project_root / 'data' / 'stock_data').exists() and self.project_root.parent != self.project_root:
            self.project_root = self.project_root.parent
            
        self.stock_data_path = self.project_root / "data" / "stock_data"
    

    def populate_price_factors(self, 
                                tickers: Optional[List[str]] = None,
                                overwrite: bool = False) -> Dict[str, Any]:
        """
        Create and populate price factors.
        
        Args:
            tickers: List of tickers to process (defaults to config universe)
            overwrite: Whether to overwrite existing factor values
            
        Returns:
            Summary of factor creation and population
        """
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        print(f"🚀 Populating price factors for {len(tickers)} tickers...")
        
        
        # Ensure entities exist using service
        entities_summary = self.entity_existence_service.ensure_entities_exist(tickers)
        
        # Create price factor definitions
        price_factors_summary = self._create_price_factor_definitions()
        
        # Calculate and store momentum factor values
        values_summary = self._calculate_price_factor_values(tickers, overwrite)
        
        total_summary = {
            'factors_created': price_factors_summary['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
        
        print(f"✅ Price factor population complete:")
        print(f"  • Factors created: {total_summary['factors_created']}")  
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        
        return total_summary
    
    def populate_momentum_factors(self, 
                                tickers: Optional[List[str]] = None,
                                overwrite: bool = False) -> Dict[str, Any]:
        """
        Create and populate spatiotemporal momentum factors.
        
        Args:
            tickers: List of tickers to process (defaults to config universe)
            overwrite: Whether to overwrite existing factor values
            
        Returns:
            Summary of factor creation and population
        """
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        print(f"🚀 Populating momentum factors for {len(tickers)} tickers...")
        
        
        # Ensure entities exist using service
        entities_summary = self.entity_existence_service.ensure_entities_exist(tickers)
        
        # Create momentum factor definitions
        momentum_factors_summary = self._create_momentum_factor_definitions()
        
        # Calculate and store momentum factor values
        values_summary = self._calculate_momentum_factor_values(tickers, overwrite)
        
        total_summary = {
            'factors_created': momentum_factors_summary['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
        
        print(f"✅ Momentum factor population complete:")
        print(f"  • Factors created: {total_summary['factors_created']}")  
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        
        return total_summary
    
    def populate_technical_indicators(self,
                                     tickers: Optional[List[str]] = None,
                                     overwrite: bool = False) -> Dict[str, Any]:
        """
        Calculate and store technical indicator factors.
        
        Args:
            tickers: List of tickers to process
            overwrite: Whether to overwrite existing values
            
        Returns:
            Summary of technical indicator calculation
        """
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        print(f"📊 Calculating technical indicators for {len(tickers)} tickers...")
        
        # Ensure entities exist using service
        entities_summary = self.entity_existence_service.ensure_entities_exist(tickers)
        
        # Create technical factor definitions
        technical_factors_summary = self._create_technical_factor_definitions()
        
        # Calculate and store values using the domain factors
        values_summary = self._calculate_technical_factor_values(tickers, overwrite)
        
        return {
            'factors_created': technical_factors_summary['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
    
    def store_engineered_factors(self,
                               data: pd.DataFrame,
                               ticker: str,
                               factor_group: str = 'engineered',
                               overwrite: bool = False) -> Dict[str, Any]:
        """
        Store engineered features as factors in the database.
        
        Args:
            data: DataFrame with engineered features
            ticker: Stock ticker
            factor_group: Group name for the factors
            overwrite: Whether to overwrite existing values
            
        Returns:
            Summary of factor storage
        """
        print(f"💾 Storing engineered factors for {ticker}...")
        
        # Get the company share entity using service
        share = self.factor_data_service.get_company_share_by_ticker(ticker)
        if not share:
            raise ValueError(f"Company share not found for ticker: {ticker}")
        
        stored_factors = 0
        stored_values = 0
        
        # Store each column as a factor
        for column in data.columns:
            if column in ['Date'] or data[column].dtype == 'object':
                continue
                
            try:
                # Create or get factor using service
                factor = self.factor_data_service.create_or_get_factor(
                    name=column,
                    group=factor_group,
                    subgroup="general",
                    data_type="int",
                    source="excel",
                    definition=f"Technical indicator: {column}"
                )
                
                if factor:
                    stored_factors += 1
                    
                    # Store values
                    values_stored = self._store_factor_values(
                        factor, share, data, column, overwrite
                    )
                    stored_values += values_stored
                    
            except Exception as e:
                print(f"  ⚠️  Error storing factor {column}: {str(e)}")
        
        return {
            'factors_stored': stored_factors,
            'values_stored': stored_values,
            'ticker': ticker,
            'success': True
        }
    
    def get_factor_data_for_training(self,
                                   tickers: List[str],
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   factor_groups: Optional[List[str]] = None,
                                   lookback_days: Optional[int] = None) -> pd.DataFrame:
        """
        Retrieve factor data formatted for model training.
        
        Args:
            tickers: List of tickers to retrieve
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            factor_groups: List of factor groups to include
            lookback_days: Number of days to look back from end_date (overrides start_date if provided)
            
        Returns:
            DataFrame ready for model training
        """
        print(f"📊 Retrieving factor data for {len(tickers)} tickers...")
        
        # Handle lookback_days parameter by calculating start_date
        if lookback_days is not None and end_date is not None:
            # Parse end_date and calculate start_date
            if isinstance(end_date, str):
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            elif isinstance(end_date, datetime):
                end_dt = end_date
            else:
                end_dt = datetime.now()
            
            start_dt = end_dt - timedelta(days=lookback_days)
            start_date = start_dt.strftime('%Y-%m-%d')
            print(f"  📅 Using lookback_days={lookback_days}: {start_date} to {end_date}")
        
        if factor_groups is None:
            factor_groups = ['price', 'momentum', 'technical', 'engineered']
        
        all_data = {}
        
        for ticker in tickers:
            ticker_data = self._get_ticker_factor_data(
                ticker, start_date, end_date, factor_groups
            )
            if ticker_data is not None and not ticker_data.empty:
                all_data[ticker] = ticker_data
        
        if not all_data:
            print(f"  ⚠️  No factor data retrieved for any ticker")
            # Return empty DataFrame instead of raising exception
            return pd.DataFrame()
        
        # Combine into format expected by spatiotemporal models
        return self._format_for_model_training(all_data)
    
    def _ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Ensure all required entities exist in the database.
        
        DEPRECATED: Use EntityExistenceService.ensure_entities_exist() instead.
        This method is kept for backward compatibility but delegates to the service.
        """
        return self.entity_existence_service.ensure_entities_exist(tickers)
    

    def _create_price_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions for momentum features."""
        print("  📈 Creating Price factor definitions...")
        
        factors_created = 0
        
        # Price factors from config
        price_factors = self.config['FACTORS']['PRICE_FACTORS']
        
        for factor_def in price_factors:
            try:
                factor = self.factor_data_service.create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="int",
                    source="excel",
                    definition=f" price feature: {factor_def['name']}"
                )
                
                if factor:
                    factors_created += 1
                    
                    
                        
            except Exception as e:
                print(f"    ❌ Error creating price factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created
        }
    def _create_momentum_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions for momentum features."""
        print("  📈 Creating momentum factor definitions...")
        
        factors_created = 0
        
        # Momentum factors from config
        momentum_factors = self.config['FACTORS']['MOMENTUM_FACTORS']
        
        for factor_def in momentum_factors:
            try:
                factor = self.factor_data_service.create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{factor_def['period']}-day momentum return factor"
                )
                
                if factor:
                    factors_created += 1
                        
            except Exception as e:
                print(f"    ❌ Error creating momentum factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created
        }
    
    def _create_technical_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions for technical features."""
        print("  🔧 Creating technical factor definitions...")
        
        factors_created = 0
        
        # Technical factors from config
        technical_factors = self.config['FACTORS']['TECHNICAL_FACTORS']
        
        for factor_def in technical_factors:
            try:
                factor = self.factor_data_service.create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"Technical indicator: {factor_def['name']}"
                )
                
                if factor:
                    factors_created += 1
                        
            except Exception as e:
                print(f"    ❌ Error creating technical factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created
        }
    
    def _calculate_price_factor_values(self, tickers: List[str], overwrite: bool) -> Dict[str, Any]:
        """Calculate and store Price factor values."""
        print("  📊 Calculating Price factor values...")
        
        total_values = 0
        
        for ticker in tickers:
            # Load historical data
            csv_file = self.stock_data_path / f"{ticker}.csv"
            if not csv_file.exists():
                continue
                
            try:
                # Load and process data
                df = pd.read_csv(csv_file)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                
                
                
                # Store the momentum features as factors
                values_stored = self._store_price_features(
                    df, ticker, overwrite
                )
                total_values += values_stored
                
                print(f"    ✅ Processed {ticker}: {values_stored} price values")
                
            except Exception as e:
                print(f"    ❌ Error processing price for {ticker}: {str(e)}")
        
        return {'total_values': total_values}
    
    def _calculate_momentum_factor_values(self, tickers: List[str], overwrite: bool) -> Dict[str, Any]:
        """Calculate and store momentum factor values."""
        print("📊 Calculating momentum factor values...")
        total_values = 0

        # Get momentum factors from config
        momentum_factors = self.config['FACTORS']['MOMENTUM_FACTORS']
        
        for factor_def in momentum_factors:
            for ticker in tickers:
                try:
                    company = self.factor_data_service.get_company_share_by_ticker(ticker)
                    if not company:
                        continue

                    # Get repository factor for momentum storage
                    repository_factor = self.factor_data_service.get_factor_by_name(factor_def['name'])
                    
                    if repository_factor:
                        # Create domain factor for calculation with period as timedelta
                        momentum_factor = ShareMomentumFactor(
                            name=factor_def['name'],
                            period=timedelta(days=factor_def['period']),  # Convert to timedelta for date-aware calculations
                            group=factor_def['group'],
                            subgroup=factor_def['subgroup'],
                            data_type="numeric",
                            source="internal",
                            definition=f"{factor_def['period']}-day momentum return factor"
                        )
                        momentum_factor.factor_id = repository_factor.id
                        
                        # Use factor calculation service
                        momentum_results = self.factor_calculation_service.calculate_and_store_momentum(
                            factor=momentum_factor,
                            entity_id=company.id,
                            ticker=ticker,
                            overwrite=overwrite
                        )
                        values_stored = momentum_results.get('stored_values', 0) if momentum_results else 0

                        total_values += values_stored
                        print(f"✅ {ticker}: stored {values_stored} {factor_def['name']} values")

                except Exception as e:
                    print(f"❌ Error processing {ticker} for {factor_def['name']}: {e}")

        return {"total_values": total_values}

    
    def _calculate_technical_factor_values(self, tickers: List[str], overwrite: bool) -> Dict[str, Any]:
        """Calculate and store technical indicator values."""
        print("📊 Calculating technical indicator values...")
        total_values = 0

        # Get technical factors from config
        technical_factors = self.config['FACTORS']['TECHNICAL_FACTORS']
        
        for factor_def in technical_factors:
            for ticker in tickers:
                try:
                    company = self.factor_data_service.get_company_share_by_ticker(ticker)
                    if not company:
                        continue
                    
                    # Get repository factor for technical storage
                    repository_factor = self.factor_data_service.get_factor_by_name(factor_def['name'])
                    
                    if repository_factor:
                        # Create domain factor for calculation
                        technical_factor = ShareTechnicalFactor(
                            name=factor_def['name'],
                            indicator_type="oscillator",  # Default type
                            period=20,  # Default period
                            group=factor_def['group'],
                            subgroup=factor_def['subgroup'],
                            data_type="numeric",
                            source="internal",
                            definition=f"Technical indicator: {factor_def['name']}"
                        )
                        technical_factor.factor_id = repository_factor.id
                        
                        # Use factor calculation service
                        technical_results = self.factor_calculation_service.calculate_and_store_technical(
                            factor=technical_factor,
                            entity_id=company.id,
                            ticker=ticker,
                            overwrite=overwrite
                        )
                        values_stored = len(technical_results) if technical_results else 0

                        total_values += values_stored
                        print(f"✅ {ticker}: stored {values_stored} {factor_def['name']} values")

                except Exception as e:
                    print(f"❌ Error processing {ticker} for {factor_def['name']}: {e}")

        return {"total_values": total_values}
    
    def _store_momentum_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store momentum features as factor values."""
        share = self.factor_data_service.get_company_share_by_ticker(ticker)
        if not share:
            return 0
        
        values_stored = 0
        momentum_columns = [col for col in data.columns if 'norm_' in col and 'return' in col]
        
        for column in momentum_columns:
            factor = self.factor_data_service.get_factor_by_name(column)
            if factor:
                values_stored += self.factor_data_service.store_factor_values(
                    factor, share, data, column, overwrite
                )

        return values_stored
    
    def _store_price_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store price features as factor values."""
        share = self.factor_data_service.get_company_share_by_ticker(ticker)
        if not share:
            return 0
        
        values_stored = 0
        price_columns = self.config['FACTORS']['PRICE_FACTORS']
        
        # Create mapping between factor names and actual CSV column names
        factor_to_column_mapping = {
            'Open': 'Open',
            'High': 'High', 
            'Low': 'Low',
            'Close': 'Close',
            'Adj Close': 'Adj Close',
            'Volume': 'Volume'
        }
        
        for column in price_columns:
            factor = self.factor_data_service.get_factor_by_name(column['name'])
            if factor:
                # Map factor name to actual CSV column name
                csv_column_name = factor_to_column_mapping.get(column['name'], column['name'])
                if csv_column_name in data.columns:
                    values_stored += self.factor_data_service.store_factor_values(
                        factor, share, data, csv_column_name, overwrite
                    )
                else:
                    print(f"      ⚠️  Column '{csv_column_name}' not found for factor '{column['name']}'")
        
        return values_stored
    
    def _store_technical_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store technical features as factor values."""
        share = self.factor_data_service.get_company_share_by_ticker(ticker)
        if not share:
            return 0
        
        values_stored = 0
        technical_columns = ['rsi_14', 'bollinger_upper', 'bollinger_lower', 'stoch_k', 'stoch_d']
        
        for column in technical_columns:
            if column in data.columns:
                factor = self.factor_data_service.get_factor_by_name(column)
                if factor:
                    values_stored += self.factor_data_service.store_factor_values(
                        factor, share, data, column, overwrite
                    )
        
        return values_stored
    
    
    
    
    
    
    def _get_ticker_factor_data(self, ticker: str, start_date: Optional[str], 
                              end_date: Optional[str], factor_groups: List[str]) -> Optional[pd.DataFrame]:
        """Get factor data for a specific ticker."""
        # Use FactorDataService for all data operations
        return self.factor_data_service.get_ticker_factor_data(
            ticker, start_date, end_date, factor_groups
        )
    
    def _format_for_model_training(self, data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Format factor data for spatiotemporal model training."""
        # Create unified DataFrame with ticker prefixes
        all_data = []
        
        for ticker, df in data_dict.items():
            df_copy = df.copy()
            df_copy.columns = [f"{ticker}_{col}" for col in df_copy.columns]
            all_data.append(df_copy)
        
        # Combine and clean
        combined_df = pd.concat(all_data, axis=1)
        combined_df = combined_df.sort_index()
        combined_df = combined_df.ffill().bfill()
        
        return combined_df
    
    def populate_volatility_factors(self, 
                                 tickers: Optional[List[str]] = None,
                                 overwrite: bool = False) -> Dict[str, Any]:
        """
        Create and populate volatility factors following momentum factor pattern.
        
        Args:
            tickers: List of tickers to process (defaults to config universe)
            overwrite: Whether to overwrite existing factor values
            
        Returns:
            Summary of factor creation and population
        """
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        print(f"🔀 Populating volatility factors for {len(tickers)} tickers...")
        
        # Create volatility factor definitions
        volatility_factors_ = self._create_volatility_factor_definitions()
        
        # Calculate and store volatility factor values
        values_summary = self._calculate_volatility_factor_values(tickers, overwrite, volatility_factors_['factors_created_list'])
        
        total_summary = {
            'factors_created': volatility_factors_['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
        
        print(f"✅ Volatility factor population complete:")
        print(f"  • Factors created: {total_summary['factors_created']}")  
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        
        return total_summary
    
    def populate_target_factors(self, 
                             tickers: Optional[List[str]] = None,
                             overwrite: bool = False) -> Dict[str, Any]:
        """
        Create and populate target variable factors following momentum factor pattern.
        
        Args:
            tickers: List of tickers to process (defaults to config universe)
            overwrite: Whether to overwrite existing factor values
            
        Returns:
            Summary of factor creation and population
        """
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        print(f"🎯 Populating target factors for {len(tickers)} tickers...")
        
        # Create target factor definitions
        target_factors_ = self._create_target_factor_definitions()
        
        # Calculate and store target factor values
        values_summary = self._calculate_target_factor_values(tickers, overwrite, target_factors_['factors_created_list'])
        
        total_summary = {
            'factors_created': target_factors_['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
        
        print(f"✅ Target factor population complete:")
        print(f"  • Factors created: {total_summary['factors_created']}")  
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        
        return total_summary
    
    def _create_volatility_factor_definitions(self) -> Dict[str, Any]:
        """Create volatility factor domain entities and their repository representations."""
        print("  📊 Creating volatility factor definitions...")
        
        factors_created = 0
        volatility_domain_factors = []
        
        # Define volatility factors
        volatility_configs = [
            {'name': 'daily_vol', 'volatility_type': 'daily_vol', 'period': 21, 'group': 'volatility', 'subgroup': 'realized'},
            {'name': 'monthly_vol', 'volatility_type': 'monthly_vol', 'period': 63, 'group': 'volatility', 'subgroup': 'realized'},
            {'name': 'vol_of_vol', 'volatility_type': 'vol_of_vol', 'period': 21, 'group': 'volatility', 'subgroup': 'derivative'},
            {'name': 'realized_vol', 'volatility_type': 'realized_vol', 'period': 21, 'group': 'volatility', 'subgroup': 'realized'}
        ]
        
        for vol_config in volatility_configs:
            try:
                
                # Create domain volatility factor entity
                volatility_factor = ShareVolatilityFactor(
                    name=vol_config['name'],
                    volatility_type=vol_config['volatility_type'],
                    period=vol_config['period'],
                    group=vol_config['group'],
                    subgroup=vol_config['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{vol_config['volatility_type']} volatility factor (period: {vol_config['period']})"
                )
                
                # Create or get corresponding repository factor
                repo_factor = self.factor_data_service.create_or_get_factor(
                    name=vol_config['name'],
                    group=vol_config['group'],
                    subgroup=vol_config['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=volatility_factor.definition
                )
                
                # Link the domain entity with the repository factor
                volatility_factor.factor_id = repo_factor.id
                volatility_domain_factors.append(volatility_factor)
                factors_created += 1
                
                print(f"    ✅ Created volatility factor: {vol_config['name']} (ID: {repo_factor.id})")
                
            except Exception as e:
                print(f"    ❌ Error creating volatility factor {vol_config['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created,
            'factors_created_list': volatility_domain_factors
        }
    
    def _create_target_factor_definitions(self) -> Dict[str, Any]:
        """Create target factor domain entities and their repository representations."""
        print("  🎯 Creating target factor definitions...")
        
        factors_created = 0
        target_domain_factors = []
        
        # Define target factors
        target_configs = [
            {'name': 'target_returns', 'target_type': 'target_returns', 'forecast_horizon': 1, 'is_scaled': True, 'group': 'target', 'subgroup': 'scaled'},
            {'name': 'target_returns_nonscaled', 'target_type': 'target_returns_nonscaled', 'forecast_horizon': 1, 'is_scaled': False, 'group': 'target', 'subgroup': 'nonscaled'}
        ]
        
        for target_config in target_configs:
            try:
                
                
                # Create domain target factor entity
                target_factor = ShareTargetFactor(
                    name=target_config['name'],
                    target_type=target_config['target_type'],
                    forecast_horizon=target_config['forecast_horizon'],
                    is_scaled=target_config['is_scaled'],
                    group=target_config['group'],
                    subgroup=target_config['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{target_config['target_type']} target variable (horizon: {target_config['forecast_horizon']}, scaled: {target_config['is_scaled']})"
                )
                
                # Create or get corresponding repository factor
                repo_factor = self.factor_data_service.create_or_get_factor(
                    name=target_config['name'],
                    group=target_config['group'],
                    subgroup=target_config['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=target_factor.definition
                )
                
                # Link the domain entity with the repository factor
                target_factor.factor_id = repo_factor.id
                target_domain_factors.append(target_factor)
                factors_created += 1
                
                print(f"    ✅ Created target factor: {target_config['name']} (ID: {repo_factor.id})")
                
            except Exception as e:
                print(f"    ❌ Error creating target factor {target_config['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created,
            'factors_created_list': target_domain_factors
        }
    
    def _calculate_volatility_factor_values(self, tickers: List[str], overwrite: bool, volatility_factors_list: List) -> Dict[str, Any]:
        """Calculate and store volatility factor values."""
        print("📊 Calculating volatility factor values...")
        
        total_values_stored = 0
        
        for volatility_factor in volatility_factors_list:
            try:
                
                # Get repository factor by name
                repo_factor = self.factor_data_service.get_factor_by_name(volatility_factor.name)
                if not repo_factor:
                    print(f"      ❌ Repository factor not found for {volatility_factor.name}")
                    continue
                
                # Use factor calculation service instead of direct value class
                # Proper calculations are done per ticker below
                
                # Process each ticker
                for ticker in tickers:
                    share = self.factor_data_service.get_company_share_by_ticker(ticker)
                    if not share:
                        continue
                    
                    # Load price data for ticker
                    ticker_data = self._load_ticker_price_data(ticker)
                    if ticker_data is None or ticker_data.empty:
                        continue
                    
                    # Use factor calculation service
                    if 'close_price' in ticker_data.columns:
                        prices = ticker_data['close_price'].tolist()
                        dates = ticker_data.index.tolist()
                        
                        volatility_results = self.factor_calculation_service.calculate_and_store_volatility(
                            factor=volatility_factor,
                            entity_id=share.id,
                            ticker=ticker,
                            overwrite=overwrite
                        )
                        values_stored = len(volatility_results) if volatility_results else 0
                    else:
                        values_stored = 0
                    
                    total_values_stored += values_stored
                    print(f"      ✅ {ticker}: stored {values_stored} {volatility_factor.volatility_type} values")
                    
            except Exception as e:
                print(f"      ❌ Error calculating volatility factor {volatility_factor.name}: {str(e)}")
        
        return {'total_values': total_values_stored}
    
    def _calculate_target_factor_values(self, tickers: List[str], overwrite: bool, target_factors_list: List) -> Dict[str, Any]:
        """Calculate and store target factor values."""
        print("🎯 Calculating target factor values...")
        
        total_values_stored = 0
        
        for target_factor in target_factors_list:
            try:
                
                # Get repository factor by name
                repo_factor = self.factor_data_service.get_factor_by_name(target_factor.name)
                if not repo_factor:
                    print(f"      ❌ Repository factor not found for {target_factor.name}")
                    continue
                
                # Use factor calculation service instead of direct value class
                target_results = []
                
                # Process each ticker
                for ticker in tickers:
                    share = self.factor_data_service.get_company_share_by_ticker(ticker)
                    if not share:
                        continue
                    
                    # Load price data for ticker
                    ticker_data = self._load_ticker_price_data(ticker)
                    if ticker_data is None or ticker_data.empty:
                        continue
                    
                    # Use factor calculation service for target factors
                    if 'close_price' in ticker_data.columns:
                        prices = ticker_data['close_price'].tolist()
                        dates = ticker_data.index.tolist()
                        
                        # Calculate target returns using domain logic
                        target_values = target_factor.calculate_target(
                            prices=prices,
                            forecast_horizon=target_factor.forecast_horizon,
                            is_scaled=target_factor.is_scaled
                        )
                        
                        # Store via factor service
                        values_stored = self.factor_calculation_service._store_factor_values(
                            factor=repo_factor,
                            entity_id=share.id,
                            entity_type='share',
                            values=target_values,
                            dates=dates[:-target_factor.forecast_horizon] if dates else [],
                            overwrite=overwrite
                        )
                    else:
                        values_stored = 0
                    
                    total_values_stored += values_stored
                    print(f"      ✅ {ticker}: stored {values_stored} {target_factor.target_type} values")
                    
            except Exception as e:
                print(f"      ❌ Error calculating target factor {target_factor.name}: {str(e)}")
        
        return {'total_values': total_values_stored}
    
    def _load_ticker_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load price data for a single ticker from database using repository pattern."""
        try:
            # Use FactorDataService for price data loading
            return self.factor_data_service.load_ticker_price_data(ticker)
                
        except Exception as e:
            print(f"      ⚠️  Error loading price data for {ticker}: {str(e)}")
            return None