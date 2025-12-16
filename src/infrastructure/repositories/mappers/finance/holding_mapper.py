"""
Mappers for converting between holding domain entities and infrastructure models.
Follows the established mapper pattern in the codebase.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.entities.finance.holding.holding import Holding
from domain.entities.finance.holding.portfolio_holding import PortfolioHolding
from domain.entities.finance.holding.portfolio_company_share_holding import PortfolioCompanyShareHolding

from src.infrastructure.models.finance.holding import (
    HoldingModel,
    PortfolioHoldingModel,
    PortfolioCompanyShareHoldingModel
)


class HoldingMapper:
    """Mapper for basic Holding entities."""
    
    @staticmethod
    def to_entity(model: HoldingModel) -> Optional[Holding]:
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
    
    @staticmethod
    def to_model(entity: Holding) -> Optional[HoldingModel]:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return HoldingModel(
            id=getattr(entity, 'id', None),
            asset_id=entity.asset.id if hasattr(entity, 'asset') and entity.asset else getattr(entity, 'asset_id', None),
            container_id=entity.container_id,
            asset_type=getattr(entity, 'asset_type', 'UNKNOWN'),
            container_type=getattr(entity, 'container_type', 'PORTFOLIO'),
            quantity=float(getattr(entity, 'quantity', 0)) if hasattr(entity, 'quantity') else 0,
            average_cost=float(entity.average_cost) if hasattr(entity, 'average_cost') and entity.average_cost else None,
            current_price=float(entity.current_price) if hasattr(entity, 'current_price') and entity.current_price else None,
            is_active=entity.is_active() if hasattr(entity, 'is_active') else True,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )


class PortfolioHoldingMapper:
    """Mapper for PortfolioHolding entities."""
    
    @staticmethod
    def to_entity(model: PortfolioHoldingModel) -> Optional[PortfolioHolding]:
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
    
    @staticmethod
    def to_model(entity: PortfolioHolding) -> Optional[PortfolioHoldingModel]:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PortfolioHoldingModel(
            id=getattr(entity, 'id', None),
            portfolio_id=entity.portfolio_id,
            asset_id=entity.asset_id,
            asset_type=getattr(entity, 'asset_type', 'UNKNOWN'),
            quantity=float(entity.quantity) if entity.quantity else 0.0,
            average_cost=float(entity.average_cost) if entity.average_cost else None,
            current_price=float(entity.current_price) if entity.current_price else None,
            market_value=float(entity.market_value) if entity.market_value else None,
            unrealized_pnl=float(entity.unrealized_pnl) if entity.unrealized_pnl else None,
            is_active=entity.is_active() if hasattr(entity, 'is_active') else True,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )


class PortfolioCompanyShareHoldingMapper:
    """Mapper for PortfolioCompanyShareHolding entities."""
    
    @staticmethod
    def to_entity(model: PortfolioCompanyShareHoldingModel) -> Optional[PortfolioCompanyShareHolding]:
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
    
    @staticmethod
    def to_model(entity: PortfolioCompanyShareHolding) -> Optional[PortfolioCompanyShareHoldingModel]:
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
            market_value=float(entity.market_value) if entity.market_value else None,
            unrealized_pnl=float(entity.unrealized_pnl) if entity.unrealized_pnl else None,
            is_active=entity.is_active() if hasattr(entity, 'is_active') else True,
            start_date=entity.start_date,
            end_date=entity.end_date,
            created_at=getattr(entity, 'created_at', datetime.now()),
            updated_at=getattr(entity, 'updated_at', datetime.now())
        )