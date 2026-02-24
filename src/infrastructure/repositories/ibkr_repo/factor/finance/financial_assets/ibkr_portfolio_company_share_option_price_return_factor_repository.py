"""
IBKR Portfolio Company Share Option Price Return Factor Repository - Retrieval and creation of portfolio company share option price return factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_return_factor import PortfolioCompanyShareOptionPriceReturnFactor
from src.domain.ports.factor.portfolio_company_share_option_price_return_factor_port import PortfolioCompanyShareOptionPriceReturnFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRPortfolioCompanyShareOptionPriceReturnFactorRepository(BaseIBKRFactorRepository, PortfolioCompanyShareOptionPriceReturnFactorPort):
    """
    IBKR implementation for PortfolioCompanyShareOptionPriceReturn factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Portfolio Company Share Option Price Return Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('portfolio_company_share_option_price_return_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create a portfolio company share option price return factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "price_return")
            subgroup: Factor subgroup (default: "option")
            
        Returns:
            PortfolioCompanyShareOptionPriceReturnFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific return calculation data
            enhanced_kwargs = self._enhance_with_ibkr_return_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create portfolio company share option price return factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share option price return factor {name}: {e}")
            return None

    def _enhance_with_ibkr_return_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific return calculation data for portfolio company shares.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with return calculation metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_calculated'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Portfolio Company Share Option Price Return factor: {primary_key}'
        
        # Add return-specific metadata
        if 'return_type' not in enhanced:
            enhanced['return_type'] = self._infer_return_type(primary_key)
        
        if 'calculation_method' not in enhanced:
            enhanced['calculation_method'] = self._infer_calculation_method(primary_key)
        
        # Add underlying portfolio mapping if not provided
        if 'underlying_portfolio' not in enhanced:
            enhanced['underlying_portfolio'] = self._infer_underlying_portfolio(primary_key)
        
        # Add time period specifications
        if 'time_period' not in enhanced:
            enhanced['time_period'] = self._infer_time_period(primary_key)
            
        if 'frequency' not in enhanced:
            enhanced['frequency'] = self._infer_frequency(primary_key)
        
        # Add portfolio-specific return calculation metadata
        enhanced['volatility_adjustment'] = enhanced.get('volatility_adjustment', True)
        enhanced['correlation_adjustment'] = enhanced.get('correlation_adjustment', True)
        enhanced['portfolio_rebalancing_impact'] = enhanced.get('portfolio_rebalancing_impact', True)
        enhanced['dividend_treatment'] = enhanced.get('dividend_treatment', 'reinvested')
        enhanced['benchmark_comparison'] = enhanced.get('benchmark_comparison', 'portfolio_weighted')
        
        return enhanced

    def _infer_return_type(self, factor_name: str) -> str:
        """
        Infer return type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Return type (simple, log, volatility_adjusted, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'LOG' in factor_upper:
            return 'log_return'
        elif 'VOLATILITY' in factor_upper:
            return 'volatility_adjusted'
        elif 'SHARPE' in factor_upper:
            return 'sharpe_ratio'
        elif 'CORRELATION' in factor_upper:
            return 'correlation_adjusted'
        elif 'EXCESS' in factor_upper:
            return 'excess_return'
        else:
            return 'simple_return'  # Default to simple return

    def _infer_calculation_method(self, factor_name: str) -> str:
        """
        Infer calculation method from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Calculation method
        """
        factor_upper = factor_name.upper()
        
        if 'WEIGHTED' in factor_upper:
            return 'portfolio_weighted'
        elif 'EQUAL' in factor_upper:
            return 'equal_weighted'
        elif 'CAP' in factor_upper:
            return 'market_cap_weighted'
        elif 'MOMENTUM' in factor_upper:
            return 'momentum_adjusted'
        else:
            return 'standard'  # Default calculation method

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

    def _infer_time_period(self, factor_name: str) -> str:
        """
        Infer time period from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Time period (1D, 1W, 1M, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'DAILY' in factor_upper or '1D' in factor_upper:
            return '1D'
        elif 'WEEKLY' in factor_upper or '1W' in factor_upper:
            return '1W'
        elif 'MONTHLY' in factor_upper or '1M' in factor_upper:
            return '1M'
        elif 'QUARTERLY' in factor_upper or '3M' in factor_upper:
            return '3M'
        elif 'YEARLY' in factor_upper or '1Y' in factor_upper:
            return '1Y'
        else:
            return '1D'  # Default to daily

    def _infer_frequency(self, factor_name: str) -> str:
        """
        Infer calculation frequency from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Frequency (real_time, daily, weekly, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'REALTIME' in factor_upper or 'RT' in factor_upper:
            return 'real_time'
        elif 'INTRADAY' in factor_upper:
            return 'intraday'
        elif 'DAILY' in factor_upper:
            return 'daily'
        elif 'WEEKLY' in factor_upper:
            return 'weekly'
        elif 'MONTHLY' in factor_upper:
            return 'monthly'
        else:
            return 'daily'  # Default to daily

    # Port interface implementation - delegated to local repository
    def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: PortfolioCompanyShareOptionPriceReturnFactor) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: PortfolioCompanyShareOptionPriceReturnFactor) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False