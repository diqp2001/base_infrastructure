"""
IBKR Index Future Factor Repository - Retrieval and creation of index future factors via IBKR.
"""

from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor
from src.domain.ports.factor.index_future_factor_port import IndexFutureFactorPort
from src.infrastructure.repositories.ibkr_repo.factor.base_ibkr_factor_repository import BaseIBKRFactorRepository


class IBKRIndexFutureFactorRepository(BaseIBKRFactorRepository, IndexFutureFactorPort):
    """
    IBKR implementation for IndexFuture factor acquisition and local delegation.
    """

    def __init__(self, ibkr_client, factory=None):
        """Initialize IBKR Index Future Factor Repository."""
        super().__init__(ibkr_client, factory)
        self.local_repo = factory.index_future_factor_local_repo if factory else None

    def get_or_create(self, primary_key: str, **kwargs) -> Optional[IndexFutureFactor]:
        """
        Get or create an index future factor using IBKR data if available.
        
        Args:
            primary_key: Factor name identifier
            **kwargs: Additional parameters for factor creation
            
        Returns:
            IndexFutureFactor entity or None if creation failed
        """
        try:
            # First check local repository
            if self.local_repo:
                existing = self.local_repo.get_by_name(primary_key)
                if existing:
                    return existing

            # For index future factors, we may need to enhance with IBKR-specific logic
            # For now, delegate to local repository with enhanced parameters
            if self.local_repo:
                enhanced_kwargs = self._enhance_with_ibkr_data(primary_key, **kwargs)
                return self.local_repo.get_or_create(primary_key, **enhanced_kwargs)
            
            return None
            
        except Exception as e:
            print(f"Error in IBKR get_or_create for index future factor {primary_key}: {e}")
            return None

    def _enhance_with_ibkr_data(self, primary_key: str, **kwargs) -> dict:
        """
        Enhance factor creation parameters with IBKR-specific data.
        
        Args:
            primary_key: Factor name
            **kwargs: Original parameters
            
        Returns:
            Enhanced parameters dictionary
        """
        enhanced = kwargs.copy()
        
        # Add IBKR-specific enhancements if available
        if 'source' not in enhanced:
            enhanced['source'] = 'ibkr_api'
        
        if 'definition' not in enhanced:
            enhanced['definition'] = f'IBKR Index Future factor: {primary_key}'
        
        # Add underlying index mapping if not provided
        if 'underlying_index' not in enhanced:
            enhanced['underlying_index'] = self._infer_underlying_index(primary_key)
        
        return enhanced

    def _infer_underlying_index(self, factor_name: str) -> Optional[str]:
        """
        Infer underlying index from factor name.
        
        Args:
            factor_name: Factor name to analyze
            
        Returns:
            Underlying index symbol if determinable
        """
        # Simple heuristics - could be enhanced with IBKR contract lookup
        if 'ES' in factor_name.upper():
            return 'SPX'
        elif 'NQ' in factor_name.upper():
            return 'NDX'
        elif 'RTY' in factor_name.upper():
            return 'RUT'
        elif 'YM' in factor_name.upper():
            return 'DJI'
        
        return None

    # Delegate standard operations to local repository
    def get_by_name(self, name: str) -> Optional[IndexFutureFactor]:
        """Get factor by name (delegates to local repo)."""
        return self.local_repo.get_by_name(name) if self.local_repo else None

    def get_by_id(self, factor_id: int) -> Optional[IndexFutureFactor]:
        """Get factor by ID (delegates to local repo)."""
        return self.local_repo.get_by_id(factor_id) if self.local_repo else None

    def get_all(self) -> List[IndexFutureFactor]:
        """Get all factors (delegates to local repo)."""
        return self.local_repo.get_all() if self.local_repo else []

    def add(self, entity: IndexFutureFactor) -> Optional[IndexFutureFactor]:
        """Add factor entity (delegates to local repo)."""
        return self.local_repo.add(entity) if self.local_repo else None

    def update(self, entity: IndexFutureFactor) -> Optional[IndexFutureFactor]:
        """Update factor entity (delegates to local repo)."""
        return self.local_repo.update(entity) if self.local_repo else None

    def delete(self, factor_id: int) -> bool:
        """Delete factor entity (delegates to local repo)."""
        return self.local_repo.delete(factor_id) if self.local_repo else False