"""
IBKR Index Future Option Delta Factor Repository - Retrieval and creation of index future option delta factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_delta_factor import IndexFutureOptionDeltaFactor
from src.domain.ports.factor.index_future_option_delta_factor_port import IndexFutureOptionDeltaFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRIndexFutureOptionDeltaFactorRepository(BaseIBKRFactorRepository, IndexFutureOptionDeltaFactorPort):
    """
    IBKR implementation for IndexFutureOptionDelta factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Index Future Option Delta Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('index_future_option_delta_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an index future option delta factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "greeks")
            subgroup: Factor subgroup (default: "delta")
            
        Returns:
            IndexFutureOptionDeltaFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific delta calculation data
            enhanced_kwargs = self._enhance_with_ibkr_delta_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create index future option delta factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for index future option delta factor {name}: {e}")
            return None

    def _enhance_with_ibkr_delta_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific delta calculation data.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with delta calculation metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Index Future Option Delta factor: {primary_key}'
        
        # Add delta calculation specific metadata
        if 'delta_type' not in enhanced:
            enhanced['delta_type'] = self._infer_delta_type(primary_key)
        
        if 'calculation_model' not in enhanced:
            enhanced['calculation_model'] = self._infer_calculation_model(primary_key)
        
        if 'hedge_ratio_type' not in enhanced:
            enhanced['hedge_ratio_type'] = self._infer_hedge_ratio_type(primary_key)
        
        # Add underlying index mapping if not provided
        if 'underlying_index' not in enhanced:
            enhanced['underlying_index'] = self._infer_underlying_index(primary_key)
        
        # Add option-specific delta attributes
        if 'option_type' not in enhanced:
            enhanced['option_type'] = self._infer_option_type(primary_key)
            
        if 'strike_price' not in enhanced:
            enhanced['strike_price'] = self._infer_strike_price(primary_key)
        
        # Add delta calculation metadata
        enhanced['volatility_surface_enabled'] = enhanced.get('volatility_surface_enabled', True)
        enhanced['time_decay_adjustment'] = enhanced.get('time_decay_adjustment', True)
        enhanced['interest_rate_sensitivity'] = enhanced.get('interest_rate_sensitivity', True)
        enhanced['dividend_adjustment'] = enhanced.get('dividend_adjustment', True)
        
        return enhanced

    def _infer_delta_type(self, factor_name: str) -> str:
        """
        Infer delta calculation type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Delta type (spot, forward, normalized, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'SPOT' in factor_upper and 'DELTA' in factor_upper:
            return 'spot'
        elif 'FORWARD' in factor_upper and 'DELTA' in factor_upper:
            return 'forward'
        elif 'NORMALIZED' in factor_upper or 'NORM' in factor_upper:
            return 'normalized'
        elif 'EFFECTIVE' in factor_upper:
            return 'effective'
        elif 'HEDGE' in factor_upper and 'DELTA' in factor_upper:
            return 'hedge'
        else:
            return 'spot'  # Default to spot delta

    def _infer_calculation_model(self, factor_name: str) -> str:
        """
        Infer calculation model from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Calculation model (black_scholes, binomial, monte_carlo, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'BLACK' in factor_upper and 'SCHOLES' in factor_upper:
            return 'black_scholes'
        elif 'BINOMIAL' in factor_upper:
            return 'binomial'
        elif 'MONTE' in factor_upper and 'CARLO' in factor_upper:
            return 'monte_carlo'
        elif 'FINITE' in factor_upper and 'DIFFERENCE' in factor_upper:
            return 'finite_difference'
        elif 'HESTON' in factor_upper:
            return 'heston'
        else:
            return 'black_scholes'  # Default to Black-Scholes

    def _infer_hedge_ratio_type(self, factor_name: str) -> str:
        """
        Infer hedge ratio type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Hedge ratio type (simple, risk_adjusted, dollar_neutral, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'DOLLAR' in factor_upper and 'NEUTRAL' in factor_upper:
            return 'dollar_neutral'
        elif 'RISK' in factor_upper and 'ADJUSTED' in factor_upper:
            return 'risk_adjusted'
        elif 'BETA' in factor_upper and 'ADJUSTED' in factor_upper:
            return 'beta_adjusted'
        elif 'VOLATILITY' in factor_upper and 'WEIGHTED' in factor_upper:
            return 'volatility_weighted'
        elif 'SIMPLE' in factor_upper:
            return 'simple'
        else:
            return 'simple'  # Default to simple hedge ratio

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
        # E.g., "ES_4200_CALL_DELTA" -> 4200
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

    def calculate_option_delta(self, option_symbol: str, **calculation_params) -> Optional[float]:
        """
        Calculate option delta using IBKR pricing models.
        
        Args:
            option_symbol: Option symbol
            **calculation_params: Delta calculation parameters (spot_price, volatility, etc.)
            
        Returns:
            Calculated delta if available
        """
        try:
            # This would integrate with IBKR's option pricing/greeks calculation
            # For now, return None as placeholder
            print(f"Delta calculation for {option_symbol} - placeholder")
            return None
            
        except Exception as e:
            print(f"Error calculating delta for {option_symbol}: {e}")
            return None

    def get_real_time_delta(self, option_symbol: str) -> Optional[float]:
        """
        Get real-time option delta from IBKR API.
        
        Args:
            option_symbol: Option symbol
            
        Returns:
            Real-time delta if available
        """
        try:
            # This would integrate with IBKR's real-time greeks data
            # For now, return None as placeholder
            print(f"Real-time delta request for {option_symbol} - placeholder")
            return None
            
        except Exception as e:
            print(f"Error getting real-time delta for {option_symbol}: {e}")
            return None

    def calculate_hedge_ratio(self, option_symbol: str, hedge_type: str = 'simple') -> Optional[float]:
        """
        Calculate hedge ratio for option position.
        
        Args:
            option_symbol: Option symbol
            hedge_type: Type of hedge ratio calculation
            
        Returns:
            Calculated hedge ratio if available
        """
        try:
            # This would calculate various hedge ratios using delta and other factors
            # For now, return None as placeholder
            print(f"Hedge ratio calculation for {option_symbol} ({hedge_type}) - placeholder")
            return None
            
        except Exception as e:
            print(f"Error calculating hedge ratio for {option_symbol}: {e}")
            return None

    def get_delta_sensitivity_analysis(self, option_symbol: str) -> Optional[dict]:
        """
        Get delta sensitivity analysis (delta vs spot, time, volatility).
        
        Args:
            option_symbol: Option symbol
            
        Returns:
            Dictionary with sensitivity analysis data
        """
        try:
            # This would perform comprehensive delta sensitivity analysis
            # For now, return None as placeholder
            print(f"Delta sensitivity analysis for {option_symbol} - placeholder")
            return None
            
        except Exception as e:
            print(f"Error getting delta sensitivity for {option_symbol}: {e}")
            return None

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionDeltaFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[IndexFutureOptionDeltaFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_all(self) -> List[IndexFutureOptionDeltaFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: IndexFutureOptionDeltaFactor) -> Optional[IndexFutureOptionDeltaFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: IndexFutureOptionDeltaFactor) -> Optional[IndexFutureOptionDeltaFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False