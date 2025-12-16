"""
Holding Repository - handles CRUD operations for Holding entities.
Follows the standardized repository pattern with _create_or_get_* methods.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.holding import (
    HoldingModel, 
    PortfolioHoldingModel, 
    PortfolioCompanyShareHoldingModel
)
from domain.entities.finance.holding.holding import Holding
from domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
from src.infrastructure.repositories.base_repository import BaseRepository


class HoldingRepository(BaseRepository):
    """Repository for managing Holding entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Holding."""
        return HoldingModel
    
    def _to_entity(self, model: HoldingModel) -> Holding:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return Holding(
            id=model.id,
            asset_id=model.asset_id,
            container_id=model.container_id,
            start_date=model.start_date,
            end_date=model.end_date
        )
    
    def _to_model(self, entity: Holding) -> HoldingModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return HoldingModel(
            id=getattr(entity, 'id', None),
            asset_id=entity.asset.id if hasattr(entity, 'asset') and entity.asset else entity.asset_id,
            container_id=entity.container_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )
    
    def get_all(self) -> List[Holding]:
        """Retrieve all Holding records."""
        models = self.session.query(HoldingModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, holding_id: int) -> Optional[Holding]:
        """Retrieve a Holding by its ID."""
        model = self.session.query(HoldingModel).filter(
            HoldingModel.id == holding_id
        ).first()
        return self._to_entity(model)
    
    def get_by_container_id(self, container_id: int) -> List[Holding]:
        """Retrieve holdings by container ID."""
        models = self.session.query(HoldingModel).filter(
            HoldingModel.container_id == container_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_active_holdings(self, container_id: int) -> List[Holding]:
        """Retrieve active holdings by container ID."""
        models = self.session.query(HoldingModel).filter(
            HoldingModel.container_id == container_id,
            HoldingModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]
    
    def add(self, entity: Holding) -> Holding:
        """Add a new Holding entity to the database."""
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        return self._to_entity(model)
    
    def update(self, holding_id: int, **kwargs) -> Optional[Holding]:
        """Update an existing Holding record."""
        model = self.session.query(HoldingModel).filter(
            HoldingModel.id == holding_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        model.updated_at = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, holding_id: int) -> bool:
        """Delete a Holding record by ID."""
        model = self.session.query(HoldingModel).filter(
            HoldingModel.id == holding_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def create(self, entity: Holding) -> Holding:
        """Create new holding entity in database (standard CRUD interface)."""
        return self.add(entity)


class PortfolioHoldingRepository(BaseRepository):
    """Repository for managing PortfolioHolding entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        return PortfolioHoldingModel
    
    def _to_entity(self, model: PortfolioHoldingModel) -> PortfolioHolding:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return PortfolioHolding(
            id=model.id,
            portfolio_id=model.portfolio_id,
            asset_id=model.asset_id,
            quantity=Decimal(str(model.quantity)) if model.quantity else Decimal('0'),
            average_cost=Decimal(str(model.average_cost)) if model.average_cost else None,
            current_price=Decimal(str(model.current_price)) if model.current_price else None,
            start_date=model.start_date,
            end_date=model.end_date
        )
    
    def _to_model(self, entity: PortfolioHolding) -> PortfolioHoldingModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PortfolioHoldingModel(
            id=getattr(entity, 'id', None),
            portfolio_id=entity.portfolio_id,
            asset_id=entity.asset_id,
            quantity=float(entity.quantity) if entity.quantity else 0.0,
            average_cost=float(entity.average_cost) if entity.average_cost else None,
            current_price=float(entity.current_price) if entity.current_price else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )
    
    def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioHolding]:
        """Retrieve portfolio holdings by portfolio ID."""
        models = self.session.query(PortfolioHoldingModel).filter(
            PortfolioHoldingModel.portfolio_id == portfolio_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_active_holdings(self, portfolio_id: int) -> List[PortfolioHolding]:
        """Retrieve active portfolio holdings."""
        models = self.session.query(PortfolioHoldingModel).filter(
            PortfolioHoldingModel.portfolio_id == portfolio_id,
            PortfolioHoldingModel.is_active == True
        ).all()
        return [self._to_entity(model) for model in models]


class PortfolioCompanyShareHoldingRepository(BaseRepository):
    """Repository for managing PortfolioCompanyShareHolding entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        return PortfolioCompanyShareHoldingModel
    
    def _to_entity(self, model: PortfolioCompanyShareHoldingModel) -> PortfolioCompanyShareHolding:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        return PortfolioCompanyShareHolding(
            id=model.id,
            portfolio_id=model.portfolio_id,
            company_share_id=model.company_share_id,
            symbol=model.symbol,
            quantity=Decimal(str(model.quantity)) if model.quantity else Decimal('0'),
            average_cost=Decimal(str(model.average_cost)) if model.average_cost else None,
            current_price=Decimal(str(model.current_price)) if model.current_price else None,
            start_date=model.start_date,
            end_date=model.end_date
        )
    
    def _to_model(self, entity: PortfolioCompanyShareHolding) -> PortfolioCompanyShareHoldingModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PortfolioCompanyShareHoldingModel(
            id=getattr(entity, 'id', None),
            portfolio_id=entity.portfolio_id,
            company_share_id=entity.company_share_id,
            symbol=entity.symbol,
            quantity=float(entity.quantity) if entity.quantity else 0.0,
            average_cost=float(entity.average_cost) if entity.average_cost else None,
            current_price=float(entity.current_price) if entity.current_price else None,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )
    
    def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioCompanyShareHolding]:
        """Retrieve company share holdings by portfolio ID."""
        models = self.session.query(PortfolioCompanyShareHoldingModel).filter(
            PortfolioCompanyShareHoldingModel.portfolio_id == portfolio_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_symbol(self, symbol: str) -> List[PortfolioCompanyShareHolding]:
        """Retrieve holdings by symbol."""
        models = self.session.query(PortfolioCompanyShareHoldingModel).filter(
            PortfolioCompanyShareHoldingModel.symbol == symbol
        ).all()
        return [self._to_entity(model) for model in models]