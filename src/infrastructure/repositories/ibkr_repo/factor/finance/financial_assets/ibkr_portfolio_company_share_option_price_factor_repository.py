"""
IBKR Portfolio Company Share Option Price Factor Repository - Retrieval and creation of portfolio company share option price factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_factor import PortfolioCompanyShareOptionPriceFactor
from src.domain.ports.factor.portfolio_company_share_option_price_factor_port import PortfolioCompanyShareOptionPriceFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRPortfolioCompanyShareOptionPriceFactorRepository(BaseIBKRFactorRepository, PortfolioCompanyShareOptionPriceFactorPort):
    """
    IBKR implementation for PortfolioCompanyShareOptionPrice factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Portfolio Company Share Option Price Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('portfolio_company_share_option_price_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create a portfolio company share option price factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "price")
            subgroup: Factor subgroup (default: "option")
            
        Returns:
            PortfolioCompanyShareOptionPriceFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific pricing data
            enhanced_kwargs = self._enhance_with_ibkr_pricing_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create portfolio company share option price factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share option price factor {name}: {e}")
            return None

    def _enhance_with_ibkr_pricing_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific pricing data for portfolio company shares.
        
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
            enhanced['definition'] = f'IBKR Portfolio Company Share Option Price factor: {primary_key}'
        
        # Add pricing-specific metadata
        if 'pricing_model' not in enhanced:
            enhanced['pricing_model'] = 'black_scholes'
        
        if 'price_type' not in enhanced:
            enhanced['price_type'] = self._infer_price_type(primary_key)
        
        # Add underlying portfolio mapping if not provided
        if 'underlying_portfolio' not in enhanced:
            enhanced['underlying_portfolio'] = self._infer_underlying_portfolio(primary_key)
        
        # Add option-specific pricing attributes
        if 'option_type' not in enhanced:
            enhanced['option_type'] = self._infer_option_type(primary_key)
            
        if 'strike_price' not in enhanced:
            enhanced['strike_price'] = self._infer_strike_price(primary_key)
        
        # Add portfolio-specific pricing calculation metadata
        enhanced['calculation_frequency'] = enhanced.get('calculation_frequency', 'real_time')
        enhanced['volatility_source'] = enhanced.get('volatility_source', 'implied')
        enhanced['interest_rate_source'] = enhanced.get('interest_rate_source', 'risk_free')
        enhanced['portfolio_correlation_model'] = enhanced.get('portfolio_correlation_model', 'historical')
        enhanced['dividend_yield_handling'] = enhanced.get('dividend_yield_handling', 'portfolio_weighted')
        
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

    def _infer_underlying_portfolio(self, factor_name: str) -> Optional[str]:
        """
        Infer underlying portfolio symbol from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Portfolio symbol or None if cannot be inferred
        """
        factor_upper = factor_name.upper()
        
        # Common portfolio patterns
        if 'TECH' in factor_upper:
            return 'TECH_PORTFOLIO'
        elif 'HEALTHCARE' in factor_upper or 'HEALTH' in factor_upper:
            return 'HEALTH_PORTFOLIO'
        elif 'ENERGY' in factor_upper:
            return 'ENERGY_PORTFOLIO'
        elif 'FINANCE' in factor_upper or 'FINANCIAL' in factor_upper:
            return 'FINANCIAL_PORTFOLIO'
        elif 'REIT' in factor_upper:
            return 'REIT_PORTFOLIO'
        elif 'GROWTH' in factor_upper:
            return 'GROWTH_PORTFOLIO'
        elif 'VALUE' in factor_upper:
            return 'VALUE_PORTFOLIO'
        elif 'DIVIDEND' in factor_upper:
            return 'DIVIDEND_PORTFOLIO'
        elif 'SP500' in factor_upper or 'S&P500' in factor_upper:
            return 'SP500_PORTFOLIO'
        else:
            return 'MIXED_PORTFOLIO'  # Default portfolio type

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
    def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: PortfolioCompanyShareOptionPriceFactor) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: PortfolioCompanyShareOptionPriceFactor) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False