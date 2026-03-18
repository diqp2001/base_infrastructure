"""
IBKR Company Share Option Price Factor Repository - Retrieval and creation of company share option price factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_factor import CompanyShareOptionPriceFactor
from src.domain.ports.factor.company_share_option_price_factor_port import CompanyShareOptionPriceFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareOptionPriceFactorRepository(BaseIBKRFactorRepository, CompanyShareOptionPriceFactorPort):
    """
    IBKR implementation for CompanyShareOptionPrice factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Company Share Option Price Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('company_share_option_price_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create a company share option price factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "price")
            subgroup: Factor subgroup (default: "company_option")
            
        Returns:
            CompanyShareOptionPriceFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific pricing data
            enhanced_kwargs = self._enhance_with_ibkr_pricing_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create company share option price factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for company share option price factor {name}: {e}")
            return None

    def _enhance_with_ibkr_pricing_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific pricing data for company shares.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with pricing metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Company Share Option Price factor: {primary_key}'
        
        # Add pricing-specific metadata
        if 'pricing_model' not in enhanced:
            enhanced['pricing_model'] = 'black_scholes'
        
        if 'price_type' not in enhanced:
            enhanced['price_type'] = self._infer_price_type(primary_key)
        
        # Add underlying company mapping if not provided
        if 'underlying_symbol' not in enhanced:
            enhanced['underlying_symbol'] = self._infer_underlying_symbol(primary_key)
        
        # Add option-specific pricing attributes
        if 'option_type' not in enhanced:
            enhanced['option_type'] = self._infer_option_type(primary_key)
            
        if 'strike_price' not in enhanced:
            enhanced['strike_price'] = self._infer_strike_price(primary_key)
        
        # Add company-specific pricing calculation metadata
        enhanced['calculation_frequency'] = enhanced.get('calculation_frequency', 'real_time')
        enhanced['volatility_source'] = enhanced.get('volatility_source', 'implied')
        enhanced['interest_rate_source'] = enhanced.get('interest_rate_source', 'risk_free')
        enhanced['dividend_yield_handling'] = enhanced.get('dividend_yield_handling', 'continuous')
        enhanced['earnings_adjustment'] = enhanced.get('earnings_adjustment', True)
        enhanced['after_hours_pricing'] = enhanced.get('after_hours_pricing', False)
        enhanced['bid_ask_spread_modeling'] = enhanced.get('bid_ask_spread_modeling', 'dynamic')
        enhanced['liquidity_premium_adjustment'] = enhanced.get('liquidity_premium_adjustment', True)
        
        return enhanced

    def _infer_price_type(self, factor_name: str) -> str:
        """
        Infer price type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Price type (bid, ask, mid, theoretical, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'BID' in factor_upper:
            return 'bid'
        elif 'ASK' in factor_upper:
            return 'ask'
        elif 'MID' in factor_upper:
            return 'mid'
        elif 'THEO' in factor_upper or 'THEORETICAL' in factor_upper:
            return 'theoretical'
        elif 'MARK' in factor_upper:
            return 'mark'
        elif 'LAST' in factor_upper:
            return 'last'
        else:
            return 'mid'  # Default to mid price

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
            common_words = {'PRICE', 'CALL', 'PUT', 'OPTION', 'RETURN', 'DELTA', 'GAMMA', 'THETA', 'VEGA', 'RHO'}
            for pattern in symbol_patterns:
                if pattern not in common_words:
                    return pattern
        
        return None

    def _infer_option_type(self, factor_name: str) -> str:
        """
        Infer option type (call/put) from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Option type ('call' or 'put')
        """
        factor_upper = factor_name.upper()
        
        if 'PUT' in factor_upper or 'P' in factor_upper.split('_')[-1:]:
            return 'put'
        elif 'CALL' in factor_upper or 'C' in factor_upper.split('_')[-1:]:
            return 'call'
        else:
            return 'call'  # Default to call option

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

    # Port interface implementation - delegated to local repository
    def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[CompanyShareOptionPriceFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareOptionPriceFactor) -> Optional[CompanyShareOptionPriceFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareOptionPriceFactor) -> Optional[CompanyShareOptionPriceFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False