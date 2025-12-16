"""
Factor Data Service - handles all data retrieval and storage operations for factors.
Provides a service layer to replace direct repository calls from managers.
"""

from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import date, datetime

from src.domain.entities.factor.factor import Factor
from domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.repositories.local_repo.factor.base_factor_repository import BaseFactorRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.share_factor_repository import ShareFactorRepository
from application.services.database_service.database_service import DatabaseService


class FactorDataService:
    """Service for all factor data retrieval and storage operations."""
    
    def __init__(self, database_service: DatabaseService, db_type: str = 'sqlite'):
        """
        Initialize the service with database service and repositories.
        
        Args:
            database_service: DatabaseService instance for database operations
            db_type: Database type for repository initialization
        """
        self.database_service = database_service
        
        # Initialize repositories
        self.base_factor_repository = BaseFactorRepository(database_service.session)
        self.company_share_repository = CompanyShareRepository(database_service.session)
        self.share_factor_repository = ShareFactorRepository(database_service.session)
    
    # CompanyShare operations
    def get_company_share_by_ticker(self, ticker: str) -> Optional[CompanyShare]:
        """Get company share entity by ticker."""
        try:
            shares = self.company_share_repository.get_by_ticker(ticker)
            return shares[0] if shares else None
        except Exception as e:
            print(f"Error getting company share by ticker {ticker}: {str(e)}")
            return None
    
    def get_company_shares_by_tickers(self, tickers: List[str]) -> Dict[str, Optional[CompanyShare]]:
        """Get multiple company share entities by tickers."""
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_company_share_by_ticker(ticker)
        return result
    
    # Factor operations
    def create_or_get_factor(self, name: str, group: str, subgroup: str, 
                            data_type: str, source: str, definition: str) -> Optional[Factor]:
        """Create or get factor using the standardized repository pattern."""
        try:
            return self.base_factor_repository._create_or_get_factor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type=data_type,
                source=source,
                definition=definition
            )
        except Exception as e:
            print(f"Error creating/getting factor {name}: {str(e)}")
            return None
    
    def get_factor_by_name(self, name: str) -> Optional[Factor]:
        """Get factor entity by name."""
        try:
            return self.share_factor_repository.get_by_name(name)
        except Exception as e:
            print(f"Error getting factor by name {name}: {str(e)}")
            return None
    
    def get_factors_by_groups(self, groups: List[str]) -> List[Factor]:
        """Get factors by groups."""
        try:
            return self.share_factor_repository.get_factors_by_groups(groups)
        except Exception as e:
            print(f"Error getting factors by groups {groups}: {str(e)}")
            return []
    
    # Factor value operations
    def store_factor_values(self, factor: Factor, share: CompanyShare, 
                           data: pd.DataFrame, column: str, overwrite: bool = False) -> int:
        """Store factor values for a share."""
        try:
            return self.share_factor_repository._store_factor_values(
                factor, share, data, column, overwrite
            )
        except Exception as e:
            print(f"Error storing factor values for {factor.name}: {str(e)}")
            return 0
    
    def get_factor_values(self, factor_id: int, entity_id: int, 
                         start_date: Optional[str] = None, 
                         end_date: Optional[str] = None) -> List:
        """Get factor values for a specific factor and entity."""
        try:
            return self.share_factor_repository.get_factor_values(
                factor_id, entity_id, start_date, end_date
            )
        except Exception as e:
            print(f"Error getting factor values for factor {factor_id}: {str(e)}")
            return []
    
    def get_factor_values_df(self, factor_id: int, entity_id: int) -> pd.DataFrame:
        """Get factor values as DataFrame for a specific factor and entity."""
        try:
            return self.share_factor_repository.get_factor_values_df(
                factor_id=factor_id, 
                entity_id=entity_id
            )
        except Exception as e:
            print(f"Error getting factor values DataFrame for factor {factor_id}: {str(e)}")
            return pd.DataFrame()
    
    # Bulk operations for efficiency
    def bulk_store_factor_values(self, storage_operations: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Perform bulk factor value storage operations.
        
        Args:
            storage_operations: List of dicts with keys: 'factor', 'share', 'data', 'column', 'overwrite'
            
        Returns:
            Dict with results per operation
        """
        results = {}
        for i, operation in enumerate(storage_operations):
            try:
                values_stored = self.store_factor_values(
                    factor=operation['factor'],
                    share=operation['share'],
                    data=operation['data'],
                    column=operation['column'],
                    overwrite=operation.get('overwrite', False)
                )
                results[f"operation_{i}"] = values_stored
            except Exception as e:
                print(f"Error in bulk storage operation {i}: {str(e)}")
                results[f"operation_{i}"] = 0
        
        return results
    
    def load_ticker_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load price data for a ticker from the database.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            DataFrame with price data or None if not found
        """
        try:
            # Get company entity
            company = self.get_company_share_by_ticker(ticker)
            if not company:
                print(f"Company not found for ticker: {ticker}")
                return None
            
            # Define price factor names to fetch
            price_factor_names = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            price_data = {}
            
            # Fetch each price factor from database
            for factor_name in price_factor_names:
                factor_entity = self.get_factor_by_name(factor_name)
                if factor_entity:
                    df = self.get_factor_values_df(
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
                print(f"No price data found in database for {ticker}")
                return None
            
            # Combine into single DataFrame
            price_df = pd.DataFrame(price_data)
            price_df.index.name = 'Date'
            return price_df
                
        except Exception as e:
            print(f"Error loading price data for {ticker}: {str(e)}")
            return None
    
    def get_ticker_factor_data(self, ticker: str, start_date: Optional[str], 
                              end_date: Optional[str], factor_groups: List[str]) -> Optional[pd.DataFrame]:
        """
        Get factor data for a specific ticker.
        
        Args:
            ticker: Stock ticker
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            factor_groups: List of factor groups to include
            
        Returns:
            DataFrame with factor data or None if not found
        """
        try:
            share = self.get_company_share_by_ticker(ticker)
            if not share:
                return None
            
            # Get factors for the specified groups
            factors = self.get_factors_by_groups(factor_groups)
            if not factors:
                return None
            
            # Retrieve factor values
            factor_data = {}
            for factor in factors:
                values = self.get_factor_values(
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
            
        except Exception as e:
            print(f"Error getting ticker factor data for {ticker}: {str(e)}")
            return None
    
    # Convenience methods for common factor patterns
    def get_close_price_factor(self) -> Optional[Factor]:
        """Get the Close price factor."""
        return self.get_factor_by_name('Close')
    
    def get_price_factors(self) -> List[Factor]:
        """Get all price-related factors."""
        price_factor_names = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        factors = []
        for name in price_factor_names:
            factor = self.get_factor_by_name(name)
            if factor:
                factors.append(factor)
        return factors
    
    def validate_ticker_and_factor_existence(self, ticker: str, factor_name: str) -> bool:
        """
        Validate that both ticker and factor exist in the database.
        
        Args:
            ticker: Stock ticker to validate
            factor_name: Factor name to validate
            
        Returns:
            True if both exist, False otherwise
        """
        share = self.get_company_share_by_ticker(ticker)
        factor = self.get_factor_by_name(factor_name)
        return share is not None and factor is not None