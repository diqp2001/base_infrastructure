"""
Factor management component combining factor creation capabilities
with spatiotemporal feature storage and retrieval.

Integrates the factor system from test_project_factor_creation with 
the advanced feature engineering from spatiotemporal models.
"""

import os
import time
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pathlib import Path

from application.managers.database_managers.database_manager import DatabaseService
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository

from .feature_engineer import SpatiotemporalFeatureEngineer
from ..config import DEFAULT_CONFIG


class FactorEnginedDataManager:
    """
    Manages factor creation, storage, and retrieval for spatiotemporal models.
    
    Combines the entity/factor management from test_project_factor_creation
    with the advanced feature engineering from spatiotemporal_momentum_manager.
    """
    
    def __init__(self, database_manager: DatabaseService):
        self.database_service = database_manager
        self.config = DEFAULT_CONFIG
        
        # Initialize repositories
        self.company_share_repository = CompanyShareRepositoryLocal(database_manager.session)
        self.share_factor_repository = ShareFactorRepository(self.config['DATABASE']['DB_TYPE'])
        
        # Initialize feature engineer
        self.feature_engineer = SpatiotemporalFeatureEngineer(self.database_service)
        
        # Data paths - find project root by looking for data/stock_data directory
        current_path = Path(__file__).resolve()
        self.project_root = current_path
        
        # Walk up the directory tree to find the project root
        while not (self.project_root / 'data' / 'stock_data').exists() and self.project_root.parent != self.project_root:
            self.project_root = self.project_root.parent
            
        self.stock_data_path = self.project_root / "data" / "stock_data"
    
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
        
        # First ensure basic entities and price factors exist
        entity_summary = self._ensure_entities_exist(tickers)
        
        # Create momentum factor definitions
        momentum_factors_summary = self._create_momentum_factor_definitions()
        
        # Calculate and store momentum factor values
        values_summary = self._calculate_momentum_factor_values(tickers, overwrite)
        
        total_summary = {
            'entities': entity_summary,
            'factors_created': momentum_factors_summary['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
        
        print(f"✅ Momentum factor population complete:")
        print(f"  • Entities verified: {entity_summary['verified']}")
        print(f"  • Factors created: {total_summary['factors_created']}")  
        print(f"  • Values calculated: {total_summary['values_calculated']}")
        
        return total_summary
    
    def calculate_technical_indicators(self,
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
        
        # Create technical factor definitions
        technical_factors_summary = self._create_technical_factor_definitions()
        
        # Calculate and store values
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
        
        # Get the company share entity
        share = self.company_share_repository.get_by_ticker(ticker)
        if not share:
            raise ValueError(f"Company share not found for ticker: {ticker}")
        
        stored_factors = 0
        stored_values = 0
        
        # Store each column as a factor
        for column in data.columns:
            if column in ['Date'] or data[column].dtype == 'object':
                continue
                
            try:
                # Create or get factor
                factor = self._create_or_get_factor(
                    name=column,
                    group=factor_group,
                    subgroup='spatiotemporal',
                    definition=f'Spatiotemporal engineered feature: {column}'
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
                                   factor_groups: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Retrieve factor data formatted for model training.
        
        Args:
            tickers: List of tickers to retrieve
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            factor_groups: List of factor groups to include
            
        Returns:
            DataFrame ready for model training
        """
        print(f"📊 Retrieving factor data for {len(tickers)} tickers...")
        
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
            raise ValueError("No factor data retrieved for any ticker")
        
        # Combine into format expected by spatiotemporal models
        return self._format_for_model_training(all_data)
    
    def _ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
        """Ensure all required entities exist in the database."""
        print("  📋 Verifying entities exist...")
        
        existing_count = 0
        created_count = 0
        
        for ticker in tickers:
            share = self.company_share_repository.get_by_ticker(ticker)
            
            if share:
                existing_count += 1
            else:
                # Create the entity
                try:
                    new_share = CompanyShareEntity(
                        ticker=ticker,
                        exchange_id=1,
                        company_id=None,
                        start_date=datetime(2020, 1, 1)
                    )
                    new_share.set_company_name(f"{ticker} Inc.")
                    new_share.update_sector_industry("Technology", None)
                    
                    created_share = self.company_share_repository.add(new_share)
                    created_count += 1
                    print(f"    ✅ Created entity for {ticker}")
                    
                except Exception as e:
                    print(f"    ❌ Error creating entity for {ticker}: {str(e)}")
        
        return {
            'verified': existing_count + created_count,
            'existing': existing_count,
            'created': created_count
        }
    
    def _create_momentum_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions for momentum features."""
        print("  📈 Creating momentum factor definitions...")
        
        factors_created = 0
        
        # Momentum factors from config
        momentum_factors = self.config['FACTORS']['MOMENTUM_FACTORS']
        
        for factor_def in momentum_factors:
            try:
                factor = self._create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    definition=f"Spatiotemporal momentum feature: {factor_def['name']}"
                )
                
                if factor:
                    factors_created += 1
                    
                    
                        
            except Exception as e:
                print(f"    ❌ Error creating momentum factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created
        }
    
    def _create_technical_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions for technical indicators."""
        print("  🔧 Creating technical factor definitions...")
        
        factors_created = 0
        
        # Technical factors from config
        technical_factors = self.config['FACTORS']['TECHNICAL_FACTORS']
        
        for factor_def in technical_factors:
            try:
                factor = self._create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    definition=f"Technical indicator: {factor_def['name']}"
                )
                
                if factor:
                    factors_created += 1
                    
                    
                    
                    
                        
            except Exception as e:
                print(f"    ❌ Error creating technical factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created
        }
    
    def _calculate_momentum_factor_values(self, tickers: List[str], overwrite: bool) -> Dict[str, Any]:
        """Calculate and store momentum factor values."""
        print("  📊 Calculating momentum factor values...")
        
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
                
                # Engineer momentum features
                engineered_data = self.feature_engineer.add_deep_momentum_features(
                    df, 'Close'
                )
                
                # Store the momentum features as factors
                values_stored = self._store_momentum_features(
                    engineered_data, ticker, overwrite
                )
                total_values += values_stored
                
                print(f"    ✅ Processed {ticker}: {values_stored} momentum values")
                
            except Exception as e:
                print(f"    ❌ Error processing momentum for {ticker}: {str(e)}")
        
        return {'total_values': total_values}
    
    def _calculate_technical_factor_values(self, tickers: List[str], overwrite: bool) -> Dict[str, Any]:
        """Calculate and store technical indicator values.""" 
        print("  🔧 Calculating technical indicator values...")
        
        total_values = 0
        
        for ticker in tickers:
            csv_file = self.stock_data_path / f"{ticker}.csv"
            if not csv_file.exists():
                continue
                
            try:
                # Load data
                df = pd.read_csv(csv_file)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                
                # Standardize column names
                df = df.rename(columns={
                    'Open': 'open_price', 'High': 'high_price',
                    'Low': 'low_price', 'Close': 'close_price',
                    'Adj Close': 'adj_close_price', 'Volume': 'volume'
                })
                
                # Engineer technical features
                engineered_data = self.feature_engineer.add_technical_indicators(
                    df, 'close_price'
                )
                
                # Store technical features as factors
                values_stored = self._store_technical_features(
                    engineered_data, ticker, overwrite
                )
                total_values += values_stored
                
                print(f"    ✅ Processed {ticker}: {values_stored} technical values")
                
            except Exception as e:
                print(f"    ❌ Error processing technical indicators for {ticker}: {str(e)}")
        
        return {'total_values': total_values}
    
    def _store_momentum_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store momentum features as factor values."""
        share = self.company_share_repository.get_by_ticker(ticker)
        if not share:
            return 0
        
        values_stored = 0
        momentum_columns = [col for col in data.columns if 'norm_' in col and 'return' in col]
        
        for column in momentum_columns:
            factor = self.share_factor_repository.get_by_name(column)
            if factor:
                values_stored += self._store_factor_values(
                    factor, share, data, column, overwrite
                )
        
        return values_stored
    
    def _store_technical_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store technical features as factor values."""
        share = self.company_share_repository.get_by_ticker(ticker)
        if not share:
            return 0
        
        values_stored = 0
        technical_columns = ['rsi_14', 'bollinger_upper', 'bollinger_lower', 'stoch_k', 'stoch_d']
        
        for column in technical_columns:
            if column in data.columns:
                factor = self.share_factor_repository.get_by_name(column)
                if factor:
                    values_stored += self._store_factor_values(
                        factor, share, data, column, overwrite
                    )
        
        return values_stored
    
    def _create_or_get_factor(self, name: str, group: str, subgroup: str, definition: str):
        """Create factor if it doesn't exist, otherwise return existing."""
        existing_factor = self.share_factor_repository.get_by_name(name)
        if existing_factor:
            return existing_factor
        
        return self.share_factor_repository.add_factor(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type='numeric',
            source='spatiotemporal_engineering',
            definition=definition
        )
    
    
    def _store_factor_values(self, factor, share, data: pd.DataFrame, column: str, overwrite: bool) -> int:
        """Store factor values for a specific factor."""
        values_stored = 0
        
        # Get existing dates if not overwriting
        existing_dates = set()
        if not overwrite:
            existing_dates = self.share_factor_repository.get_existing_value_dates(
                factor.id, share.id
            )
        
        for date_index, row in data.iterrows():
            if pd.isna(row[column]):
                continue
                
            trade_date = date_index.date() if hasattr(date_index, 'date') else date_index
            
            if not overwrite and trade_date in existing_dates:
                continue
            
            try:
                self.share_factor_repository.add_factor_value(
                    factor_id=factor.id,
                    entity_id=share.id,
                    date=trade_date,
                    value=Decimal(str(row[column]))
                )
                values_stored += 1
                
            except Exception as e:
                print(f"      ⚠️  Error storing {column} value for {trade_date}: {str(e)}")
        
        return values_stored
    
    def _get_ticker_factor_data(self, ticker: str, start_date: Optional[str], 
                              end_date: Optional[str], factor_groups: List[str]) -> Optional[pd.DataFrame]:
        """Get factor data for a specific ticker."""
        share = self.company_share_repository.get_by_ticker(ticker)
        if not share:
            return None
        
        # Get factors for the specified groups
        factors = self.share_factor_repository.get_factors_by_groups(factor_groups)
        
        if not factors:
            return None
        
        # Retrieve factor values
        factor_data = {}
        for factor in factors:
            values = self.share_factor_repository.get_factor_values(
                factor.id, share.id, start_date, end_date
            )
            if values:
                factor_data[factor.name] = {
                    pd.to_datetime(v.date): float(v.value) for v in values
                }
        
        if not factor_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(factor_data)
        df.index.name = 'Date'
        return df
    
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