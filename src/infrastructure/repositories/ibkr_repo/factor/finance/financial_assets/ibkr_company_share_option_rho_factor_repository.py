"""
IBKR Company Share Option Rho Factor Repository - Retrieval and creation of company share option rho factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import CompanyShareOptionRhoFactor
from src.domain.ports.factor.company_share_option_rho_factor_port import CompanyShareOptionRhoFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRCompanyShareOptionRhoFactorRepository(BaseIBKRFactorRepository, CompanyShareOptionRhoFactorPort):
    """
    IBKR implementation for CompanyShareOptionRho factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Company Share Option Rho Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('company_share_option_rho_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create a company share option rho factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "rho")
            subgroup: Factor subgroup (default: "company_greeks")
            
        Returns:
            CompanyShareOptionRhoFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific rho calculation data
            enhanced_kwargs = self._enhance_with_ibkr_rho_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create company share option rho factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for company share option rho factor {name}: {e}")
            return None

    def _enhance_with_ibkr_rho_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific rho calculation data for company shares.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with rho calculation metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_model'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Company Share Option Rho factor: {primary_key}'
        
        # Add rho-specific metadata
        if 'calculation_model' not in enhanced:
            enhanced['calculation_model'] = 'black_scholes'
        
        if 'greek_type' not in enhanced:
            enhanced['greek_type'] = 'rho'
        
        # Add underlying company mapping if not provided
        if 'underlying_symbol' not in enhanced:
            enhanced['underlying_symbol'] = self._infer_underlying_symbol(primary_key)
        
        # Add rho-specific calculation metadata
        enhanced['interest_rate_source'] = enhanced.get('interest_rate_source', 'risk_free')
        enhanced['rate_curve_modeling'] = enhanced.get('rate_curve_modeling', 'treasury_curve')
        enhanced['fed_policy_impact'] = enhanced.get('fed_policy_impact', True)
        enhanced['term_structure_adjustment'] = enhanced.get('term_structure_adjustment', True)
        enhanced['credit_spread_adjustment'] = enhanced.get('credit_spread_adjustment', False)
        enhanced['parallel_shift_assumption'] = enhanced.get('parallel_shift_assumption', True)
        enhanced['non_parallel_shift_modeling'] = enhanced.get('non_parallel_shift_modeling', False)
        enhanced['dividend_yield_correlation'] = enhanced.get('dividend_yield_correlation', True)
        
        return enhanced

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
            common_words = {'RHO', 'DELTA', 'GAMMA', 'THETA', 'VEGA', 'CALL', 'PUT', 'OPTION', 'PRICE', 'RETURN'}
            for pattern in symbol_patterns:
                if pattern not in common_words:
                    return pattern
        
        return None

    # Port interface implementation - delegated to local repository
    def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionRhoFactor]:
        return self.local_repo.get_by_id(entity_id) if self.local_repo else None

    def get_by_name(self, name: str) -> Optional[CompanyShareOptionRhoFactor]:
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionRhoFactor]:
        return self.local_repo.get_by_underlying_symbol(underlying_symbol) if self.local_repo else []

    def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionRhoFactor]:
        return self.local_repo.get_by_date_range(start_date, end_date) if self.local_repo else []

    def get_all(self) -> List[CompanyShareOptionRhoFactor]:
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: CompanyShareOptionRhoFactor) -> Optional[CompanyShareOptionRhoFactor]:
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: CompanyShareOptionRhoFactor) -> Optional[CompanyShareOptionRhoFactor]:
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, entity_id: int) -> bool:
        return self.local_repo.delete(entity_id) if self.local_repo else False