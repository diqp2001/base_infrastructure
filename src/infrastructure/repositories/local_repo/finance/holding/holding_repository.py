"""
Repository for holding entities
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.infrastructure.models.finance.holding.holding import (
    HoldingModel
)
from src.infrastructure.models.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHoldingModel

from src.infrastructure.repositories.mappers.finance.holding.holding_mapper import HoldingMapper
from src.domain.entities.finance.holding.holding import Holding
from src.domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding
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

    def get_or_create(self, container_id: int, asset_id: Optional[int] = None, 
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
        Follows the standard _create_or_get pattern from Repository_Local_CreateOrGet_CLAUDE.md
        
        Args:
            container_id: Container ID (primary identifier component)
            asset_id: Asset ID (primary identifier component, optional)
            **kwargs: Additional holding parameters
                - quantity: Holding quantity (default: 0)
                - start_date: Start date (default: today)
                - end_date: End date (optional)
            
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
            
            # Step 2: Create new entity if not found
            self.logger.info(f"Creating new holding for container {container_id} and asset {asset_id}")
            
            # Handle defaults and dependencies
            if not asset_id:
                # Get or create default asset dependency
                from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository
                share_repo = CompanyShareRepository(self.session, self.factory)
                default_asset = share_repo.get_or_create("DEFAULT_HOLDING_ASSET", "Default Holding Asset")
                asset_id = default_asset.id if default_asset else 1
            
            quantity = kwargs.get('quantity', 0)
            start_date = kwargs.get('start_date', datetime.now().date())
            end_date = kwargs.get('end_date')
            
            # Create domain entity
            new_holding = Holding(
                id=None,  # Will be assigned by database
                container_id=container_id,
                asset_id=asset_id,
                quantity=quantity,
                start_date=start_date,
                end_date=end_date,
                **{k: v for k, v in kwargs.items() if k not in ['quantity', 'start_date', 'end_date']}
            )
            
            # Step 3: Convert to ORM model and persist
            holding_model = self.mapper.to_model(new_holding)
            
            self.session.add(holding_model)
            self.session.commit()
            self.session.refresh(holding_model)
            
            # Step 4: Convert back to domain entity with database ID
            persisted_entity = self.mapper.to_entity(holding_model)
            
            self.logger.info(f"Successfully created holding for container {container_id} and asset {asset_id} with ID {persisted_entity.id}")
            return persisted_entity
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error creating/getting holding for container {container_id} and asset {asset_id}: {str(e)}")
            raise



