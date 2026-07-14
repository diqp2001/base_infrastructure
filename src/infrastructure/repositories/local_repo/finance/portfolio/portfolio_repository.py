"""
Portfolio Repository - handles CRUD operations for Portfolio entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from decimal import Decimal
from sqlalchemy import inspect

logger = logging.getLogger(__name__)



from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.finance.portfolio_mapper import PortfolioMapper
from src.domain.ports.finance.portfolio.portfolio_port import PortfolioPort


class PortfolioRepository(BaseLocalRepository, PortfolioPort):
    """Repository for managing Portfolio entities."""
    
    def __init__(self, session: Session, factory, mapper: PortfolioMapper = None):
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or PortfolioMapper()
    @property
    def entity_class(self):
        return self.mapper.entity_class
    @property
    def model_class(self):
        return self.mapper.model_class
    
    def _to_entity(self, model: model_class) -> entity_class:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        return self.mapper.to_domain(model)
    
    def _to_model(self, entity: entity_class) -> model_class:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        return self.mapper.to_orm(entity)
        
    
    def get_all(self) -> List[entity_class]:
        """Retrieve all Portfolio records."""
        models = self.session.query(self.model_class).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, portfolio_id: int) -> Optional[entity_class]:
        """Retrieve a Portfolio by its ID."""
        model = self.session.query(self.model_class).filter(
            self.model_class.id == portfolio_id
        ).first()
        return self._to_entity(model)    if model else None
    
    def get_by_name(self, name: str) -> Optional[entity_class]:
        """Retrieve a portfolio by name."""
        model = self.session.query(self.model_class).filter(
            self.model_class.name == name
        ).first()
        return self._to_entity(model)     if model else None
    
    def get_by_backtest_id(self, backtest_id: str) -> List[entity_class]:
        """Retrieve portfolios by backtest ID."""
        models = self.session.query(self.model_class).filter(
            self.model_class.backtest_id == backtest_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_owner_id(self, owner_id: int) -> List[entity_class]:
        """Retrieve portfolios by owner ID."""
        models = self.session.query(self.model_class).filter(
            self.model_class.owner_id == owner_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_name(self, name: str) -> bool:
        """Check if a Portfolio exists by name."""
        return self.session.query(self.model_class).filter(
            self.model_class.name == name
        ).first() is not None
    
    def add(self, entity: entity_class) -> entity_class:
        """Add a new Portfolio entity to the database."""
        # Check for existing portfolio with same name
        if self.exists_by_name(entity.name):
            existing = self.get_by_name(entity.name)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, portfolio_id: int, **kwargs) -> Optional[entity_class]:
        """Update an existing Portfolio record."""
        model = self.session.query(self.model_class).filter(
            self.model_class.id == portfolio_id
        ).first()
        
        if not model:
            return None
        
        for attr, value in kwargs.items():
            if hasattr(model, attr):
                setattr(model, attr, value)
        
        self.session.commit()
        return self._to_entity(model)
    
    def delete(self, portfolio_id: int) -> bool:
        """Delete a Portfolio record by ID."""
        model = self.session.query(self.model_class).filter(
            self.model_class.id == portfolio_id
        ).first()
        
        if not model:
            return False
        
        self.session.delete(model)
        self.session.commit()
        return True
    
    def _get_next_available_portfolio_id(self) -> int:
        """
        Get the next available ID for portfolio creation.
        Returns the next sequential ID based on existing database records.
        
        Returns:
            int: Next available ID (defaults to 1 if no records exist)
        """
        try:
            max_id_result = self.session.query(self.model_class.id).order_by(self.model_class.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available portfolio ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def get_or_create(self, name: str, portfolio_type: str = "STANDARD",
                     initial_cash: float = 100000.0, currency_code: str = "USD",
                     owner_id: Optional[int] = None) -> Optional[entity_class]:
        """
        Get or create a portfolio with dependency resolution.
        
        Args:
            name: Portfolio name (required)
            portfolio_type: Type of portfolio (STANDARD, RETIREMENT, BACKTEST, etc.)
            initial_cash: Initial cash amount (default: 100000.0)
            currency_code: Currency ISO code (default: USD)
            owner_id: Owner ID (optional)
            
        Returns:
            Portfolio entity or None if creation failed
        """
        return self._create_or_get(name, portfolio_type=portfolio_type, 
                                  initial_cash=initial_cash, currency=currency_code, 
                                  owner_id=owner_id)

    def _create_or_get(self, name: str, **kwargs) -> Optional[entity_class]:
        """
        Create portfolio entity if it doesn't exist, otherwise return existing.
        Follows the standard _create_or_get pattern from Repository_Local_CreateOrGet_CLAUDE.md
        
        Args:
            name: Portfolio name (unique identifier)
            **kwargs: Additional portfolio parameters
                - portfolio_type: Type of portfolio (default: "STANDARD")
                - initial_cash: Initial cash amount (default: 100000.0)
                - currency: Portfolio currency (default: "USD")
                - owner_id: Owner ID (optional)
                - inception_date: Portfolio inception date (default: today)
                - created_at: Creation timestamp (default: now)
            
        Returns:
            PortfolioEntity: Created or existing portfolio entity
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If required parameters are invalid
        """
        try:
            # Step 1: Check if entity already exists by unique identifier
            existing_portfolio = self.get_by_name(name)
            if existing_portfolio:
                logger.debug(f"Portfolio {name} already exists, returning existing entity")
                return existing_portfolio

            # Step 2: Create new entity if not found
            logger.info(f"Creating new portfolio: {name}")

            # Handle defaults — accept both 'currency_code' and 'currency' for the ISO code
            portfolio_type = kwargs.get('portfolio_type', "STANDARD")
            initial_cash   = float(kwargs.get('initial_cash', 100000.0))
            currency_code  = (
                kwargs.get('currency_code')
                or kwargs.get('currency')
                or 'USD'
            )
            owner_id       = kwargs.get('owner_id')
            inception_date = kwargs.get('inception_date', date.today())

            # Create domain entity
            new_portfolio = self.entity_class(
                id=None,
                name=name,
                start_date=inception_date,
                end_date=kwargs.get('end_date', None),
            )

            # Step 3: Convert to ORM model and persist
            portfolio_model = self.mapper.to_orm(new_portfolio)

            self.session.add(portfolio_model)
            self.session.commit()

            # Step 4: Convert back to domain entity with database ID
            persisted_entity = self.mapper.to_domain(portfolio_model)

            logger.info(f"Successfully created portfolio {name} with ID {persisted_entity.id}")

            # Step 5: Create the initial cash holding (currency position)
            # Every new portfolio gets one holding for its base currency with
            # quantity equal to initial_cash.
            self._create_cash_holding(persisted_entity, initial_cash, currency_code)

            return persisted_entity

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating/getting portfolio {name}: {str(e)}")
            raise
    
    def _create_cash_holding(
        self,
        portfolio,
        initial_cash: float,
        currency_code: str,
    ) -> None:
        """
        Create the initial cash / currency holding using the CurrencyPortfolio pipeline.

        Structure:
            Portfolio (main)
              └─ CurrencyPortfolioPortfolioHolding  (container = main portfolio)
                   └─ CurrencyPortfolio             (sub-portfolio)
                        └─ CurrencyPortfolioHolding (asset = currency)
                             └─ Position            (quantity = initial_cash)

        All steps are idempotent.
        """
        try:
            from src.infrastructure.repositories.local_repo.finance.position_repository import PositionRepository
            from src.infrastructure.repositories.local_repo.finance.portfolio.currency_portfolio_repository import CurrencyPortfolioRepository
            from src.infrastructure.repositories.local_repo.finance.holding.currency_portfolio_holding_repository import CurrencyPortfolioHoldingRepository
            from src.infrastructure.repositories.local_repo.finance.holding.currency_portfolio_portfolio_holding_repository import CurrencyPortfolioPortfolioHoldingRepository
            from src.infrastructure.models.finance.holding.currency_portfolio_portfolio_holding import CurrencyPortfolioPortfolioHoldingModel
            from src.infrastructure.models.finance.holding.currency_portfolio_holding import CurrencyPortfolioHoldingModel
            from src.domain.entities.finance.holding.currency_portfolio_portfolio_holding import CurrencyPortfolioPortfolioHolding
            from src.domain.entities.finance.holding.currency_portfolio_holding import CurrencyPortfolioHolding

            portfolio_id = getattr(portfolio, 'id', None)
            if not portfolio_id:
                logger.warning("_create_cash_holding: portfolio has no id, skipping")
                return

            position_repo = PositionRepository(self.session, self.factory)
            currency_portfolio_repo = CurrencyPortfolioRepository(self.session, self.factory)
            cp_portfolio_holding_repo = CurrencyPortfolioPortfolioHoldingRepository(self.session, self.factory)
            currency_holding_repo = CurrencyPortfolioHoldingRepository(self.session, self.factory)

            # 1. Resolve the Currency financial asset
            currency_repo = getattr(self.factory, 'currency_local_repo', None)
            if not currency_repo:
                logger.warning(
                    "_create_cash_holding: currency_local_repo not available; "
                    "cash holding will not be created"
                )
                return
            currency = currency_repo._create_or_get(iso_code=currency_code)
            if not currency:
                logger.warning(f"_create_cash_holding: could not get/create currency {currency_code}")
                return
            currency_id = getattr(currency, 'id', None) or getattr(currency, 'asset_id', None)
            if not currency_id:
                logger.warning(f"_create_cash_holding: currency {currency_code} has no id")
                return

            # 2. Find or create the CurrencyPortfolio sub-portfolio + portfolio-portfolio link
            existing_link = (
                self.session.query(CurrencyPortfolioPortfolioHoldingModel)
                .filter_by(container_id=portfolio_id)
                .first()
            )
            if existing_link:
                sub_portfolio_id = existing_link.currency_portfolio_id
            else:
                sub_name = f"{getattr(portfolio, 'name', 'portfolio')}_cash"
                sub_portfolio = currency_portfolio_repo._create_or_get(name=sub_name)
                sub_portfolio_id = sub_portfolio.id
                logger.info(f"Created CurrencyPortfolio '{sub_name}' id={sub_portfolio_id}")

                # Step 1: structural position for the portfolio-portfolio link
                pp_pos = position_repo._create_or_get(
                    portfolio_id=portfolio_id, quantity=1, position_type='LONG'
                )

                # Step 2: link the sub-portfolio to the main portfolio
                cp_link_entity = CurrencyPortfolioPortfolioHolding(
                    id=None,
                    portfolio=type('_Ref', (), {'id': portfolio_id})(),
                    currency_portfolio=type('_Ref', (), {'id': sub_portfolio_id})(),
                    position=pp_pos,
                    start_date=datetime.now(),
                )
                cp_portfolio_holding_repo.save(cp_link_entity)
                logger.info(f"Linked CurrencyPortfolio {sub_portfolio_id} → main portfolio {portfolio_id}")

            # 3. Find or create the leaf CurrencyPortfolioHolding + cash Position
            existing_holding = (
                self.session.query(CurrencyPortfolioHoldingModel)
                .filter_by(currency_portfolio_id=sub_portfolio_id, asset_id=currency_id)
                .first()
            )
            if not existing_holding:
                # Step 3: cash position
                cash_pos = position_repo._create_or_get(
                    portfolio_id=sub_portfolio_id,
                    quantity=int(initial_cash),
                    position_type='LONG',
                )

                # Step 4: currency holding
                currency_holding_entity = CurrencyPortfolioHolding(
                    id=None,
                    asset=type('_Ref', (), {'id': currency_id})(),
                    portfolio=type('_Ref', (), {'id': sub_portfolio_id})(),
                    position=cash_pos,
                    start_date=datetime.now(),
                )
                currency_holding_repo.save(currency_holding_entity)
                logger.info(
                    f"Created CurrencyPortfolioHolding: {currency_code} "
                    f"(currency_id={currency_id}) → sub-portfolio {sub_portfolio_id}, "
                    f"quantity={initial_cash}"
                )

        except Exception as e:
            logger.error(
                f"Error creating cash holding for portfolio {getattr(portfolio, 'id', '?')}: {e}"
            )
            # Not re-raised: cash holding failure must not prevent portfolio creation

    def get_related_entities(self, portfolio_id: int) -> List:
        """Return all sub-portfolio holdings contained in this portfolio."""
        try:
            from src.infrastructure.repositories.local_repo.finance.holding.currency_portfolio_portfolio_holding_repository import CurrencyPortfolioPortfolioHoldingRepository
            from src.infrastructure.repositories.local_repo.finance.holding.company_share_portfolio_portfolio_holding_repository import CompanySharePortfolioPortfolioHoldingRepository
            holdings = []
            holdings += CurrencyPortfolioPortfolioHoldingRepository(self.session, self.factory).get_related_entities(portfolio_id)
            holdings += CompanySharePortfolioPortfolioHoldingRepository(self.session, self.factory).get_related_entities(portfolio_id)
            logger.info(f"Retrieved {len(holdings)} related entities for portfolio {portfolio_id}")
            return holdings
        except Exception as e:
            logger.error(f"Error retrieving related entities for portfolio {portfolio_id}: {str(e)}")
            return []

    # Standard CRUD interface
    def create(self, entity: entity_class) -> entity_class:
        """Create new portfolio entity in database (standard CRUD interface)."""
        return self.add(entity)