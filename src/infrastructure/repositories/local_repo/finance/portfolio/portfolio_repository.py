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
        Create the initial cash / currency holding for a newly created portfolio.

        A portfolio always starts with a cash position equal to ``initial_cash``
        in ``currency_code``.  This is represented as:

        * A ``HoldingModel`` row that links the portfolio (via ``container_id``)
          to the ``Currency`` financial asset (via ``asset_id``).
        * A ``PositionModel`` row on the portfolio with ``quantity = initial_cash``
          and ``position_type = LONG``.

        Both creations are idempotent: if the holding/position already exists
        (e.g. because the portfolio was just fetched rather than truly created
        anew) nothing is changed.
        """
        try:
            from src.infrastructure.models.finance.holding.holding import HoldingModel
            from src.infrastructure.models.finance.position import PositionModel
            from src.domain.entities.finance.holding.position import PositionType

            portfolio_id = getattr(portfolio, 'id', None)
            if not portfolio_id:
                logger.warning("_create_cash_holding: portfolio has no id, skipping")
                return

            # 1. Get or create the Currency entity
            currency_repo = getattr(self.factory, 'currency_local_repo', None)
            if not currency_repo:
                logger.warning(
                    "_create_cash_holding: currency_local_repo not available in factory; "
                    "cash holding will not be created"
                )
                return

            currency = currency_repo.get_or_create(iso_code=currency_code)
            if not currency:
                logger.warning(
                    f"_create_cash_holding: could not get/create currency {currency_code}"
                )
                return

            currency_id = getattr(currency, 'id', None) or getattr(currency, 'asset_id', None)
            if not currency_id:
                logger.warning(
                    f"_create_cash_holding: currency {currency_code} has no id"
                )
                return

            # 2. Create the Holding (idempotent)
            holding_model = self.session.query(HoldingModel).filter(
                HoldingModel.container_id == portfolio_id,
                HoldingModel.asset_id    == currency_id,
            ).first()

            if not holding_model:
                holding_model = HoldingModel(
                    asset_id     = currency_id,
                    container_id = portfolio_id,
                    start_date   = datetime.now(),
                    end_date     = None,
                )
                self.session.add(holding_model)
                self.session.flush()   # assign id before linking to position
                logger.info(
                    f"Created cash holding: portfolio {portfolio_id} ← "
                    f"{currency_code} (currency_id={currency_id})"
                )

            # 3. Create the Position for the cash amount (idempotent)
            position_model = self.session.query(PositionModel).filter(
                PositionModel.portfolio_id == portfolio_id,
            ).first()

            if not position_model:
                position_model = PositionModel(
                    portfolio_id  = portfolio_id,
                    quantity      = int(initial_cash),   # PositionModel.quantity is Integer
                    position_type = PositionType.LONG,
                    holding_id    = holding_model.id,    # link to holding
                )
                self.session.add(position_model)
                self.session.flush()
                logger.info(
                    f"Created cash position: portfolio {portfolio_id}, "
                    f"quantity={initial_cash} {currency_code}"
                )

            # 4. Ensure the bidirectional FK is set on both sides.
            if holding_model.position_id != position_model.id:
                holding_model.position_id = position_model.id
            if getattr(position_model, 'holding_id', None) != holding_model.id:
                position_model.holding_id = holding_model.id

            self.session.commit()

        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Error creating cash holding for portfolio {getattr(portfolio, 'id', '?')}: {e}"
            )
            # Not re-raised: cash holding failure must not prevent portfolio creation

    def get_related_entities(self, portfolio_id: int) -> List:
        """
        Get all entities related to a specific portfolio using SQLAlchemy inspect
        to discover direct and indirect relationships.

        Args:
            portfolio_id: The portfolio ID to get related entities for

        Returns:
            List of related entities found through relationship inspection
        """
        try:
            # Get the portfolio model to inspect its relationships
            portfolio_model = self.session.query(self.model_class).filter_by(id=portfolio_id).first()
            if not portfolio_model:
                logger.warning(f"Portfolio {portfolio_id} not found")
                return []

            related_entities = []
            
            # Use SQLAlchemy inspect to get relationship information
            mapper = inspect(self.model_class)
            
            # Process direct relationships (portfolio -> related entity)
            for relationship_name, relationship in mapper.relationships.items():
                try:
                    # Get the related entity through the relationship
                    related_value = getattr(portfolio_model, relationship_name, None)
                    
                    if related_value is not None:
                        if hasattr(related_value, '__iter__') and not isinstance(related_value, str):
                            # Collection relationship (one-to-many, many-to-many)
                            for item in related_value:
                                if item:
                                    entity = self._to_entity(item) if hasattr(self, '_to_entity') else item
                                    if entity:
                                        related_entities.append(entity)
                        else:
                            # Single relationship (many-to-one, one-to-one)
                            entity = self._to_entity(related_value) if hasattr(self, '_to_entity') else related_value
                            if entity:
                                related_entities.append(entity)
                                
                except Exception as rel_error:
                    logger.debug(f"Could not access relationship {relationship_name}: {rel_error}")
                    continue

            # Process indirect relationships (entities that reference this portfolio)
            # Look for entities that have foreign keys pointing to this portfolio
            portfolio_table = mapper.mapped_table
            
            for table_name, table in portfolio_table.metadata.tables.items():
                try:
                    for column in table.columns:
                        # Check if column is a foreign key to portfolio table
                        if column.foreign_keys:
                            for fk in column.foreign_keys:
                                if fk.column.table.name == portfolio_table.name and str(fk.column.name) == 'id':
                                    # Found a table that references portfolios
                                    # Query for entities that reference this portfolio
                                    referencing_models = self.session.query(table).filter(
                                        column == portfolio_id
                                    ).all()
                                    
                                    for ref_model in referencing_models:
                                        # Convert to entity if mapper available, otherwise use raw model
                                        if hasattr(ref_model, '__table__'):
                                            related_entities.append(ref_model)
                                        
                except Exception as indirect_error:
                    logger.debug(f"Could not process indirect relationships for table {table_name}: {indirect_error}")
                    continue

            logger.info(f"Retrieved {len(related_entities)} related entities for portfolio {portfolio_id}")
            return related_entities
            
        except Exception as e:
            logger.error(f"Error retrieving related entities for portfolio {portfolio_id}: {str(e)}")
            return []

    # Standard CRUD interface
    def create(self, entity: entity_class) -> entity_class:
        """Create new portfolio entity in database (standard CRUD interface)."""
        return self.add(entity)