"""
Portfolio Repository - handles CRUD operations for Portfolio entities.

Follows the standardized repository pattern with _create_or_get_* methods
consistent with other repositories in the codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from decimal import Decimal

from src.infrastructure.models.finance.portfolio import Portfolio as PortfolioModel
from src.domain.entities.finance.portfolio.portfolio import (
    Portfolio as PortfolioEntity, 
    PortfolioType, 
    RiskTolerance,
    PortfolioHoldings,
    PortfolioStatistics
)
from src.infrastructure.repositories.base_repository import BaseRepository


class PortfolioRepository(BaseRepository):
    """Repository for managing Portfolio entities."""
    
    def __init__(self, session: Session):
        super().__init__(session)
    
    @property
    def model_class(self):
        """Return the SQLAlchemy model class for Portfolio."""
        return PortfolioModel
    
    def _to_entity(self, model: PortfolioModel) -> PortfolioEntity:
        """Convert infrastructure model to domain entity."""
        if not model:
            return None
        
        # Convert portfolio type
        portfolio_type = PortfolioType.STANDARD
        try:
            portfolio_type = PortfolioType(model.portfolio_type)
        except (ValueError, AttributeError):
            pass
        
        # Convert risk tolerance
        risk_tolerance = RiskTolerance.MODERATE
        try:
            if model.risk_tolerance:
                risk_tolerance = RiskTolerance(model.risk_tolerance)
        except (ValueError, AttributeError):
            pass
        
        # Create portfolio statistics
        statistics = PortfolioStatistics(
            total_return=Decimal(str(model.total_return)) if model.total_return else Decimal('0'),
            total_return_percent=Decimal(str(model.total_return_percent)) if model.total_return_percent else Decimal('0'),
            max_drawdown=Decimal(str(model.max_drawdown)) if model.max_drawdown else Decimal('0'),
            high_water_mark=Decimal(str(model.high_water_mark)) if model.high_water_mark else Decimal('0'),
            volatility=Decimal(str(model.volatility)) if model.volatility else Decimal('0'),
            sharpe_ratio=Decimal(str(model.sharpe_ratio)) if model.sharpe_ratio else Decimal('0'),
            beta=Decimal(str(model.beta)) if model.beta else Decimal('0'),
            alpha=Decimal(str(model.alpha)) if model.alpha else Decimal('0'),
            var_95=Decimal(str(model.var_95)) if model.var_95 else Decimal('0'),
            tracking_error=Decimal(str(model.tracking_error)) if model.tracking_error else Decimal('0'),
            win_rate=Decimal(str(model.win_rate)) if model.win_rate else Decimal('0'),
            total_trades=model.total_trades or 0,
            winning_trades=model.winning_trades or 0,
            losing_trades=model.losing_trades or 0
        )
        
        # Create portfolio holdings
        holdings = PortfolioHoldings(
            cash_balance=Decimal(str(model.cash_balance)) if model.cash_balance else Decimal('0'),
            total_value=Decimal(str(model.total_value)) if model.total_value else Decimal('0')
        )
        
        return PortfolioEntity(
            name=model.name,
            portfolio_type=portfolio_type,
            initial_cash=Decimal(str(model.initial_cash)) if model.initial_cash else Decimal('100000'),
            currency=model.currency or "USD",
            inception_date=model.inception_date,
            owner_id=model.owner_id,
            manager_id=model.manager_id,
            account_number=model.account_number,
            holdings=holdings,
            statistics=statistics,
            risk_tolerance=risk_tolerance,
            investment_strategy=model.investment_strategy,
            rebalancing_frequency=model.rebalancing_frequency,
            benchmark_id=model.benchmark_id,
            is_active=model.is_active if model.is_active is not None else True,
            is_paper_trading=model.is_paper_trading if model.is_paper_trading is not None else False,
            management_fee_rate=Decimal(str(model.management_fee_rate)) if model.management_fee_rate else Decimal('0'),
            performance_fee_rate=Decimal(str(model.performance_fee_rate)) if model.performance_fee_rate else Decimal('0'),
            total_fees_paid=Decimal(str(model.total_fees_paid)) if model.total_fees_paid else Decimal('0'),
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_rebalance_date=model.last_rebalance_date,
            last_valuation_date=model.last_valuation_date,
            backtest_id=model.backtest_id,
            backtest_start_date=model.backtest_start_date,
            backtest_end_date=model.backtest_end_date
        )
    
    def _to_model(self, entity: PortfolioEntity) -> PortfolioModel:
        """Convert domain entity to infrastructure model."""
        if not entity:
            return None
        
        return PortfolioModel(
            name=entity.name,
            portfolio_type=entity.portfolio_type.value if entity.portfolio_type else "STANDARD",
            initial_cash=float(entity.initial_cash) if entity.initial_cash else 100000.0,
            currency=entity.currency or "USD",
            inception_date=entity.inception_date,
            owner_id=entity.owner_id,
            manager_id=entity.manager_id,
            account_number=entity.account_number,
            cash_balance=float(entity.holdings.cash_balance) if entity.holdings else 0.0,
            total_value=float(entity.holdings.total_value) if entity.holdings else 0.0,
            total_return=float(entity.statistics.total_return) if entity.statistics else 0.0,
            total_return_percent=float(entity.statistics.total_return_percent) if entity.statistics else 0.0,
            max_drawdown=float(entity.statistics.max_drawdown) if entity.statistics else 0.0,
            high_water_mark=float(entity.statistics.high_water_mark) if entity.statistics else 0.0,
            volatility=float(entity.statistics.volatility) if entity.statistics else None,
            sharpe_ratio=float(entity.statistics.sharpe_ratio) if entity.statistics else None,
            beta=float(entity.statistics.beta) if entity.statistics else None,
            alpha=float(entity.statistics.alpha) if entity.statistics else None,
            var_95=float(entity.statistics.var_95) if entity.statistics else None,
            tracking_error=float(entity.statistics.tracking_error) if entity.statistics else None,
            win_rate=float(entity.statistics.win_rate) if entity.statistics else 0.0,
            total_trades=entity.statistics.total_trades if entity.statistics else 0,
            winning_trades=entity.statistics.winning_trades if entity.statistics else 0,
            losing_trades=entity.statistics.losing_trades if entity.statistics else 0,
            risk_tolerance=entity.risk_tolerance.value if entity.risk_tolerance else "MODERATE",
            investment_strategy=entity.investment_strategy,
            rebalancing_frequency=entity.rebalancing_frequency,
            benchmark_id=entity.benchmark_id,
            is_active=entity.is_active,
            is_paper_trading=entity.is_paper_trading,
            management_fee_rate=float(entity.management_fee_rate) if entity.management_fee_rate else 0.0,
            performance_fee_rate=float(entity.performance_fee_rate) if entity.performance_fee_rate else 0.0,
            total_fees_paid=float(entity.total_fees_paid) if entity.total_fees_paid else 0.0,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_rebalance_date=entity.last_rebalance_date,
            last_valuation_date=entity.last_valuation_date,
            backtest_id=entity.backtest_id,
            backtest_start_date=entity.backtest_start_date,
            backtest_end_date=entity.backtest_end_date
        )
    
    def get_all(self) -> List[PortfolioEntity]:
        """Retrieve all Portfolio records."""
        models = self.session.query(PortfolioModel).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_id(self, portfolio_id: int) -> Optional[PortfolioEntity]:
        """Retrieve a Portfolio by its ID."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id
        ).first()
        return self._to_entity(model)
    
    def get_by_name(self, name: str) -> Optional[PortfolioEntity]:
        """Retrieve a portfolio by name."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.name == name
        ).first()
        return self._to_entity(model)
    
    def get_by_backtest_id(self, backtest_id: str) -> List[PortfolioEntity]:
        """Retrieve portfolios by backtest ID."""
        models = self.session.query(PortfolioModel).filter(
            PortfolioModel.backtest_id == backtest_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def get_by_owner_id(self, owner_id: int) -> List[PortfolioEntity]:
        """Retrieve portfolios by owner ID."""
        models = self.session.query(PortfolioModel).filter(
            PortfolioModel.owner_id == owner_id
        ).all()
        return [self._to_entity(model) for model in models]
    
    def exists_by_name(self, name: str) -> bool:
        """Check if a Portfolio exists by name."""
        return self.session.query(PortfolioModel).filter(
            PortfolioModel.name == name
        ).first() is not None
    
    def add(self, entity: PortfolioEntity) -> PortfolioEntity:
        """Add a new Portfolio entity to the database."""
        # Check for existing portfolio with same name
        if self.exists_by_name(entity.name):
            existing = self.get_by_name(entity.name)
            return existing
        
        model = self._to_model(entity)
        self.session.add(model)
        self.session.commit()
        
        return self._to_entity(model)
    
    def update(self, portfolio_id: int, **kwargs) -> Optional[PortfolioEntity]:
        """Update an existing Portfolio record."""
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id
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
        model = self.session.query(PortfolioModel).filter(
            PortfolioModel.id == portfolio_id
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
            max_id_result = self.session.query(PortfolioModel.id).order_by(PortfolioModel.id.desc()).first()
            
            if max_id_result:
                return max_id_result[0] + 1
            else:
                return 1  # Start from 1 if no records exist
                
        except Exception as e:
            print(f"Warning: Could not determine next available portfolio ID: {str(e)}")
            return 1  # Default to 1 if query fails
    
    def _create_or_get_portfolio(self, name: str, portfolio_type: str = "STANDARD",
                                initial_cash: float = 100000.0, currency: str = "USD",
                                owner_id: Optional[int] = None) -> PortfolioEntity:
        """
        Create portfolio entity if it doesn't exist, otherwise return existing.
        Follows the same pattern as other repositories' _create_or_get_* methods.
        
        Args:
            name: Portfolio name (unique identifier)
            portfolio_type: Type of portfolio (STANDARD, RETIREMENT, BACKTEST, etc.)
            initial_cash: Initial cash amount
            currency: Portfolio currency
            owner_id: Owner ID
            
        Returns:
            PortfolioEntity: Created or existing portfolio
        """
        # Check if entity already exists by name (unique identifier)
        if self.exists_by_name(name):
            return self.get_by_name(name)
        
        try:
            # Create new portfolio entity
            portfolio_type_enum = PortfolioType.STANDARD
            try:
                portfolio_type_enum = PortfolioType(portfolio_type)
            except ValueError:
                pass
            
            portfolio = PortfolioEntity(
                name=name,
                portfolio_type=portfolio_type_enum,
                initial_cash=Decimal(str(initial_cash)),
                currency=currency,
                owner_id=owner_id,
                inception_date=date.today(),
                created_at=datetime.now()
            )
            
            # Add to database
            return self.add(portfolio)
            
        except Exception as e:
            print(f"Error creating portfolio {name}: {str(e)}")
            return None
    
    # Standard CRUD interface
    def create(self, entity: PortfolioEntity) -> PortfolioEntity:
        """Create new portfolio entity in database (standard CRUD interface)."""
        return self.add(entity)