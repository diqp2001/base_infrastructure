"""
IBKR Portfolio Company Share Correlation Factor Repository - Interactive Brokers implementation.
"""

from typing import Optional, List, Dict, Any
from src.domain.ports.factor.factor_port import FactorPort
from src.infrastructure.repositories.ibkr_repo.base_ibkr_factor_repository import BaseIBKRFactorRepository
from src.domain.entities.factor.finance.portfolio.portfolio_company_share_factor.portfolio_company_share_correlation_factor import PortfolioCompanyShareCorrelationFactor


class IBKRPortfolioCompanyShareCorrelationFactorRepository(BaseIBKRFactorRepository, FactorPort):
    """IBKR implementation for PortfolioCompanyShareCorrelationFactor entities."""

    def __init__(self, ibkr_client, factory=None):
        super().__init__(ibkr_client)
        self.factory = factory
        
    @property
    def entity_class(self):
        return PortfolioCompanyShareCorrelationFactor

    @property
    def local_repo(self):
        if self.factory:
            return self.factory._local_repositories.get('portfolio_company_share_correlation_factor')
        return None

    def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.get_by_id(entity_id)
        return None

    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.get_by_name(name)
        return None

    def get_by_group(self, group: str) -> List[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.get_by_group(group)
        return []

    def get_by_subgroup(self, subgroup: str) -> List[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.get_by_subgroup(subgroup)
        return []

    def get_all(self) -> List[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.get_all()
        return []

    def add(self, entity: PortfolioCompanyShareCorrelationFactor) -> Optional[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.add(entity)
        return None

    def update(self, entity_id: int, **kwargs) -> Optional[PortfolioCompanyShareCorrelationFactor]:
        if self.local_repo:
            return self.local_repo.update(entity_id, **kwargs)
        return None

    def delete(self, entity_id: int) -> bool:
        if self.local_repo:
            return self.local_repo.delete(entity_id)
        return False

    def _create_or_get(self, name: str, group: str = "portfolio", subgroup: str = "correlation") -> Optional[PortfolioCompanyShareCorrelationFactor]:
        try:
            if self.local_repo:
                existing_factor = self.local_repo.get_by_name(name)
                if existing_factor:
                    return existing_factor
            
            new_factor = PortfolioCompanyShareCorrelationFactor(
                name=name,
                group=group,
                subgroup=subgroup,
                data_type="numeric",
                source="IBKR",
                definition=f"Portfolio company share correlation factor: {name} (from IBKR data)"
            )
            
            if self.local_repo:
                created_factor = self.local_repo.add(new_factor)
                if created_factor:
                    return created_factor
            return None
                
        except Exception as e:
            print(f"Error in get_or_create for portfolio company share correlation factor {name}: {e}")
            return None

    def _extract_value_for_factor(self, factor_id: int, ibkr_data: Dict[str, Any]) -> Optional[Any]:
        try:
            if 'correlation' in ibkr_data:
                return ibkr_data['correlation']
            return None
        except Exception as e:
            print(f"Error extracting correlation factor value: {e}")
            return None