"""
IBKR ETF Share Portfolio Company Share Option Factor Repository - Retrieval and creation of ETF share portfolio company share option factors via IBKR.
"""

from typing import Optional, List
from src.domain.ports.factor.etf_share_portfolio_company_share_option_factor_port import ETFSharePortfolioCompanyShareOptionFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRETFSharePortfolioCompanyShareOptionFactorRepository(BaseIBKRFactorRepository, ETFSharePortfolioCompanyShareOptionFactorPort):
    """
    IBKR implementation for EtfSharePortfolioCompanyShareOption factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR ETF Share Portfolio Company Share Option Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('etf_share_portfolio_company_share_option_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an ETF share portfolio company share option factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "option")
            subgroup: Factor subgroup (default: "etf_portfolio")
            
        Returns:
            EtfSharePortfolioCompanyShareOptionFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific option data
            enhanced_kwargs = self._enhance_with_ibkr_option_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create ETF share portfolio company share option factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for ETF share portfolio company share option factor {name}: {e}")
            return None

    def _enhance_with_ibkr_option_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific option data for ETF share portfolios.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with option metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR ETF Share Portfolio Company Share Option factor: {primary_key}'
        
        # Add option-specific metadata
        if 'option_type' not in enhanced:
            enhanced['option_type'] = self._infer_option_type(primary_key)
        
        if 'underlying_etf' not in enhanced:
            enhanced['underlying_etf'] = self._infer_underlying_etf(primary_key)
        
        if 'strike_price' not in enhanced:
            enhanced['strike_price'] = self._infer_strike_price(primary_key)
            
        if 'expiration_date' not in enhanced:
            enhanced['expiration_date'] = self._infer_expiration_date(primary_key)
        
        # Add ETF portfolio-specific option calculation metadata
        enhanced['etf_weighting_method'] = enhanced.get('etf_weighting_method', 'market_cap')
        enhanced['underlying_portfolio_correlation'] = enhanced.get('underlying_portfolio_correlation', True)
        enhanced['etf_tracking_error_adjustment'] = enhanced.get('etf_tracking_error_adjustment', True)
        enhanced['creation_redemption_impact'] = enhanced.get('creation_redemption_impact', True)
        enhanced['nav_premium_discount_adjustment'] = enhanced.get('nav_premium_discount_adjustment', True)
        enhanced['volatility_source'] = enhanced.get('volatility_source', 'implied')
        enhanced['dividend_yield_handling'] = enhanced.get('dividend_yield_handling', 'etf_weighted')
        enhanced['rebalancing_frequency'] = enhanced.get('rebalancing_frequency', 'daily')
        enhanced['risk_free_rate_source'] = enhanced.get('risk_free_rate_source', 'treasury')
        enhanced['liquidity_adjustment'] = enhanced.get('liquidity_adjustment', True)
        
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

    def _infer_underlying_etf(self, factor_name: str) -> Optional[str]:
        """
        Infer underlying ETF symbol from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            ETF symbol or None if cannot be inferred
        """
        factor_upper = factor_name.upper()
        
        # Common ETF patterns
        if 'SPY' in factor_upper:
            return 'SPY'
        elif 'QQQ' in factor_upper:
            return 'QQQ'
        elif 'IWM' in factor_upper:
            return 'IWM'
        elif 'XLF' in factor_upper:
            return 'XLF'
        elif 'XLE' in factor_upper:
            return 'XLE'
        elif 'XLK' in factor_upper:
            return 'XLK'
        elif 'XLV' in factor_upper:
            return 'XLV'
        elif 'REIT' in factor_upper:
            return 'VNQ'
        elif 'BOND' in factor_upper:
            return 'BND'
        elif 'GOLD' in factor_upper:
            return 'GLD'
        elif 'VIX' in factor_upper:
            return 'VXX'
        else:
            return 'SPY'  # Default to SPY

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
    def get_by_id(self, entity_id: int):
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str):
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str):
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str):
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self):
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity):
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity):
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False