"""
Repository for holding entities
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.infrastructure.models.finance.holding.holding import (
    HoldingModel
)
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import CompanySharePortfolioHoldingModel

from src.infrastructure.repositories.mappers.finance.holding.holding_mapper import HoldingMapper
from src.domain.entities.finance.holding.holding import Holding
from domain.entities.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHolding
from src.domain.ports.finance.holding.holding_port import HoldingPort
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository

import logging

logger = logging.getLogger(__name__)


class HoldingRepository(BaseLocalRepository, HoldingPort):
    """Repository for holding entities with basic CRUD operations"""
    
    def __init__(self, session: Session, factory, mapper: HoldingMapper = None):
        super().__init__(session)
        self.factory = factory
        self.mapper = mapper or HoldingMapper()
        self.logger = logger

    def get_by_id(self, holding_id: int) -> Optional[HoldingModel]:
        """Get a holding by ID"""
        model = self.session.query(HoldingModel).filter_by(id=holding_id).first()
        return self.mapper.to_entity(model) if model else None

    def get_all(self) -> List[HoldingModel]:
        """Get all holdings"""
        models = self.session.query(HoldingModel).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_by_container_id(self, container_id: int) -> List[HoldingModel]:
        """Get all holdings for a specific container"""
        models = self.session.query(HoldingModel).filter_by(container_id=container_id).all()
        return [self.mapper.to_entity(model) for model in models]

    def get_active_holdings(self, container_id: int = None) -> List[HoldingModel]:
        """Get active holdings (no end_date or end_date in future)"""
        query = self.session.query(HoldingModel).filter(
            (HoldingModel.end_date.is_(None)) | (HoldingModel.end_date > datetime.now())
        )
        if container_id:
            query = query.filter_by(container_id=container_id)
        
        models = query.all()
        return [self.mapper.to_entity(model) for model in models]

    def save(self, holding: HoldingModel) -> HoldingModel:
        """Save or update a holding"""
        model = self.mapper.to_model(holding)
        self.session.merge(model)
        self.session.commit()
        self.session.refresh(model)
        return self.mapper.to_entity(model)

    def delete(self, holding_id: int) -> bool:
        """Delete a holding by ID"""
        model = self.session.query(HoldingModel).filter_by(id=holding_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False

    def _create_or_get(self, container_id: int, asset_id: Optional[int] = None, 
                      quantity: Optional[float] = None, **kwargs) -> Optional[Holding]:
        """
        Get or create a holding with dependency resolution.
        
        Args:
            container_id: Container ID (primary identifier component)
            asset_id: Asset ID (optional)
            quantity: Holding quantity (optional, defaults to 0)
            **kwargs: Additional fields for the holding
            
        Returns:
            Domain holding entity or None if creation failed
        """
        try:
            # First try to get existing holding by container and asset
            if asset_id:
                model = self.session.query(HoldingModel).filter(
                    HoldingModel.container_id == container_id,
                    HoldingModel.asset_id == asset_id
                ).first()
                if model:
                    return self.mapper.to_entity(model)
            
            # Get or create asset dependency if not provided
            if not asset_id:
                from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
                share_repo = CompanyShareRepository(self.session)
                default_asset = share_repo.get_or_create("DEFAULT_HOLDING_ASSET", "Default Holding Asset")
                asset_id = default_asset.id if default_asset else 1
            
            # Set defaults
            quantity = quantity or 0
            from datetime import datetime
            
            # Create new holding entity
            new_holding = Holding(
                id=None,  # Will be assigned by database
                container_id=container_id,
                asset_id=asset_id,
                quantity=quantity,
                start_date=datetime.now().date(),
                end_date=None,
                **kwargs
            )
            
            # Save the holding
            return self.save(new_holding)
            
        except Exception as e:
            print(f"Error in get_or_create for holding (container_id: {container_id}): {e}")
            return None
    
    def _create_or_get(self, container_id: int, asset_id: int = None, **kwargs) -> Optional[Holding]:
        """
        Create holding entity if it doesn't exist, otherwise return existing.
        Enhanced to create cascading relationships:
        - Creates position (potentially empty) related to the holding
        - Ensures FinancialAsset exists via create_or_get
        - Ensures Portfolio exists via create_or_get
        
        Follows the standard _create_or_get pattern from Repository_Local_CreateOrGet_CLAUDE.md
        
        Args:
            container_id: Container ID (primary identifier component)
            asset_id: Asset ID (primary identifier component, optional)
            **kwargs: Additional holding parameters
                - quantity: Holding quantity (default: 0)
                - start_date: Start date (default: today)
                - end_date: End date (optional)
                - symbol: Asset symbol for position creation (optional)
                - is_active: Holding active status (default: True)
            
        Returns:
            Holding: Created or existing holding entity
            
        Raises:
            DatabaseError: If database operation fails
            ValidationError: If required parameters are invalid
        """
        try:
            # Step 1: Check if entity already exists by composite unique key
            if asset_id:
                model = self.session.query(HoldingModel).filter(
                    HoldingModel.container_id == container_id,
                    HoldingModel.asset_id == asset_id
                ).first()
                
                if model:
                    existing_holding = self.mapper.to_entity(model)
                    self.logger.debug(f"Holding for container {container_id} and asset {asset_id} already exists, returning existing entity")
                    return existing_holding
            
            # Step 2: Ensure dependencies exist before creating holding
            self._ensure_holding_dependencies(container_id, asset_id, **kwargs)
            
            # Step 3: Create new entity if not found
            self.logger.info(f"Creating new holding for container {container_id} and asset {asset_id}")
            
            # Handle defaults and asset dependency
            if not asset_id:
                asset_id = self._get_or_create_default_asset(**kwargs)
            
            quantity = kwargs.get('quantity', 0)
            start_date = kwargs.get('start_date', datetime.now().date())
            end_date = kwargs.get('end_date')
            is_active = kwargs.get('is_active', True)
            
            # Create domain entity
            new_holding = Holding(
                id=None,  # Will be assigned by database
                container_id=container_id,
                asset_id=asset_id,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
                **{k: v for k, v in kwargs.items() if k not in ['quantity', 'start_date', 'end_date', 'is_active']}
            )
            
            # Step 4: Convert to ORM model and persist
            holding_model = self.mapper.to_model(new_holding)
            
            self.session.add(holding_model)
            self.session.commit()
            self.session.refresh(holding_model)
            
            # Step 5: Convert back to domain entity with database ID
            persisted_entity = self.mapper.to_entity(holding_model)
            
            # Step 6: Handle cascading relationships after holding creation
            self._handle_holding_cascading_relationships(persisted_entity, **kwargs)
            
            self.logger.info(f"Successfully created holding for container {container_id} and asset {asset_id} with ID {persisted_entity.id}")
            return persisted_entity
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating/getting holding for container {container_id} and asset {asset_id}: {str(e)}")
            raise
    
    def _ensure_holding_dependencies(self, container_id: int, asset_id: int = None, **kwargs):
        """
        Ensure required dependencies exist before creating holding:
        - Portfolio (container)
        - FinancialAsset (if asset_id provided)
        
        Args:
            container_id: Portfolio/container ID
            asset_id: Asset ID (optional)
            **kwargs: Additional parameters for dependency creation
        """
        try:
            # Ensure Portfolio exists
            from src.infrastructure.repositories.local_repo.finance.portfolio_repository import PortfolioRepository
            portfolio_repo = PortfolioRepository(self.session, self.factory)
            
            portfolio = portfolio_repo.get_by_id(container_id)
            if not portfolio:
                # Create default portfolio if it doesn't exist
                portfolio_name = kwargs.get('portfolio_name', f'Portfolio_{container_id}')
                portfolio = portfolio_repo._create_or_get(
                    name=portfolio_name,
                    **{k: v for k, v in kwargs.items() if k.startswith('portfolio_')}
                )
                self.logger.info(f"Created portfolio {portfolio_name} with ID {portfolio.id} for holding")
            
            # Ensure FinancialAsset exists if asset_id provided
            if asset_id:
                self._ensure_financial_asset_exists(asset_id, **kwargs)
                
        except Exception as e:
            self.logger.error(f"Error ensuring holding dependencies: {str(e)}")
    
    def _get_or_create_default_asset(self, **kwargs) -> int:
        """
        Get or create default asset for holdings without specific asset.
        
        Args:
            **kwargs: Parameters for asset creation
            
        Returns:
            int: Asset ID
        """
        try:
            from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
            
            share_repo = CompanyShareRepository(self.session, self.factory)
            symbol = kwargs.get('symbol', 'DEFAULT_HOLDING_ASSET')
            name = kwargs.get('asset_name', 'Default Holding Asset')
            
            default_asset = share_repo.get_or_create(symbol, name)
            return default_asset.id if default_asset else 1
            
        except Exception as e:
            self.logger.error(f"Error creating default asset: {str(e)}")
            return 1  # Fallback to asset ID 1
    
    def _ensure_financial_asset_exists(self, asset_id: int, **kwargs):
        """
        Ensure the financial asset exists.
        
        Args:
            asset_id: Asset ID to verify
            **kwargs: Parameters for asset creation if needed
        """
        try:
            from src.infrastructure.repositories.local_repo.finance.financial_assets.financial_asset_repository import FinancialAssetRepository
            
            asset_repo = FinancialAssetRepository(self.session, self.factory)
            
            # Check if asset exists, create if not
            asset = asset_repo.get_by_id(asset_id)
            if not asset:
                # Create basic financial asset if it doesn't exist
                symbol = kwargs.get('symbol', f'ASSET_{asset_id}')
                asset = asset_repo._create_or_get(
                    symbol=symbol,
                    **{k: v for k, v in kwargs.items() if k.startswith('asset_')}
                )
                if asset:
                    self.logger.info(f"Created financial asset {symbol} with ID {asset.id}")
                    
        except Exception as e:
            self.logger.error(f"Error ensuring financial asset {asset_id} exists: {str(e)}")
    
    def _handle_holding_cascading_relationships(self, holding: Holding, **kwargs):
        """
        Handle cascading relationship creation for holdings:
        - Create position (potentially empty) related to the holding
        
        Args:
            holding: The created holding entity
            **kwargs: Additional parameters for relationship creation
        """
        try:
            # Create position for the holding
            self._create_position_for_holding(holding, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Error handling cascading relationships for holding {holding.id}: {str(e)}")
            # Don't re-raise as this is post-creation enhancement
    
    def _create_position_for_holding(self, holding: Holding, **kwargs):
        """
        Create a position (potentially empty) related to the holding.
        
        Args:
            holding: The holding entity
            **kwargs: Additional position parameters
        """
        try:
            from src.infrastructure.repositories.local_repo.finance.position_repository import PositionRepository
            
            position_repo = PositionRepository(self.session, self.factory)
            
            # Determine symbol for position
            symbol = kwargs.get('symbol', f'HOLDING_{holding.id}_ASSET_{holding.asset_id}')
            
            # Create position with same quantity as holding (may be 0/empty)
            position = position_repo._create_or_get(
                portfolio_id=holding.container_id,
                symbol=symbol,
                quantity=holding.quantity or 0,
                asset_id=holding.asset_id,
                **{k: v for k, v in kwargs.items() if k.startswith('position_')}
            )
            
            if position:
                self.logger.info(f"Created position {position.id} for holding {holding.id} with symbol {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error creating position for holding {holding.id}: {str(e)}")



