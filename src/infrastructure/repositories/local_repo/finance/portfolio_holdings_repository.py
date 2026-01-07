"""
PortfolioHoldings Repository - handles CRUD operations for PortfolioHoldings entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from decimal import Decimal
import json

from src.infrastructure.models.finance.holding.portfolio_holding import PortfolioHoldings
from infrastructure.repositories.local_repo.base_repository import BaseLocalRepository


class PortfolioHoldingsRepository(BaseLocalRepository):
    """Repository for managing PortfolioHoldings entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for PortfolioHoldings."""
        return PortfolioHoldings
    
    def _to_entity(self, model: PortfolioHoldings) -> dict:
        """Convert infrastructure model to entity-like dict."""
        if not model:
            return None
        
        return {
            'id': model.id,
            'portfolio_id': model.portfolio_id,
            'cash_balance': Decimal(str(model.cash_balance)) if model.cash_balance else Decimal('0'),
            'total_value': Decimal(str(model.total_value)) if model.total_value else Decimal('0'),
            'holdings_value': Decimal(str(model.holdings_value)) if model.holdings_value else Decimal('0'),
            'holdings_data': model.holdings_data or {},
            'created_at': model.created_at,
            'updated_at': model.updated_at
        }
    
    def _to_model(self, entity_data: dict) -> PortfolioHoldings:
        """Convert entity-like dict to infrastructure model."""
        if not entity_data:
            return None
        
        return PortfolioHoldings(
            portfolio_id=entity_data.get('portfolio_id'),
            cash_balance=float(entity_data.get('cash_balance', 0)),
            total_value=float(entity_data.get('total_value', 0)),
            holdings_value=float(entity_data.get('holdings_value', 0)),
            holdings_data=entity_data.get('holdings_data', {}),
            created_at=entity_data.get('created_at', datetime.now()),
            updated_at=entity_data.get('updated_at', datetime.now())
        )
    
    def get_all(self) -> List[dict]:
        """Retrieve all PortfolioHoldings records."""
        models = self.session.query(PortfolioHoldings).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, holdings_id: int) -> Optional[dict]:
        """Retrieve PortfolioHoldings by its ID."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.id == holdings_id
        ).first()
        return self._to_entity(model)
    
    def get_by_portfolio_id(self, portfolio_id: int) -> Optional[dict]:
        """Retrieve holdings for a specific portfolio."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.portfolio_id == portfolio_id
        ).first()
        return self._to_entity(model)
    
    def get_latest_by_portfolio_id(self, portfolio_id: int) -> Optional[dict]:
        """Retrieve the latest holdings for a specific portfolio."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.portfolio_id == portfolio_id
        ).order_by(PortfolioHoldings.updated_at.desc()).first()
        return self._to_entity(model)
    
    def exists_by_portfolio_id(self, portfolio_id: int) -> bool:
        """Check if holdings exist for a portfolio."""
        return self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.portfolio_id == portfolio_id
        ).first() is not None
    
    def add(self, entity_data: dict) -> dict:
        """Add a new PortfolioHoldings entity to the database."""
        # Check for existing holdings for this portfolio
        if self.exists_by_portfolio_id(entity_data.get('portfolio_id')):
            existing = self.get_by_portfolio_id(entity_data.get('portfolio_id'))
            return existing
        
        model = self._to_model(entity_data)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, holdings_id: int, **kwargs) -> Optional[dict]:
        """Update an existing PortfolioHoldings record."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.id == holdings_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        model.updated_at = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def update_by_portfolio_id(self, portfolio_id: int, **kwargs) -> Optional[dict]:
        """Update holdings by portfolio ID."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.portfolio_id == portfolio_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        model.updated_at = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def update_holdings_data(self, portfolio_id: int, holdings_data: dict) -> Optional[dict]:
        """Update the holdings data JSON for a portfolio."""
        return self.update_by_portfolio_id(
            portfolio_id, 
            holdings_data=holdings_data,
            updated_at=datetime.now()
        )
    
    def update_values(self, portfolio_id: int, cash_balance: float, 
                     holdings_value: float) -> Optional[dict]:
        """Update cash balance and holdings value."""
        total_value = cash_balance + holdings_value
        
        return self.update_by_portfolio_id(
            portfolio_id,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            total_value=total_value,
            updated_at=datetime.now()
        )
    
    def delete(self, holdings_id: int) -> bool:
        """Delete a PortfolioHoldings record by ID."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.id == holdings_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def delete_by_portfolio_id(self, portfolio_id: int) -> bool:
        """Delete holdings by portfolio ID."""
        model = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.portfolio_id == portfolio_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def _create_or_get_holdings(self, portfolio_id: int, cash_balance: float = 0.0,
                               holdings_data: dict = None) -> dict:
        """
        Create portfolio holdings if it doesn't exist, otherwise return existing.
        Follows the same pattern as other repositories' _create_or_get_* methods.
        
        Args:
            portfolio_id: Portfolio ID
            cash_balance: Initial cash balance
            holdings_data: Holdings data dictionary
            
        Returns:
            dict: Created or existing holdings
        """
        # Check if entity already exists
        if self.exists_by_portfolio_id(portfolio_id):
            return self.get_by_portfolio_id(portfolio_id)
        
        try:
            # Create new holdings entity
            entity_data = {
                'portfolio_id': portfolio_id,
                'cash_balance': cash_balance,
                'holdings_value': 0.0,
                'total_value': cash_balance,
                'holdings_data': holdings_data or {},
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Add to database
            return self.add(entity_data)
            
        except Exception as e:
            print(f"Error creating holdings for portfolio {portfolio_id}: {str(e)}")
            return None
    
    def get_portfolios_by_value_range(self, min_value: float, max_value: float) -> List[dict]:
        """Get holdings where total value is within a range."""
        models = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.total_value >= min_value,
            PortfolioHoldings.total_value <= max_value
        ).all()
        
        return [self._to_entity(model) for model in models]
    
    def get_cash_heavy_portfolios(self, min_cash_percentage: float = 50.0) -> List[dict]:
        """Get portfolios where cash represents a high percentage of total value."""
        # This would need to be calculated based on cash_balance / total_value
        models = self.session.query(PortfolioHoldings).filter(
            PortfolioHoldings.total_value > 0
        ).all()
        
        cash_heavy = []
        for model in models:
            entity = self._to_entity(model)
            if entity['total_value'] > 0:
                cash_percentage = (entity['cash_balance'] / entity['total_value']) * 100
                if cash_percentage >= min_cash_percentage:
                    cash_heavy.append(entity)
        
        return cash_heavy
    
    # Standard CRUD interface
    def create(self, entity_data: dict) -> dict:
        """Create new holdings entity in database (standard CRUD interface)."""
        return self.add(entity_data)