"""
IBKR Company Share Option Heston Price Factor Repository - Retrieval and creation of company share option Heston price factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_price_factor import CompanyShareOptionHestonPriceFactor
from src.domain.ports.factor.company_share_option_heston_price_factor_port import CompanyShareOptionHestonPriceFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareOptionHestonPriceFactorRepository(BaseIBKRFactorRepository, CompanyShareOptionHestonPriceFactorPort):
    """
    IBKR implementation for CompanyShareOption Heston price factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Company Share Option Heston Price Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('company_share_option_heston_price_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create a company share option Heston price factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "option")
            subgroup: Factor subgroup (default: "company")
            
        Returns:
            CompanyShareOptionHestonPriceFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific option data
            enhanced_kwargs = self._enhance_with_ibkr_option_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create company share option Heston price factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for company share option Heston price factor {name}: {e}")
            return None

    def _enhance_with_ibkr_option_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific option data for company shares using Heston model.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with Heston specific metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Company Share Option Heston Price factor: {primary_key}'
        
        # Add option-specific metadata
        if 'option_type' not in enhanced:
            enhanced['option_type'] = self._infer_option_type(primary_key)
        
        if 'underlying_symbol' not in enhanced:
            enhanced['underlying_symbol'] = self._infer_underlying_symbol(primary_key)
        
        if 'strike_price' not in enhanced:
            enhanced['strike_price'] = self._infer_strike_price(primary_key)
            
        if 'expiration_date' not in enhanced:
            enhanced['expiration_date'] = self._infer_expiration_date(primary_key)
        
        # Add Heston model-specific parameters
        enhanced['pricing_model'] = 'heston'
        enhanced['volatility_source'] = enhanced.get('volatility_source', 'stochastic')
        enhanced['dividend_yield_handling'] = enhanced.get('dividend_yield_handling', 'continuous')
        enhanced['risk_free_rate_source'] = enhanced.get('risk_free_rate_source', 'treasury')
        
        # Heston stochastic volatility model specific enhancements
        enhanced['initial_variance'] = enhanced.get('initial_variance', 0.04)
        enhanced['long_run_variance'] = enhanced.get('long_run_variance', 0.04)
        enhanced['variance_mean_reversion_speed'] = enhanced.get('variance_mean_reversion_speed', 2.0)
        enhanced['volatility_of_variance'] = enhanced.get('volatility_of_variance', 0.3)
        enhanced['correlation_spot_variance'] = enhanced.get('correlation_spot_variance', -0.7)
        
        # Model calibration and numerical methods
        enhanced['calibration_method'] = enhanced.get('calibration_method', 'characteristic_function')
        enhanced['integration_method'] = enhanced.get('integration_method', 'gauss_laguerre')
        enhanced['fourier_transform_method'] = enhanced.get('fourier_transform_method', 'carr_madan')
        enhanced['monte_carlo_paths'] = enhanced.get('monte_carlo_paths', 100000)
        enhanced['time_discretization'] = enhanced.get('time_discretization', 'euler_milstein')
        
        # Advanced Heston model features
        enhanced['variance_process_boundary'] = enhanced.get('variance_process_boundary', 'absorption')
        enhanced['jumps_in_returns'] = enhanced.get('jumps_in_returns', False)
        enhanced['jumps_in_variance'] = enhanced.get('jumps_in_variance', False)
        enhanced['stochastic_interest_rates'] = enhanced.get('stochastic_interest_rates', False)
        
        return enhanced

    def _infer_option_type(self, factor_name: str) -> str:
        """
        Infer option type (call/put) from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Option type ('call' or 'put')
        """
        factor_upper = factor_name.upper()
        
        if 'PUT' in factor_upper:
            return 'put'
        elif 'CALL' in factor_upper:
            return 'call'
        else:
            return 'call'  # Default to call option

    def _infer_underlying_symbol(self, factor_name: str) -> Optional[str]:
        """
        Infer underlying stock symbol from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Stock symbol or None if cannot be inferred
        """
        import re
        
        factor_upper = factor_name.upper()
        
        # Common stock patterns - look for stock symbols (3-5 letter patterns)
        symbol_patterns = re.findall(r'\b[A-Z]{2,5}\b', factor_upper)
        
        if symbol_patterns:
            # Filter out common words that might match the pattern
            common_words = {'OPTION', 'CALL', 'PUT', 'PRICE', 'RETURN', 'DELTA', 'GAMMA', 'THETA', 'VEGA', 'RHO', 'HESTON'}
            for pattern in symbol_patterns:
                if pattern not in common_words:
                    return pattern
        
        return None

    def _infer_strike_price(self, factor_name: str) -> Optional[float]:
        """
        Infer strike price from factor name if present.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Strike price as float or None if cannot be inferred
        """
        import re
        
        # Look for numeric patterns that might be strike prices
        price_patterns = re.findall(r'(\d+\.?\d*)', factor_name)
        
        if price_patterns:
            try:
                # Return the first numeric value found as potential strike
                return float(price_patterns[0])
            except ValueError:
                pass
        
        return None

    def _infer_expiration_date(self, factor_name: str) -> Optional[str]:
        """
        Infer expiration date from factor name if present.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Expiration date as string or None if cannot be inferred
        """
        import re
        
        # Look for date patterns (YYYY-MM-DD, MM/DD/YYYY, etc.)
        date_patterns = re.findall(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})', factor_name)
        
        if date_patterns:
            return date_patterns[0]
        
        # Look for expiration month patterns (JAN, FEB, etc.)
        months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        factor_upper = factor_name.upper()
        
        for month in months:
            if month in factor_upper:
                # Try to find year pattern near the month
                year_patterns = re.findall(r'(\d{4}|\d{2})', factor_name)
                if year_patterns:
                    return f"{month}_{year_patterns[0]}"
        
        return None

    # Port interface implementation - delegated to local repository
    def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareOptionHestonPriceFactor) -> Optional[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareOptionHestonPriceFactor) -> Optional[CompanyShareOptionHestonPriceFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False