"""
Data Loader for Market Making Project

Handles loading and processing of market data for derivatives pricing
and market making operations across multiple asset classes.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import numpy as np

# Database imports
from application.services.database_service.database_service import DatabaseService

# Domain imports for entities
try:
    from domain.entities.company_share import CompanyShare
    from infrastructure.models.company_share import CompanyShareModel
except ImportError as e:
    logging.warning(f"Domain/infrastructure imports not available: {e}")


class MarketMakingDataLoader:
    """
    Data loader for market making operations that handles:
    - Market data retrieval and caching
    - Derivatives pricing data preparation
    - Multi-asset class data management
    - Real-time and historical data access
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the MarketMakingDataLoader.
        
        Args:
            database_service: Database service for data access
        """
        self.database_service = database_service
        self.logger = logging.getLogger(__name__)
        
        # Data caching
        self.market_data_cache = {}
        self.curve_data_cache = {}
        self.volatility_cache = {}
        
        # Supported asset classes
        self.supported_asset_classes = ['equity', 'fixed_income', 'commodity']
        
        self.logger.info("MarketMakingDataLoader initialized")
    
    def get_market_data(self, symbol: str, asset_class: str = 'equity') -> Optional[Dict[str, Any]]:
        """
        Get current market data for a symbol.
        
        Args:
            symbol: Instrument symbol
            asset_class: Asset class (equity, fixed_income, commodity)
            
        Returns:
            Market data dictionary or None if not available
        """
        try:
            # Check cache first
            cache_key = f"{symbol}_{asset_class}"
            if cache_key in self.market_data_cache:
                cached_data = self.market_data_cache[cache_key]
                # Return cached data if less than 1 minute old
                if (datetime.now() - cached_data['timestamp']).seconds < 60:
                    return cached_data['data']
            
            # Load data based on asset class
            if asset_class == 'equity':
                market_data = self._get_equity_data(symbol)
            elif asset_class == 'fixed_income':
                market_data = self._get_fixed_income_data(symbol)
            elif asset_class == 'commodity':
                market_data = self._get_commodity_data(symbol)
            else:
                self.logger.warning(f"Unsupported asset class: {asset_class}")
                return None
            
            # Cache the data
            if market_data:
                self.market_data_cache[cache_key] = {
                    'data': market_data,
                    'timestamp': datetime.now()
                }
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return None
    
    def _get_equity_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for equity instruments."""
        try:
            # Try to get from database first
            with self.database_service.get_session() as session:
                # Query company share data
                company_share = session.query(CompanyShareModel).filter_by(symbol=symbol).first()
                
                if company_share:
                    # Get latest price data (this would typically come from a price table)
                    market_data = {
                        'symbol': symbol,
                        'asset_class': 'equity',
                        'price': Decimal('100.0'),  # Mock price - replace with actual data
                        'bid_price': Decimal('99.95'),
                        'ask_price': Decimal('100.05'),
                        'volume': 1000000,
                        'timestamp': datetime.now(),
                        'sector': company_share.sector if hasattr(company_share, 'sector') else 'Unknown',
                        'market_cap': getattr(company_share, 'market_cap', None),
                        'beta': getattr(company_share, 'beta', 1.0),
                        'dividend_yield': getattr(company_share, 'dividend_yield', 0.0)
                    }
                    
                    return market_data
                else:
                    # Fallback to mock data for testing
                    return self._get_mock_equity_data(symbol)
                    
        except Exception as e:
            self.logger.error(f"Error getting equity data for {symbol}: {str(e)}")
            return self._get_mock_equity_data(symbol)
    
    def _get_fixed_income_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for fixed income instruments."""
        # Mock fixed income data
        return {
            'symbol': symbol,
            'asset_class': 'fixed_income',
            'price': Decimal('101.25'),
            'yield': Decimal('0.0325'),  # 3.25% yield
            'duration': Decimal('5.2'),
            'convexity': Decimal('28.5'),
            'credit_spread': Decimal('0.0075'),  # 75 bps spread
            'timestamp': datetime.now(),
            'maturity_date': datetime.now() + timedelta(days=1825),  # 5 years
            'coupon_rate': Decimal('0.035'),  # 3.5% coupon
            'face_value': Decimal('100')
        }
    
    def _get_commodity_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for commodity instruments."""
        # Mock commodity data
        return {
            'symbol': symbol,
            'asset_class': 'commodity',
            'price': Decimal('75.50'),
            'bid_price': Decimal('75.45'),
            'ask_price': Decimal('75.55'),
            'volume': 50000,
            'timestamp': datetime.now(),
            'contract_month': 'Dec2024',
            'storage_cost': Decimal('0.02'),  # 2% storage cost
            'convenience_yield': Decimal('0.015'),  # 1.5% convenience yield
            'spot_price': Decimal('74.80')
        }
    
    def _get_mock_equity_data(self, symbol: str) -> Dict[str, Any]:
        """Generate mock equity data for testing."""
        # Generate realistic mock data based on symbol
        base_price = hash(symbol) % 200 + 50  # Price between 50-250
        
        return {
            'symbol': symbol,
            'asset_class': 'equity',
            'price': Decimal(str(base_price)),
            'bid_price': Decimal(str(base_price * 0.999)),
            'ask_price': Decimal(str(base_price * 1.001)),
            'volume': (hash(symbol) % 10000000) + 100000,  # Volume between 100K-10M
            'timestamp': datetime.now(),
            'sector': 'Technology',
            'market_cap': Decimal(str((hash(symbol) % 500) + 10)) * Decimal('1000000000'),  # 10B-510B
            'beta': Decimal(str(0.8 + (hash(symbol) % 100) / 100.0)),  # Beta between 0.8-1.8
            'dividend_yield': Decimal(str((hash(symbol) % 40) / 1000.0))  # 0-4% dividend yield
        }
    
    def get_historical_data(self, symbol: str, start_date: datetime, 
                           end_date: datetime, asset_class: str = 'equity') -> pd.DataFrame:
        """
        Get historical market data for a symbol.
        
        Args:
            symbol: Instrument symbol
            start_date: Start date for data
            end_date: End date for data
            asset_class: Asset class
            
        Returns:
            DataFrame with historical data
        """
        try:
            self.logger.info(f"Loading historical data for {symbol} from {start_date} to {end_date}")
            
            # Generate mock historical data for now
            # In a real implementation, this would query historical data tables
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Generate realistic price series
            base_price = hash(symbol) % 200 + 50
            returns = np.random.normal(0, 0.02, len(date_range))  # 2% daily volatility
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Create DataFrame
            df = pd.DataFrame({
                'date': date_range,
                'open': [p * np.random.uniform(0.995, 1.005) for p in prices],
                'high': [p * np.random.uniform(1.001, 1.02) for p in prices],
                'low': [p * np.random.uniform(0.98, 0.999) for p in prices],
                'close': prices,
                'volume': [np.random.randint(100000, 10000000) for _ in prices],
                'symbol': symbol
            })
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_yield_curve_data(self, curve_type: str = 'USD', date: datetime = None) -> Dict[str, Any]:
        """
        Get yield curve data for fixed income pricing.
        
        Args:
            curve_type: Type of curve (USD, EUR, GBP, etc.)
            date: Date for curve data (defaults to today)
            
        Returns:
            Yield curve data dictionary
        """
        if date is None:
            date = datetime.now().date()
        
        cache_key = f"yield_curve_{curve_type}_{date}"
        
        # Check cache
        if cache_key in self.curve_data_cache:
            cached_data = self.curve_data_cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < 3600:  # 1 hour cache
                return cached_data['data']
        
        # Mock yield curve data
        tenors = ['1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '20Y', '30Y']
        base_rates = {
            'USD': [0.05, 0.055, 0.058, 0.062, 0.065, 0.070, 0.075, 0.078, 0.080],
            'EUR': [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.032, 0.035],
            'GBP': [0.04, 0.045, 0.048, 0.052, 0.055, 0.060, 0.065, 0.068, 0.070]
        }
        
        rates = base_rates.get(curve_type, base_rates['USD'])
        
        curve_data = {
            'curve_type': curve_type,
            'date': date.isoformat(),
            'tenors': tenors,
            'rates': rates,
            'interpolation_method': 'cubic_spline',
            'timestamp': datetime.now()
        }
        
        # Cache the data
        self.curve_data_cache[cache_key] = {
            'data': curve_data,
            'timestamp': datetime.now()
        }
        
        return curve_data
    
    def get_volatility_surface(self, underlying: str, asset_class: str = 'equity') -> Dict[str, Any]:
        """
        Get volatility surface data for options pricing.
        
        Args:
            underlying: Underlying instrument symbol
            asset_class: Asset class
            
        Returns:
            Volatility surface data
        """
        cache_key = f"vol_surface_{underlying}_{asset_class}"
        
        # Check cache
        if cache_key in self.volatility_cache:
            cached_data = self.volatility_cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < 1800:  # 30 min cache
                return cached_data['data']
        
        # Mock volatility surface
        strikes = [90, 95, 100, 105, 110]  # Strike levels relative to spot
        maturities = [30, 60, 90, 180, 365]  # Days to expiration
        
        # Generate volatility surface (smile/skew pattern)
        vol_surface = {}
        base_vol = 0.20  # 20% base volatility
        
        for maturity in maturities:
            vol_surface[f"{maturity}D"] = {}
            for strike in strikes:
                # Create volatility smile pattern
                moneyness = strike / 100.0  # ATM = 1.0
                skew_adjustment = 0.05 * (1 - moneyness)  # Put skew
                time_adjustment = 0.02 * np.sqrt(maturity / 365.0)  # Term structure
                
                vol = base_vol + skew_adjustment + time_adjustment
                vol_surface[f"{maturity}D"][f"{strike}%"] = vol
        
        surface_data = {
            'underlying': underlying,
            'asset_class': asset_class,
            'surface': vol_surface,
            'strikes': strikes,
            'maturities': maturities,
            'timestamp': datetime.now()
        }
        
        # Cache the data
        self.volatility_cache[cache_key] = {
            'data': surface_data,
            'timestamp': datetime.now()
        }
        
        return surface_data
    
    def get_corporate_actions(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get corporate actions data for a symbol.
        
        Args:
            symbol: Instrument symbol
            start_date: Start date for actions
            end_date: End date for actions
            
        Returns:
            List of corporate actions
        """
        # Mock corporate actions data
        actions = []
        
        # Generate some mock dividend payments
        current_date = start_date
        while current_date <= end_date:
            if current_date.month % 3 == 0:  # Quarterly dividends
                actions.append({
                    'symbol': symbol,
                    'action_type': 'dividend',
                    'ex_date': current_date.isoformat(),
                    'amount': Decimal('0.50'),
                    'currency': 'USD',
                    'timestamp': datetime.now().isoformat()
                })
            current_date += timedelta(days=30)
        
        return actions
    
    def clear_cache(self):
        """Clear all cached data."""
        self.market_data_cache.clear()
        self.curve_data_cache.clear()
        self.volatility_cache.clear()
        self.logger.info("Data caches cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'market_data_entries': len(self.market_data_cache),
            'curve_data_entries': len(self.curve_data_cache),
            'volatility_entries': len(self.volatility_cache)
        }