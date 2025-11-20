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

from application.services.database_service.database_service import DatabaseService
from domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor
from domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor
from domain.entities.finance.financial_assets.company_share import CompanyShare as CompanyShareEntity
from infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository as CompanyShareRepositoryLocal
from infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
# ShareFactorValueMapper removed - using FactorValueMapper instead
from infrastructure.repositories.mappers.factor.factor_value_mapper import FactorValueMapper

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
        self.base_factor_repository = BaseFactorRepository(self.config['DATABASE']['DB_TYPE'])
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

                
                factor = self.base_factor_repository._create_or_get_factor(
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
                factor = self.base_factor_repository._create_or_get_factor(
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
                
                
                # Create domain momentum factor entity
                momentum_factor = ShareMomentumFactor(
                    name=factor_def['name'],
                    period=factor_def['period'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{factor_def['period']}-day momentum return factor"
                )
                
                # Create or get corresponding repository factor
                repo_factor = self.share_factor_repository._create_or_get_factor(
                    name=factor_def['name'],
                    group=factor_def['group'],
                    subgroup=factor_def['subgroup'],
                    data_type="numeric",
                    source="internal",
                    definition=f"{factor_def['period']}-day momentum return factor"
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
                elif 'macd' in name_lower:
                    indicator_type = "MACD"
                    # Extract fast and slow periods from MACD name like "macd_8_24"
                    import re
                    periods_match = re.findall(r'(\d+)', factor_def['name'])
                    if len(periods_match) >= 2:
                        period = (int(periods_match[0]), int(periods_match[1]))  # (fast, slow)
                    else:
                        period = (12, 26)  # Default MACD periods
                
                # Create domain technical factor entity
                technical_factor = ShareTechnicalFactor(
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
                                         momentum_domain_factors: List[ShareMomentumFactor]) -> Dict[str, Any]:
        """Calculate and store momentum factor values using domain entities."""
        print("📊 Calculating momentum factor values...")
        total_values = 0

        for factor in momentum_domain_factors:
            momentum_value = ShareMomentumFactorValue(
                database_manager=self.database_service, 
                factor=factor
            )
            
            for ticker in tickers:
                try:
                    company = self.company_share_repository.get_by_ticker(ticker)[0]
                    
                    
                    factorentityClose = self.share_factor_repository.get_by_name('Close')
                    df = self.share_factor_repository.get_factor_values_df(
                        factor_id=int(factorentityClose.id), 
                        entity_id=company.id
                    )
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df["value"] = df["value"].astype(float)

                    # Get repository factor for momentum storage
                    repository_factor = self.share_factor_repository.get_by_name(factor.name)
                    
                    if repository_factor:
                        # Use repository pattern (same as _store_momentum_features)
                        values_stored = momentum_value.store_package_momentum_factors(
                            repository=self.share_factor_repository,
                            factor=repository_factor,
                            share=company,
                            data=df,
                            column_name="value",
                            period=factor.period,
                            overwrite=overwrite
                        )

                        total_values += values_stored
                        print(f"✅ {ticker}: stored {values_stored} {factor.period}-day momentum values")

                except Exception as e:
                    print(f"❌ Error processing {ticker} for {factor.name}: {e}")

        return {"total_values": total_values}

    
    def _calculate_technical_factor_values(self, tickers: List[str], overwrite: bool, 
                                         technical_domain_factors: List[ShareTechnicalFactor]) -> Dict[str, Any]:
        """Calculate and store technical indicator values using domain entities (same pattern as momentum factors)."""
        print("📊 Calculating technical indicator values...")
        total_values = 0

        for factor in technical_domain_factors:
            technical_value = ShareTechnicalFactorValue(
                database_manager=self.database_service, 
                factor=factor
            )
            
            for ticker in tickers:
                try:
                    company = self.company_share_repository.get_by_ticker(ticker)[0]
                    
                    factorentityClose = self.share_factor_repository.get_by_name('Close')
                    df = self.share_factor_repository.get_factor_values_df(
                        factor_id=int(factorentityClose.id), 
                        entity_id=company.id
                    )
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                    df["value"] = df["value"].astype(float)
                    
                    # Get repository factor for technical storage
                    repository_factor = self.share_factor_repository.get_by_name(factor.name)
                    
                    if repository_factor:
                        # Use repository pattern (same as momentum factors)
                        values_stored = technical_value.store_package_technical_factors(
                            repository=self.share_factor_repository,
                            factor=repository_factor,
                            share=company,
                            data=df,
                            column_name="value",  # Will be processed in calculate() method
                            indicator_type=factor.indicator_type,
                            period=factor.period,
                            overwrite=overwrite
                        )

                        total_values += values_stored
                        print(f"✅ {ticker}: stored {values_stored} {factor.indicator_type} values")

                except Exception as e:
                    print(f"❌ Error processing {ticker} for {factor.name}: {e}")

        return {"total_values": total_values}
    
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
            factor = self.share_factor_repository.get_by_name(column['name'])
            if factor:
                # Map factor name to actual CSV column name
                csv_column_name = factor_to_column_mapping.get(column['name'], column['name'])
                if csv_column_name in data.columns:
                    values_stored += self.share_factor_repository._store_factor_values(
                        factor, share, data, csv_column_name, overwrite
                    )
                else:
                    print(f"      ⚠️  Column '{csv_column_name}' not found for factor '{column['name']}'")
        
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
        
        # Handle list return from get_by_ticker
        share = share[0] if isinstance(share, list) else share
        
        # Get factors for the specified groups
        factors = self.share_factor_repository.get_factors_by_groups(factor_groups)
        
        if not factors:
            return None
        
        # Retrieve factor values
        factor_data = {}
        for factor in factors:
            values = self.share_factor_repository.get_factor_values(
                int(factor.id), share.id, start_date, end_date
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
                # Import domain classes
                from domain.entities.factor.finance.financial_assets.share_factor.volatility_factor_share import ShareVolatilityFactor
                
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
                repo_factor = self.share_factor_repository._create_or_get_factor(
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
                # Import domain classes
                from domain.entities.factor.finance.financial_assets.share_factor.target_factor_share import ShareTargetFactor
                
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
                repo_factor = self.share_factor_repository._create_or_get_factor(
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
                # Import domain value calculator
                from domain.entities.factor.finance.financial_assets.share_factor.volatility_factor_share_value import ShareVolatilityFactorValue
                
                # Get repository factor by name
                repo_factor = self.share_factor_repository.get_by_name(volatility_factor.name)
                if not repo_factor:
                    print(f"      ❌ Repository factor not found for {volatility_factor.name}")
                    continue
                
                # Create value calculator
                volatility_calculator = ShareVolatilityFactorValue(self.database_service, volatility_factor)
                
                # Process each ticker
                for ticker in tickers:
                    share = self.company_share_repository.get_by_ticker(ticker)
                    if not share:
                        continue
                    share = share[0] if isinstance(share, list) else share
                    
                    # Load price data for ticker
                    ticker_data = self._load_ticker_price_data(ticker)
                    if ticker_data is None or ticker_data.empty:
                        continue
                    
                    # Store volatility values using repository pattern (same as momentum)
                    values_stored = volatility_calculator.store_factor_values(
                        repository=self.share_factor_repository,
                        factor=repo_factor,
                        share=share,
                        data=ticker_data,
                        column_name='close_price',
                        volatility_type=volatility_factor.volatility_type,
                        period=volatility_factor.period,
                        overwrite=overwrite
                    )
                    
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
                # Import domain value calculator
                from domain.entities.factor.finance.financial_assets.share_factor.target_factor_share_value import ShareTargetFactorValue
                
                # Get repository factor by name
                repo_factor = self.share_factor_repository.get_by_name(target_factor.name)
                if not repo_factor:
                    print(f"      ❌ Repository factor not found for {target_factor.name}")
                    continue
                
                # Create value calculator
                target_calculator = ShareTargetFactorValue(self.database_service, target_factor)
                
                # Process each ticker
                for ticker in tickers:
                    share = self.company_share_repository.get_by_ticker(ticker)
                    if not share:
                        continue
                    share = share[0] if isinstance(share, list) else share
                    
                    # Load price data for ticker
                    ticker_data = self._load_ticker_price_data(ticker)
                    if ticker_data is None or ticker_data.empty:
                        continue
                    
                    # Store target values using repository pattern (same as momentum)
                    values_stored = target_calculator.store_factor_values(
                        repository=self.share_factor_repository,
                        factor=repo_factor,
                        share=share,
                        data=ticker_data,
                        column_name='close_price',
                        target_type=target_factor.target_type,
                        forecast_horizon=target_factor.forecast_horizon,
                        is_scaled=target_factor.is_scaled,
                        overwrite=overwrite
                    )
                    
                    total_values_stored += values_stored
                    print(f"      ✅ {ticker}: stored {values_stored} {target_factor.target_type} values")
                    
            except Exception as e:
                print(f"      ❌ Error calculating target factor {target_factor.name}: {str(e)}")
        
        return {'total_values': total_values_stored}
    
    def _load_ticker_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load price data for a single ticker from database using repository pattern."""
        try:
            # Get company entity
            company = self.company_share_repository.get_by_ticker(ticker)
            if not company:
                print(f"      ⚠️  Company not found for ticker: {ticker}")
                return None
            company = company[0] if isinstance(company, list) else company
            
            # Define price factor names to fetch
            price_factor_names = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            price_data = {}
            
            # Fetch each price factor from database
            for factor_name in price_factor_names:
                factor_entity = self.share_factor_repository.get_by_name(factor_name)
                if factor_entity:
                    df = self.share_factor_repository.get_factor_values_df(
                        factor_id=int(factor_entity.id), 
                        entity_id=company.id
                    )
                    if not df.empty:
                        df["date"] = pd.to_datetime(df["date"])
                        df.set_index("date", inplace=True)
                        df["value"] = df["value"].astype(float)
                        # Map to expected column names
                        column_mapping = {
                            'Open': 'open_price',
                            'High': 'high_price', 
                            'Low': 'low_price',
                            'Close': 'close_price',
                            'Adj Close': 'adj_close_price',
                            'Volume': 'volume'
                        }
                        price_data[column_mapping.get(factor_name, factor_name.lower())] = df['value']
            
            if not price_data:
                print(f"      ⚠️  No price data found in database for {ticker}")
                return None
            
            # Combine into single DataFrame
            price_df = pd.DataFrame(price_data)
            price_df.index.name = 'Date'
            return price_df
                
        except Exception as e:
            print(f"      ⚠️  Error loading price data for {ticker}: {str(e)}")
            return None