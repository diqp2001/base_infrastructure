"""
IBKR ETF Share Portfolio Company Share Price Return Factor Repository - Retrieval and creation of ETF share portfolio company share price return factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share_portfolio_company_share_price_return_factor import ETFSharePortfolioCompanySharePriceReturnFactor
from src.domain.ports.factor.etf_share_portfolio_company_share_price_return_factor_port import ETFSharePortfolioCompanySharePriceReturnFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRETFSharePortfolioCompanySharePriceReturnFactorRepository(BaseIBKRFactorRepository, ETFSharePortfolioCompanySharePriceReturnFactorPort):
    """
    IBKR implementation for ETFSharePortfolioCompanySharePriceReturn factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR ETF Share Portfolio Company Share Price Return Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('etf_share_portfolio_company_share_price_return_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    
    @property
    def model_class(self):
        return self.local_repo.get_factor_model()

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an ETF share portfolio company share price return factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "return")
            subgroup: Factor subgroup (default: "daily")
            
        Returns:
            ETFSharePortfolioCompanySharePriceReturnFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific return calculation data
            enhanced_kwargs = self._enhance_with_ibkr_return_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create ETF share portfolio company share price return factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for ETF share portfolio company share price return factor {name}: {e}")
            return None

    def _enhance_with_ibkr_return_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific return calculation data for ETF share portfolios.
        
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
            enhanced['definition'] = f'IBKR ETF Share Portfolio Company Share Price Return factor: {primary_key}'
        
        # Add return-specific metadata
        if 'return_method' not in enhanced:
            enhanced['return_method'] = self._infer_return_method(primary_key)
        
        if 'calculation_period' not in enhanced:
            enhanced['calculation_period'] = self._infer_calculation_period(primary_key)
        
        return enhanced

    def _infer_return_method(self, factor_name: str) -> str:
        """
        Infer return calculation method based on factor name patterns.
        
        Args:
            factor_name: The factor name to analyze
            
        Returns:
            Return calculation method
        """
        name_lower = factor_name.lower()
        
        if 'log' in name_lower or 'geometric' in name_lower:
            return 'geometric'
        elif 'simple' in name_lower or 'arithmetic' in name_lower:
            return 'simple'
        else:
            return 'geometric'  # Default

    def _infer_calculation_period(self, factor_name: str) -> str:
        """
        Infer calculation period based on factor name patterns.
        
        Args:
            factor_name: The factor name to analyze
            
        Returns:
            Calculation period classification
        """
        name_lower = factor_name.lower()
        
        if 'daily' in name_lower:
            return 'daily'
        elif 'weekly' in name_lower:
            return 'weekly'
        elif 'monthly' in name_lower:
            return 'monthly'
        elif 'annual' in name_lower:
            return 'annual'
        else:
            return 'daily'  # Default

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_by_group(self, group: str) -> List[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Get factors by group (delegates to local repo)."""
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str) -> List[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Get factors by subgroup (delegates to local repo)."""
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self) -> List[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: ETFSharePortfolioCompanySharePriceReturnFactor) -> Optional[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: ETFSharePortfolioCompanySharePriceReturnFactor) -> Optional[ETFSharePortfolioCompanySharePriceReturnFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False