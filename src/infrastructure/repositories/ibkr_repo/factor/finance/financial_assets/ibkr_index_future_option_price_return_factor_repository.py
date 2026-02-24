"""
IBKR Index Future Option Price Return Factor Repository - Retrieval and creation of index future option price return factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_price_return_factor import IndexFutureOptionPriceReturnFactor
from src.domain.ports.factor.index_future_option_price_return_factor_port import IndexFutureOptionPriceReturnFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRIndexFutureOptionPriceReturnFactorRepository(BaseIBKRFactorRepository, IndexFutureOptionPriceReturnFactorPort):
    """
    IBKR implementation for IndexFutureOptionPriceReturn factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Index Future Option Price Return Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('index_future_option_price_return_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an index future option price return factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "return")
            subgroup: Factor subgroup (default: "option")
            
        Returns:
            IndexFutureOptionPriceReturnFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific return calculation data
            enhanced_kwargs = self._enhance_with_ibkr_return_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create index future option price return factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for index future option price return factor {name}: {e}")
            return None

    def _enhance_with_ibkr_return_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific return calculation data.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with return calculation metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Index Future Option Price Return factor: {primary_key}'
        
        # Add return calculation specific metadata
        if 'return_type' not in enhanced:
            enhanced['return_type'] = self._infer_return_type(primary_key)
        
        if 'calculation_period' not in enhanced:
            enhanced['calculation_period'] = self._infer_calculation_period(primary_key)
        
        if 'adjustment_type' not in enhanced:
            enhanced['adjustment_type'] = self._infer_adjustment_type(primary_key)
        
        # Add underlying index mapping if not provided
        if 'underlying_index' not in enhanced:
            enhanced['underlying_index'] = self._infer_underlying_index(primary_key)
        
        # Add option-specific return attributes
        if 'option_type' not in enhanced:
            enhanced['option_type'] = self._infer_option_type(primary_key)
            
        if 'strike_price' not in enhanced:
            enhanced['strike_price'] = self._infer_strike_price(primary_key)
        
        # Add return calculation metadata
        enhanced['volatility_adjusted'] = enhanced.get('volatility_adjusted', False)
        enhanced['dividend_adjusted'] = enhanced.get('dividend_adjusted', True)
        enhanced['split_adjusted'] = enhanced.get('split_adjusted', True)
        enhanced['time_weighted'] = enhanced.get('time_weighted', False)
        
        return enhanced

    def _infer_return_type(self, factor_name: str) -> str:
        """
        Infer return calculation type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Return type (simple, log, volatility_adjusted, sharpe, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'LOG' in factor_upper and 'RETURN' in factor_upper:
            return 'log'
        elif 'SIMPLE' in factor_upper and 'RETURN' in factor_upper:
            return 'simple'
        elif 'VOLATILITY' in factor_upper and 'ADJUSTED' in factor_upper:
            return 'volatility_adjusted'
        elif 'SHARPE' in factor_upper:
            return 'sharpe'
        elif 'EXCESS' in factor_upper:
            return 'excess'
        elif 'TOTAL' in factor_upper:
            return 'total'
        elif 'CUMULATIVE' in factor_upper:
            return 'cumulative'
        else:
            return 'simple'  # Default to simple return

    def _infer_calculation_period(self, factor_name: str) -> str:
        """
        Infer calculation period from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Calculation period (daily, weekly, monthly, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'DAILY' in factor_upper or '_1D_' in factor_upper:
            return 'daily'
        elif 'WEEKLY' in factor_upper or '_1W_' in factor_upper:
            return 'weekly'
        elif 'MONTHLY' in factor_upper or '_1M_' in factor_upper:
            return 'monthly'
        elif 'QUARTERLY' in factor_upper or '_3M_' in factor_upper:
            return 'quarterly'
        elif 'YEARLY' in factor_upper or 'ANNUAL' in factor_upper:
            return 'yearly'
        elif 'INTRADAY' in factor_upper:
            return 'intraday'
        else:
            return 'daily'  # Default to daily

    def _infer_adjustment_type(self, factor_name: str) -> str:
        """
        Infer adjustment type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Adjustment type (none, dividend, split, both)
        """
        factor_upper = factor_name.upper()
        
        if 'UNADJUSTED' in factor_upper or 'RAW' in factor_upper:
            return 'none'
        elif 'DIVIDEND' in factor_upper and 'SPLIT' in factor_upper:
            return 'both'
        elif 'DIVIDEND' in factor_upper:
            return 'dividend'
        elif 'SPLIT' in factor_upper:
            return 'split'
        else:
            return 'both'  # Default to both adjustments

    def _infer_underlying_index(self, factor_name: str) -> Optional[str]:
        """
        Infer underlying index from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Underlying index symbol if determinable
        """
        # Simple heuristics - could be enhanced with IBKR contract lookup
        if 'ES' in factor_name.upper():
            return 'SPX'
        elif 'NQ' in factor_name.upper():
            return 'NDX'
        elif 'RTY' in factor_name.upper():
            return 'RUT'
        elif 'YM' in factor_name.upper():
            return 'DJI'
        
        return None

    def _infer_option_type(self, factor_name: str) -> Optional[str]:
        """
        Infer option type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Option type ('call', 'put') if determinable
        """
        factor_upper = factor_name.upper()
        if 'CALL' in factor_upper or '_C_' in factor_upper:
            return 'call'
        elif 'PUT' in factor_upper or '_P_' in factor_upper:
            return 'put'
        
        return None

    def _infer_strike_price(self, factor_name: str) -> Optional[float]:
        """
        Infer strike price from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Strike price if determinable from name pattern
        """
        import re
        
        # Look for numeric patterns that might represent strike prices
        # E.g., "ES_4200_CALL_RETURN" -> 4200
        strike_patterns = [
            r'_(\d+)_',  # Underscore-separated number
            r'(\d{3,5})',  # 3-5 digit number (typical strike range)
        ]
        
        for pattern in strike_patterns:
            match = re.search(pattern, factor_name)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None

    def calculate_option_return(self, option_symbol: str, start_date: str, end_date: str, return_type: str = 'simple') -> Optional[float]:
        """
        Calculate option return over specified period using IBKR data.
        
        Args:
            option_symbol: Option symbol
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            return_type: Type of return calculation
            
        Returns:
            Calculated return if available
        """
        try:
            # This would integrate with IBKR's historical data API
            # For now, return None as placeholder
            print(f"Return calculation for {option_symbol} from {start_date} to {end_date} ({return_type}) - placeholder")
            return None
            
        except Exception as e:
            print(f"Error calculating return for {option_symbol}: {e}")
            return None

    def get_return_statistics(self, option_symbol: str, period_days: int = 252) -> Optional[dict]:
        """
        Get return statistics for option over specified period.
        
        Args:
            option_symbol: Option symbol
            period_days: Number of days for statistics calculation
            
        Returns:
            Dictionary with return statistics (mean, std, sharpe, etc.)
        """
        try:
            # This would calculate various return statistics using IBKR data
            # For now, return None as placeholder
            print(f"Return statistics for {option_symbol} over {period_days} days - placeholder")
            return None
            
        except Exception as e:
            print(f"Error getting return statistics for {option_symbol}: {e}")
            return None

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_all(self) -> List[IndexFutureOptionPriceReturnFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: IndexFutureOptionPriceReturnFactor) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: IndexFutureOptionPriceReturnFactor) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False