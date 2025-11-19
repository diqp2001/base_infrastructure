"""
Stock Data Repository for Backtesting
Provides access to historical stock price data saved from CSV files.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from application.services.database_service import DatabaseService


class StockDataRepository:
    """Repository for accessing historical stock price data during backtesting."""
    
    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.session = database_service.session
    
    def get_historical_data(
        self, 
        ticker: str, 
        periods: int, 
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Retrieve historical stock data for a given ticker.
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            periods: Number of periods to retrieve
            end_time: End date for data retrieval (defaults to latest)
            
        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        table_name = f"stock_price_data_{ticker.lower()}"
        
        try:
            # Build query to get historical data
            if end_time:
                query = f"""
                SELECT * FROM {table_name}
                WHERE Date <= :end_time
                ORDER BY Date DESC
                LIMIT :periods
                """
                params = {"end_time": end_time.strftime('%Y-%m-%d'), "periods": periods}
            else:
                query = f"""
                SELECT * FROM {table_name}
                ORDER BY Date DESC
                LIMIT :periods
                """
                params = {"periods": periods}
            
            # Execute query and return DataFrame
            result = pd.read_sql(text(query), con=self.session.bind, params=params)
            
            if not result.empty:
                # Sort by date ascending for proper time series
                result = result.sort_values('Date')
                # Ensure Date column is datetime
                result['Date'] = pd.to_datetime(result['Date'])
                print(f"📊 Retrieved {len(result)} price records for {ticker}")
                return result
            else:
                print(f"⚠️  No data found for ticker {ticker} in table {table_name}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error retrieving data for {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def get_multiple_tickers_data(
        self, 
        tickers: List[str], 
        periods: int,
        end_time: Optional[datetime] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Retrieve historical data for multiple tickers.
        
        Args:
            tickers: List of stock symbols
            periods: Number of periods to retrieve
            end_time: End date for data retrieval
            
        Returns:
            Dictionary mapping ticker to DataFrame
        """
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_historical_data(ticker, periods, end_time)
        return result
    
    def get_price_at_date(self, ticker: str, target_date: datetime) -> Optional[float]:
        """
        Get the closing price for a specific ticker on a specific date.
        
        Args:
            ticker: Stock symbol
            target_date: Date to get price for
            
        Returns:
            Closing price or None if not found
        """
        table_name = f"stock_price_data_{ticker.lower()}"
        
        try:
            query = f"""
            SELECT Close FROM {table_name}
            WHERE Date = :target_date
            LIMIT 1
            """
            params = {"target_date": target_date.strftime('%Y-%m-%d')}
            
            result = pd.read_sql(text(query), con=self.session.bind, params=params)
            
            if not result.empty:
                return float(result.iloc[0]['Close'])
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error getting price for {ticker} on {target_date}: {str(e)}")
            return None
    
    def table_exists(self, ticker: str) -> bool:
        """Check if a stock price table exists for the given ticker."""
        table_name = f"stock_price_data_{ticker.lower()}"
        
        try:
            query = f"SELECT 1 FROM {table_name} LIMIT 1"
            result = pd.read_sql(text(query), con=self.session.bind)
            return not result.empty
        except:
            return False
    
    def get_available_tickers(self) -> List[str]:
        """Get list of tickers with available price data in the database."""
        try:
            # Query to get all tables that match stock price data pattern
            tables_query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'stock_price_data_%'
            """
            
            result = pd.read_sql(text(tables_query), con=self.session.bind)
            
            # Extract ticker symbols from table names
            tickers = []
            for table_name in result['name'].tolist():
                ticker = table_name.replace('stock_price_data_', '').upper()
                tickers.append(ticker)
            
            return tickers
            
        except Exception as e:
            print(f"❌ Error getting available tickers: {str(e)}")
            return []