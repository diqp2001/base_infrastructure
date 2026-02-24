"""
IBKR Portfolio Company Share Option Delta Factor Repository - Retrieval and creation of portfolio company share option delta factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_delta_factor import PortfolioCompanyShareOptionDeltaFactor
from src.domain.ports.factor.portfolio_company_share_option_delta_factor_port import PortfolioCompanyShareOptionDeltaFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRPortfolioCompanyShareOptionDeltaFactorRepository(BaseIBKRFactorRepository, PortfolioCompanyShareOptionDeltaFactorPort):
    """
    IBKR implementation for PortfolioCompanyShareOptionDelta factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Portfolio Company Share Option Delta Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('portfolio_company_share_option_delta_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create a portfolio company share option delta factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "delta")
            subgroup: Factor subgroup (default: "greeks")
            
        Returns:
            PortfolioCompanyShareOptionDeltaFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific delta calculation data
            enhanced_kwargs = self._enhance_with_ibkr_delta_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create portfolio company share option delta factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share option delta factor {name}: {e}")
            return None

    def _enhance_with_ibkr_delta_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific delta calculation data for portfolio company shares.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with delta calculation metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_model'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Portfolio Company Share Option Delta factor: {primary_key}'
        
        # Add delta-specific metadata
        if 'calculation_model' not in enhanced:
            enhanced['calculation_model'] = self._infer_calculation_model(primary_key)
        
        if 'greek_type' not in enhanced:
            enhanced['greek_type'] = self._infer_greek_type(primary_key)
        
        # Add underlying portfolio mapping if not provided
        if 'underlying_portfolio' not in enhanced:
            enhanced['underlying_portfolio'] = self._infer_underlying_portfolio(primary_key)
        
        # Add sensitivity specifications
        if 'sensitivity_type' not in enhanced:
            enhanced['sensitivity_type'] = self._infer_sensitivity_type(primary_key)
            
        if 'hedge_ratio_calculation' not in enhanced:
            enhanced['hedge_ratio_calculation'] = self._infer_hedge_ratio_method(primary_key)
        
        # Add portfolio-specific delta calculation metadata
        enhanced['portfolio_correlation_impact'] = enhanced.get('portfolio_correlation_impact', True)
        enhanced['individual_stock_delta_aggregation'] = enhanced.get('individual_stock_delta_aggregation', 'weighted')
        enhanced['cross_correlation_adjustment'] = enhanced.get('cross_correlation_adjustment', True)
        enhanced['rebalancing_sensitivity'] = enhanced.get('rebalancing_sensitivity', True)
        enhanced['volatility_surface_modeling'] = enhanced.get('volatility_surface_modeling', 'implied_vol')
        enhanced['time_decay_adjustment'] = enhanced.get('time_decay_adjustment', True)
        
        return enhanced

    def _infer_calculation_model(self, factor_name: str) -> str:
        """
        Infer calculation model from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Calculation model (black_scholes, binomial, monte_carlo, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'BLACK_SCHOLES' in factor_upper or 'BS' in factor_upper:
            return 'black_scholes'
        elif 'BINOMIAL' in factor_upper:
            return 'binomial'
        elif 'MONTE_CARLO' in factor_upper or 'MC' in factor_upper:
            return 'monte_carlo'
        elif 'TRINOMIAL' in factor_upper:
            return 'trinomial'
        elif 'FINITE_DIFF' in factor_upper:
            return 'finite_difference'
        else:
            return 'black_scholes'  # Default to Black-Scholes

    def _infer_greek_type(self, factor_name: str) -> str:
        """
        Infer Greek type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Greek type (delta, gamma, theta, vega, rho)
        """
        factor_upper = factor_name.upper()
        
        if 'DELTA' in factor_upper:
            return 'delta'
        elif 'GAMMA' in factor_upper:
            return 'gamma'
        elif 'THETA' in factor_upper:
            return 'theta'
        elif 'VEGA' in factor_upper:
            return 'vega'
        elif 'RHO' in factor_upper:
            return 'rho'
        else:
            return 'delta'  # Default to delta

    def _infer_sensitivity_type(self, factor_name: str) -> str:
        """
        Infer sensitivity type from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Sensitivity type (price, volatility, time, rate, etc.)
        """
        factor_upper = factor_name.upper()
        
        if 'PRICE' in factor_upper:
            return 'price_sensitivity'
        elif 'VOL' in factor_upper:
            return 'volatility_sensitivity'
        elif 'TIME' in factor_upper:
            return 'time_sensitivity'
        elif 'RATE' in factor_upper:
            return 'interest_rate_sensitivity'
        elif 'DIVIDEND' in factor_upper:
            return 'dividend_sensitivity'
        else:
            return 'price_sensitivity'  # Default to price sensitivity

    def _infer_hedge_ratio_method(self, factor_name: str) -> str:
        """
        Infer hedge ratio calculation method from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Hedge ratio method
        """
        factor_upper = factor_name.upper()
        
        if 'SIMPLE' in factor_upper:
            return 'simple_delta'
        elif 'DYNAMIC' in factor_upper:
            return 'dynamic_hedge'
        elif 'MINIMUM_VARIANCE' in factor_upper:
            return 'minimum_variance'
        elif 'PORTFOLIO_LEVEL' in factor_upper:
            return 'portfolio_level'
        else:
            return 'delta_neutral'  # Default hedge method

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

    # Port interface implementation - delegated to local repository
    def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: PortfolioCompanyShareOptionDeltaFactor) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: PortfolioCompanyShareOptionDeltaFactor) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False