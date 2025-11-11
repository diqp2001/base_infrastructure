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

from application.managers.database_managers.database_manager import DatabaseManager
from domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share import MomentumFactorShare
from domain.entities.factor.finance.financial_assets.share_factor.momentum_factor_share_value import MomentumFactorShareValue
from domain.entities.factor.finance.financial_assets.share_factor.technical_factor_share import TechnicalFactorShare
from domain.entities.factor.finance.financial_assets.share_factor.technical_factor_share_value import TechnicalFactorShareValue
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
from infrastructure.repositories.mappers.factor.finance.financial_assets.share_factor_value_mapper import ShareFactorValueMapper

from .feature_engineer import SpatiotemporalFeatureEngineer
from ..config import DEFAULT_CONFIG


class FactorEnginedDataManager:
    """
    Manages factor creation, storage, and retrieval for spatiotemporal models.
    
    Combines the entity/factor management from test_project_factor_creation
    with the advanced feature engineering from spatiotemporal_momentum_manager.
    """
    
    def __init__(self, database_manager: DatabaseManager):
        self.database_manager = database_manager
        self.config = DEFAULT_CONFIG
        
        # Initialize repositories
        self.company_share_repository = CompanyShareRepositoryLocal(database_manager.session)
        self.share_factor_repository = ShareFactorRepository(self.config['DATABASE']['DB_TYPE'])
        
        # Initialize feature engineer
        self.feature_engineer = SpatiotemporalFeatureEngineer(self.database_manager)
        
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
        
        
        
        # Create momentum factor definitions
        momentum_factors_ = self._create_momentum_factor_definitions()
        
        # Calculate and store momentum factor values
        values_summary = self._calculate_momentum_factor_values(tickers, overwrite, momentum_factors_['factors_created_list'])
        
        total_summary = {
            'factors_created': momentum_factors_['factors_created'],
            'values_calculated': values_summary['total_values'],
            'tickers_processed': len(tickers),
            'success': True
        }
        
        print(f"✅ Momentum factor population complete:")
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
        
        # Calculate and store values using the domain factors
        values_summary = self._calculate_technical_factor_values(
            tickers, overwrite, technical_factors_summary['factors_created_list']
        )
        
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

                
                factor = self.share_factor_repository._create_or_get_factor(
                    name=column,
                    group=factor_group,
                    subgroup= "general",
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
    

    def _create_price_factor_definitions(self) -> Dict[str, Any]:
        """Create factor definitions for momentum features."""
        print("  📈 Creating Price factor definitions...")
        
        factors_created = 0
        
        # Price factors from config
        price_factors = self.config['FACTORS']['PRICE_FACTORS']
        
        for factor_def in price_factors:
            try:
                factor = self.share_factor_repository._create_or_get_factor(
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
        """Create momentum factor domain entities and their repository representations."""
        print("  📈 Creating momentum factor definitions...")
        
        factors_created = 0
        momentum_domain_factors = []
        
        # Momentum factors from config
        momentum_factors = self.config['FACTORS']['MOMENTUM_FACTORS']
        
        for factor_def in momentum_factors:
            try:
                # Extract period from factor name (e.g., "63-day Momentum" -> 63)
                period = 63  # Default period
                if 'day' in factor_def['name'].lower():
                    import re
                    period_match = re.search(r'(\d+)-day', factor_def['name'])
                    if period_match:
                        period = int(period_match.group(1))
                
                # Create domain momentum factor entity
                momentum_factor = MomentumFactorShare(
                    name=factor_def['name'],
                    period=period,
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{period}-day momentum return factor"
                )
                
                # Create or get corresponding repository factor
                repo_factor = self.share_factor_repository._create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{period}-day momentum return factor"
                )
                
                if repo_factor:
                    # Set the factor_id from repository
                    momentum_factor.factor_id = repo_factor.id
                    momentum_domain_factors.append(momentum_factor)
                    factors_created += 1
                    print(f"    ✅ Created momentum factor: {factor_def['name']} (ID: {repo_factor.id})")
                        
            except Exception as e:
                print(f"    ❌ Error creating momentum factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created,
            'factors_created_list': momentum_domain_factors
        }
    
    def _create_technical_factor_definitions(self) -> Dict[str, Any]:
        """Create technical indicator factor domain entities and their repository representations."""
        print("  🔧 Creating technical factor definitions...")
        
        factors_created = 0
        technical_domain_factors = []
        
        # Technical factors from config
        technical_factors = self.config['FACTORS']['TECHNICAL_FACTORS']
        
        for factor_def in technical_factors:
            try:
                # Extract indicator type and period from factor name
                indicator_type = "oscillator"  # Default type
                period = None
                
                name_lower = factor_def['name'].lower()
                if 'rsi' in name_lower:
                    indicator_type = "RSI"
                    import re
                    period_match = re.search(r'(\d+)', factor_def['name'])
                    if period_match:
                        period = int(period_match.group(1))
                elif 'bollinger' in name_lower:
                    indicator_type = "Bollinger"
                    period = 20  # Default Bollinger period
                elif 'stoch' in name_lower:
                    indicator_type = "Stochastic"
                    period = 14  # Default Stochastic period
                
                # Create domain technical factor entity
                technical_factor = TechnicalFactorShare(
                    name=factor_def['name'],
                    indicator_type=indicator_type,
                    period=period,
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{indicator_type} technical indicator{f' ({period}-period)' if period else ''}"
                )
                
                # Create or get corresponding repository factor
                repo_factor = self.share_factor_repository._create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{indicator_type} technical indicator{f' ({period}-period)' if period else ''}"
                )
                
                if repo_factor:
                    # Set the factor_id from repository
                    technical_factor.factor_id = repo_factor.id
                    technical_domain_factors.append(technical_factor)
                    factors_created += 1
                    print(f"    ✅ Created technical factor: {factor_def['name']} (ID: {repo_factor.id})")
                    
            except Exception as e:
                print(f"    ❌ Error creating technical factor {factor_def['name']}: {str(e)}")
        
        return {
            'factors_created': factors_created,
            'factors_created_list': technical_domain_factors
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
    
    def _calculate_momentum_factor_values(self, tickers: List[str], overwrite: bool, 
                                         momentum_domain_factors: List[MomentumFactorShare]) -> Dict[str, Any]:
        """Calculate and store momentum factor values using domain entities."""
        print("📊 Calculating momentum factor values...")
        total_values = 0

        for factor in momentum_domain_factors:
            momentum_value = MomentumFactorShareValue(
                database_manager=self.database_manager, 
                factor=factor
            )
            
            for ticker in tickers:
                try:
                    company = self.company_share_repository.get_by_ticker(ticker)[0]
                    
                    # Get price data (assuming factor_id=20 is Close price or similar)
                    price_factor_id = 20  # This should be configurable or determined dynamically
                    df = self.share_factor_repository.get_factor_values_df(
                        factor_id=price_factor_id, 
                        entity_id=company.id
                    )
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df["value"] = df["value"].astype(float)

                    # Calculate momentum using the domain factor's specific period
                    orm_values = momentum_value.store_package_momentum_factors(
                        data=df,
                        column_name="value",
                        entity_id=company.id,
                        factor_id=factor.factor_id,
                        period=factor.period,
                    )

                    if orm_values:
                        # Store the ORM values directly using session
                        for orm_value in orm_values:
                            if not overwrite:
                                # Check if value already exists
                                existing = self.share_factor_repository.factor_value_exists(
                                    orm_value.factor_id, orm_value.entity_id, orm_value.date
                                )
                                if existing:
                                    continue
                            
                            self.database_manager.session.add(orm_value)
                        
                        self.database_manager.session.commit()
                        total_values += len(orm_values)

                    print(f"✅ {ticker}: stored {len(orm_values)} {factor.period}-day momentum values")

                except Exception as e:
                    print(f"❌ Error processing {ticker} for {factor.name}: {e}")

        return {"total_values": total_values}

    
    def _calculate_technical_factor_values(self, tickers: List[str], overwrite: bool, 
                                         technical_domain_factors: List[TechnicalFactorShare]) -> Dict[str, Any]:
        """Calculate and store technical indicator values using domain entities."""
        print("  🔧 Calculating technical indicator values...")
        
        total_values = 0
        
        for factor in technical_domain_factors:
            technical_value = TechnicalFactorShareValue(
                database_manager=self.database_manager, 
                factor=factor
            )
            
            for ticker in tickers:
                csv_file = self.stock_data_path / f"{ticker}.csv"
                if not csv_file.exists():
                    continue
                    
                try:
                    company = self.company_share_repository.get_by_ticker(ticker)[0]
                    
                    # Load price data
                    df = pd.read_csv(csv_file)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    
                    # Standardize column names
                    df = df.rename(columns={
                        'Open': 'open_price', 'High': 'high_price',
                        'Low': 'low_price', 'Close': 'close_price',
                        'Adj Close': 'adj_close_price', 'Volume': 'volume'
                    })
                    
                    # Calculate specific technical indicator based on factor type
                    if factor.indicator_type == "RSI":
                        df['indicator_value'] = technical_value.calculate_rsi(
                            df['close_price'], factor.period or 14
                        )
                    elif factor.indicator_type == "Bollinger":
                        if 'upper' in factor.name.lower():
                            bollinger = technical_value.calculate_bollinger_bands(df['close_price'])
                            df['indicator_value'] = bollinger['upper']
                        elif 'lower' in factor.name.lower():
                            bollinger = technical_value.calculate_bollinger_bands(df['close_price'])
                            df['indicator_value'] = bollinger['lower']
                    elif factor.indicator_type == "Stochastic":
                        stoch = technical_value.calculate_stochastic(
                            df['high_price'], df['low_price'], df['close_price']
                        )
                        if 'k' in factor.name.lower():
                            df['indicator_value'] = stoch['k']
                        elif 'd' in factor.name.lower():
                            df['indicator_value'] = stoch['d']
                    
                    # Store the calculated technical indicator values
                    orm_values = technical_value.store_package_technical_factors(
                        data=df,
                        column_name="indicator_value",
                        entity_id=company.id,
                        factor_id=factor.factor_id,
                        indicator_type=factor.indicator_type
                    )
                    
                    if orm_values:
                        # Store the ORM values directly using session
                        for orm_value in orm_values:
                            if not overwrite:
                                # Check if value already exists
                                existing = self.share_factor_repository.factor_value_exists(
                                    orm_value.factor_id, orm_value.entity_id, orm_value.date
                                )
                                if existing:
                                    continue
                            
                            self.database_manager.session.add(orm_value)
                        
                        self.database_manager.session.commit()
                        total_values += len(orm_values)
                        
                    print(f"    ✅ {ticker}: stored {len(orm_values)} {factor.indicator_type} values")
                    
                except Exception as e:
                    print(f"    ❌ Error processing {factor.indicator_type} for {ticker}: {str(e)}")
        
        return {'total_values': total_values}
    
    def _store_momentum_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store momentum features as factor values."""
        share = self.company_share_repository.get_by_ticker(ticker)[0]
        if not share:
            return 0
        
        values_stored = 0
        momentum_columns = [col for col in data.columns if 'norm_' in col and 'return' in col]
        
        for column in momentum_columns:
            factor = self.share_factor_repository.get_by_name(column)
            if factor:
                values_stored += self.share_factor_repository._store_factor_values(
                    factor, share, data, column, overwrite
                )
        
        return values_stored
    
    def _store_price_features(self, data: pd.DataFrame, ticker: str, overwrite: bool) -> int:
        """Store price features as factor values."""
        share = self.company_share_repository.get_by_ticker(ticker)[0]
        if not share:
            return 0
        
        values_stored = 0
        price_columns =  self.config['FACTORS']['PRICE_FACTORS']
        
        for column in price_columns:
            factor = self.share_factor_repository.get_by_name(column['name'])
            if factor:
                values_stored += self.share_factor_repository._store_factor_values(
                    factor, share, data, column['name'], overwrite
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
                    values_stored += self.share_factor_repository._store_factor_values(
                        factor, share, data, column, overwrite
                    )
        
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
        combined_df = combined_df.fillna(method='ffill').fillna(method='bfill')
        
        return combined_df