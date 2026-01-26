# Security Holding Local Repository
# Mirrors src/infrastructure/models/finance/security_holding.py
from typing import Optional
from sqlalchemy.orm import Session

from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
class SecurityHoldingRepository(BaseLocalRepository):
    """Local repository for security holding model"""
    
    def __init__(self, session: Session):
        super().__init__(session)
        self.data_store = []
    
    def save(self, security_holding):
        """Save security holding to local storage"""
        self.data_store.append(security_holding)
        
    def find_by_id(self, security_holding_id):
        """Find security holding by ID"""
        for holding in self.data_store:
            if getattr(holding, 'id', None) == security_holding_id:
                return holding
        return None
        
    def find_all(self):
        """Find all security holdings"""
        return self.data_store.copy()

    def get_or_create(self, security_id: int, portfolio_id: Optional[int] = None, 
                      quantity: Optional[float] = None, **kwargs) -> Optional[dict]:
        """
        Get or create a security holding with dependency resolution.
        
        Args:
            security_id: Security ID (primary identifier)
            portfolio_id: Portfolio ID (optional)
            quantity: Holding quantity (optional, defaults to 0)
            **kwargs: Additional fields for security holding
            
        Returns:
            Security holding or None if creation failed
        """
        try:
            # First try to find existing security holding
            for holding in self.data_store:
                if (getattr(holding, 'security_id', None) == security_id and 
                    getattr(holding, 'portfolio_id', None) == portfolio_id):
                    return holding
            
            # Set defaults
            quantity = quantity or 0
            portfolio_id = portfolio_id or 1
            
            # Create new security holding
            holding_data = {
                'security_id': security_id,
                'portfolio_id': portfolio_id,
                'quantity': quantity,
                **kwargs
            }
            
            # Save to data store
            self.save(holding_data)
            
            return holding_data
            
        except Exception as e:
            print(f"Error in get_or_create for security holding (security_id: {security_id}): {e}")
            return None