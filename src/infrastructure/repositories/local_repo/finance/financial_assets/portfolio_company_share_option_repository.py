"""
PortfolioCompanyShareOption Repository - handles CRUD operations for option entities.
Follows the standardized repository pattern with _create_or_get_* methods.
"""

from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.financial_assets.portfolio_company_share_option import PortfolioCompanyShareOptionModel
from domain.entities.finance.financial_assets.derivatives.option.portfolio_company_share_option import PortfolioCompanyShareOption
from domain.entities.finance.financial_assets.derivatives.option.option_type import OptionType
from src.infrastructure.repositories.base_repository import BaseRepository


class PortfolioCompanyShareOptionRepository(BaseRepository):
    """Repository for managing PortfolioCompanyShareOption entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class."""
        return PortfolioCompanyShareOptionModel
    
    def _to_entity(self, model: PortfolioCompanyShareOptionModel) -> PortfolioCompanyShareOption:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        # Convert option type
        option_type = OptionType.CALL
        try:
            option_type = OptionType(model.option_type.value) if model.option_type else OptionType.CALL
        except (ValueError, AttributeError):
            pass
        
        return PortfolioCompanyShareOption(
            id=model.id,
            underlying=None,  # Will need to be populated separately if needed
            company_id=model.company_id,
            expiration_date=model.expiration_date,
            option_type=option_type,
            exercise_style=model.exercise_style or 'American',
            strike_id=None,  # Derived from strike_price if needed
            start_date=model.start_date,
            end_date=model.end_date
        )
    
    def _to_model(self, entity: PortfolioCompanyShareOption) -> PortfolioCompanyShareOptionModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PortfolioCompanyShareOptionModel(
            id=getattr(entity, 'id', None),
            symbol=getattr(entity, 'symbol', ''),
            underlying_symbol=getattr(entity, 'underlying_symbol', ''),
            option_type=entity.option_type if hasattr(entity, 'option_type') else OptionType.CALL,
            company_id=entity.company_id,
            strike_price=float(getattr(entity, 'strike_price', 0)) if hasattr(entity, 'strike_price') else 0.0,
            expiration_date=entity.expiration_date,
            exercise_style=entity.exercise_style or 'American',
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )
    
    def get_all(self) -> List[PortfolioCompanyShareOption]:
        """Retrieve all PortfolioCompanyShareOption records."""
        models = self.session.query(PortfolioCompanyShareOptionModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, option_id: int) -> Optional[PortfolioCompanyShareOption]:
        """Retrieve an option by its ID."""
        model = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.id == option_id
        ).first()
        return self._to_entity(model)
    
    def get_by_symbol(self, symbol: str) -> Optional[PortfolioCompanyShareOption]:
        """Retrieve an option by its symbol."""
        model = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.symbol == symbol
        ).first()
        return self._to_entity(model)
    
    def get_by_portfolio_id(self, portfolio_id: int) -> List[PortfolioCompanyShareOption]:
        """Retrieve options by portfolio ID."""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.portfolio_id == portfolio_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOption]:
        """Retrieve options by underlying symbol."""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.underlying_symbol == underlying_symbol
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_expiring_options(self, expiry_date: date) -> List[PortfolioCompanyShareOption]:
        """Retrieve options expiring on a specific date."""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.expiration_date == expiry_date
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_options_by_type(self, option_type: OptionType) -> List[PortfolioCompanyShareOption]:
        """Retrieve options by type (CALL/PUT)."""
        models = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.option_type == option_type
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_symbol(self, symbol: str) -> bool:
        """Check if an option exists by symbol."""
        return self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.symbol == symbol
        ).first() is not None
    
    def add(self, entity: PortfolioCompanyShareOption) -> PortfolioCompanyShareOption:
        """Add a new option entity to the database."""
        if hasattr(entity, 'symbol') and self.exists_by_symbol(entity.symbol):
            existing = self.get_by_symbol(entity.symbol)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        return self._to_entity(model)
    
    def update(self, option_id: int, **kwargs) -> Optional[PortfolioCompanyShareOption]:
        """Update an existing option record."""
        model = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.id == option_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        model.updated_at = datetime.now()
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, option_id: int) -> bool:
        """Delete an option record by ID."""
        model = self.session.query(PortfolioCompanyShareOptionModel).filter(
            PortfolioCompanyShareOptionModel.id == option_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def create(self, entity: PortfolioCompanyShareOption) -> PortfolioCompanyShareOption:
        """Create new option entity in database (standard CRUD interface)."""
        return self.add(entity)