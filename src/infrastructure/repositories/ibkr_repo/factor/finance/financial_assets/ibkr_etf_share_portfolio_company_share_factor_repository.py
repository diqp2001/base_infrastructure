"""
IBKR ETF Share Portfolio Company Share Factor Repository - Retrieval and creation of ETF share portfolio company share factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share_portfolio_company_share_factor import ETFSharePortfolioCompanyShareFactor
from src.domain.ports.factor.etf_share_portfolio_company_share_factor_port import ETFSharePortfolioCompanyShareFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRETFSharePortfolioCompanyShareFactorRepository(BaseIBKRFactorRepository, ETFSharePortfolioCompanyShareFactorPort):
    """
    IBKR implementation for ETFSharePortfolioCompanyShare factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR ETF Share Portfolio Company Share Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.factory = factory
        if self.factory:
            self.local_repo = self.factory._local_repositories.get('etf_share_portfolio_company_share_factor')

    @property
    def entity_class(self):
        return self.local_repo.get_factor_entity()
    
    @property
    def model_class(self):
        return self.local_repo.get_factor_model()

    def _create_or_get(self, name: str, **kwargs):
        """
        Get or create an ETF share portfolio company share factor.
        
        Args:
            name: Factor name
            group: Factor group (default: "return")
            subgroup: Factor subgroup (default: "daily")
            
        Returns:
            ETFSharePortfolioCompanyShareFactor entity from database or newly created
        """
        try:
            # Enhance with IBKR-specific share data
            enhanced_kwargs = self._enhance_with_ibkr_share_data(name, **kwargs)
            
            # Persist to local database
            if self.local_repo:
                created_factor = self.local_repo._create_or_get(primary_key=name, **enhanced_kwargs)
                if created_factor:
                    return created_factor
            
            print(f"Failed to create ETF share portfolio company share factor: {name}")
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for ETF share portfolio company share factor {name}: {e}")
            return None

    def _enhance_with_ibkr_share_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific share data for ETF share portfolios.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary with share metadata
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR ETF Share Portfolio Company Share factor: {primary_key}'
        
        # Add ETF-specific metadata
        if 'etf_type' not in enhanced:
            enhanced['etf_type'] = self._infer_etf_type(primary_key)
        
        return enhanced

    def _infer_etf_type(self, factor_name: str) -> str:
        """
        Infer ETF type based on factor name patterns.
        
        Args:
            factor_name: The factor name to analyze
            
        Returns:
            ETF type classification
        """
        name_lower = factor_name.lower()
        
        if 'sector' in name_lower:
            return 'sector_etf'
        elif 'bond' in name_lower:
            return 'bond_etf'
        elif 'international' in name_lower or 'global' in name_lower:
            return 'international_etf'
        else:
            return 'equity_etf'

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[ETFSharePortfolioCompanyShareFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[ETFSharePortfolioCompanyShareFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_by_group(self, group: str) -> List[ETFSharePortfolioCompanyShareFactor]:
        """Get factors by group (delegates to local repo)."""
        return self.local_repo.get_by_group(group) if self.local_repo else []

    def get_by_subgroup(self, subgroup: str) -> List[ETFSharePortfolioCompanyShareFactor]:
        """Get factors by subgroup (delegates to local repo)."""
        return self.local_repo.get_by_subgroup(subgroup) if self.local_repo else []

    def get_all(self) -> List[ETFSharePortfolioCompanyShareFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: ETFSharePortfolioCompanyShareFactor) -> Optional[ETFSharePortfolioCompanyShareFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: ETFSharePortfolioCompanyShareFactor) -> Optional[ETFSharePortfolioCompanyShareFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False