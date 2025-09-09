"""
Result storage for backtest results.
Handles persistence using infrastructure models and DDD principles.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from infrastructure.models.back_testing import (
    MockPortfolioModel, 
    MockPortfolioSnapshot, 
    MockSecurityModel,
    MockSecurityPriceSnapshot
)
from domain.entities.back_testing import MockPortfolio, MockSecurity
from .result_handler import BacktestResult


class ResultStorage:
    """
    Storage handler for backtest results.
    Bridges domain entities and infrastructure models for persistence.
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def save_backtest_result(
        self, 
        result: BacktestResult, 
        portfolio: MockPortfolio
    ) -> MockPortfolioModel:
        """
        Save complete backtest result to database.
        
        Args:
            result: BacktestResult to save
            portfolio: Final portfolio state
            
        Returns:
            Saved MockPortfolioModel instance
        """
        # Create portfolio model from domain entity
        portfolio_model = self._create_portfolio_model(result, portfolio)
        
        # Save to database
        self.db_session.add(portfolio_model)
        self.db_session.commit()
        
        # Save securities
        for symbol, security in portfolio._securities.items():
            security_model = self._create_security_model(
                security, portfolio_model.id, portfolio
            )
            self.db_session.add(security_model)
        
        # Save portfolio snapshot
        snapshot = self._create_portfolio_snapshot(portfolio_model, portfolio)
        self.db_session.add(snapshot)
        
        self.db_session.commit()
        return portfolio_model
    
    def save_portfolio_snapshot(
        self, 
        portfolio_id: int, 
        portfolio: MockPortfolio, 
        timestamp: Optional[datetime] = None
    ) -> MockPortfolioSnapshot:
        """Save a snapshot of portfolio state at specific time."""
        if timestamp is None:
            timestamp = datetime.now()
        
        snapshot = MockPortfolioSnapshot(
            portfolio_id=portfolio_id,
            snapshot_date=timestamp,
            cash=portfolio.cash,
            total_portfolio_value=portfolio.total_portfolio_value,
            holdings_value=portfolio.holdings_value,
            unrealized_pnl=sum(
                security.holdings.unrealized_pnl 
                for security in portfolio._securities.values()
            ),
            total_return_percent=(
                (portfolio.total_portfolio_value - portfolio._initial_cash) / 
                portfolio._initial_cash * 100
            ),
            drawdown_percent=portfolio.calculate_statistics().max_drawdown,
            holdings_snapshot=json.dumps({
                symbol: {
                    'quantity': float(quantity),
                    'price': float(portfolio.get_security(symbol).price) if portfolio.get_security(symbol) else 0,
                    'value': float(portfolio.get_holding_value(symbol))
                }
                for symbol, quantity in portfolio.get_holdings().items()
                if quantity != 0
            })
        )
        
        self.db_session.add(snapshot)
        self.db_session.commit()
        return snapshot
    
    def save_security_price_snapshot(
        self, 
        security_id: int, 
        security: MockSecurity, 
        timestamp: Optional[datetime] = None
    ) -> MockSecurityPriceSnapshot:
        """Save a snapshot of security price at specific time."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Calculate 1-day return if we have price history
        return_1d = 0.0
        if len(security._price_history) >= 2:
            prev_price = security._price_history[-2].price
            return_1d = float((security.price - prev_price) / prev_price)
        
        snapshot = MockSecurityPriceSnapshot(
            security_id=security_id,
            timestamp=timestamp,
            price=security.price,
            volume=security.volume,
            bid=security.bid,
            ask=security.ask,
            open_price=security.open,
            high_price=security.high,
            low_price=security.low,
            close_price=security.close,
            return_1d=return_1d,
            volatility_20d=security.calculate_volatility(20)
        )
        
        self.db_session.add(snapshot)
        self.db_session.commit()
        return snapshot
    
    def load_backtest_result(self, backtest_id: str) -> Optional[MockPortfolioModel]:
        """Load backtest result by ID."""
        return self.db_session.query(MockPortfolioModel).filter(
            MockPortfolioModel.backtest_id == backtest_id
        ).first()
    
    def load_portfolio_snapshots(
        self, 
        portfolio_id: int, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MockPortfolioSnapshot]:
        """Load portfolio snapshots for given time range."""
        query = self.db_session.query(MockPortfolioSnapshot).filter(
            MockPortfolioSnapshot.portfolio_id == portfolio_id
        )
        
        if start_date:
            query = query.filter(MockPortfolioSnapshot.snapshot_date >= start_date)
        if end_date:
            query = query.filter(MockPortfolioSnapshot.snapshot_date <= end_date)
        
        return query.order_by(MockPortfolioSnapshot.snapshot_date).all()
    
    def load_security_snapshots(
        self, 
        security_id: int, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MockSecurityPriceSnapshot]:
        """Load security price snapshots for given time range."""
        query = self.db_session.query(MockSecurityPriceSnapshot).filter(
            MockSecurityPriceSnapshot.security_id == security_id
        )
        
        if start_date:
            query = query.filter(MockSecurityPriceSnapshot.timestamp >= start_date)
        if end_date:
            query = query.filter(MockSecurityPriceSnapshot.timestamp <= end_date)
        
        return query.order_by(MockSecurityPriceSnapshot.timestamp).all()
    
    def get_backtest_summary(self, limit: int = 50) -> List[Dict]:
        """Get summary of recent backtests."""
        portfolios = self.db_session.query(MockPortfolioModel).order_by(
            MockPortfolioModel.created_at.desc()
        ).limit(limit).all()
        
        summaries = []
        for portfolio in portfolios:
            summaries.append({
                'backtest_id': portfolio.backtest_id,
                'name': portfolio.name,
                'created_at': portfolio.created_at.isoformat(),
                'total_return_percent': float(portfolio.total_return_percent) if portfolio.total_return_percent else 0,
                'max_drawdown': float(portfolio.max_drawdown) if portfolio.max_drawdown else 0,
                'total_trades': portfolio.total_trades,
                'win_rate': float(portfolio.win_rate) if portfolio.win_rate else 0,
                'final_value': float(portfolio.total_portfolio_value)
            })
        
        return summaries
    
    def delete_backtest_result(self, backtest_id: str) -> bool:
        """Delete backtest result and all associated data."""
        portfolio = self.load_backtest_result(backtest_id)
        if not portfolio:
            return False
        
        # Delete associated data
        self.db_session.query(MockSecurityPriceSnapshot).filter(
            MockSecurityPriceSnapshot.security_id.in_(
                self.db_session.query(MockSecurityModel.id).filter(
                    MockSecurityModel.portfolio_id == portfolio.id
                )
            )
        ).delete(synchronize_session=False)
        
        self.db_session.query(MockPortfolioSnapshot).filter(
            MockPortfolioSnapshot.portfolio_id == portfolio.id
        ).delete()
        
        self.db_session.query(MockSecurityModel).filter(
            MockSecurityModel.portfolio_id == portfolio.id
        ).delete()
        
        self.db_session.delete(portfolio)
        self.db_session.commit()
        return True
    
    def _create_portfolio_model(
        self, 
        result: BacktestResult, 
        portfolio: MockPortfolio
    ) -> MockPortfolioModel:
        """Create MockPortfolioModel from domain entities."""
        stats = portfolio.calculate_statistics()
        
        return MockPortfolioModel(
            backtest_id=result.backtest_id,
            name=result.algorithm_name,
            description=f"Backtest from {result.start_date.date()} to {result.end_date.date()}",
            initial_cash=portfolio._initial_cash,
            current_cash=portfolio.cash,
            total_portfolio_value=portfolio.total_portfolio_value,
            holdings_value=portfolio.holdings_value,
            total_return=result.total_return,
            total_return_percent=result.total_return_percent,
            unrealized_pnl=sum(
                security.holdings.unrealized_pnl 
                for security in portfolio._securities.values()
            ),
            realized_pnl=sum(
                security.holdings.realized_pnl 
                for security in portfolio._securities.values()
            ),
            max_drawdown=stats.max_drawdown,
            high_water_mark=portfolio._high_water_mark,
            total_trades=stats.trades_count,
            winning_trades=stats.winning_trades,
            losing_trades=stats.losing_trades,
            win_rate=stats.win_rate,
            volatility=result.volatility,
            sharpe_ratio=result.sharpe_ratio,
            holdings_data=json.dumps({
                symbol: float(quantity) 
                for symbol, quantity in portfolio.get_holdings().items()
            }),
            average_costs_data=json.dumps({
                symbol: float(cost) 
                for symbol, cost in portfolio._average_costs.items()
            }),
            securities_data=json.dumps({
                symbol: {
                    'security_type': security.security_type.value,
                    'exchange': security.symbol.exchange
                }
                for symbol, security in portfolio._securities.items()
            }),
            transaction_history=json.dumps(portfolio.get_transaction_history()),
            is_active=False,  # Backtest is completed
            is_paper_trading=True,
            created_at=result.start_date,
            updated_at=datetime.now(),
            backtest_start_date=result.start_date,
            backtest_end_date=result.end_date
        )
    
    def _create_security_model(
        self, 
        security: MockSecurity, 
        portfolio_id: int, 
        portfolio: MockPortfolio
    ) -> MockSecurityModel:
        """Create MockSecurityModel from domain entity."""
        symbol = security.symbol.ticker
        holdings_quantity = portfolio.get_holding_quantity(symbol)
        average_cost = portfolio.get_average_cost(symbol)
        
        return MockSecurityModel(
            portfolio_id=portfolio_id,
            symbol_ticker=security.symbol.ticker,
            symbol_exchange=security.symbol.exchange,
            security_type=security.security_type.value,
            current_price=security.price,
            bid_price=security.bid,
            ask_price=security.ask,
            volume=security.volume,
            daily_open=security.open,
            daily_high=security.high,
            daily_low=security.low,
            daily_close=security.close,
            holdings_quantity=holdings_quantity,
            average_cost=average_cost,
            market_value=security.holdings.market_value,
            unrealized_pnl=security.holdings.unrealized_pnl,
            realized_pnl=security.holdings.realized_pnl,
            volatility=security.calculate_volatility(),
            beta=None,  # Would be calculated separately
            correlation=None,  # Would be calculated separately
            is_tradeable=security.is_tradeable,
            is_delisted=security.is_delisted,
            is_suspended=not security.is_tradeable and not security.is_delisted,
            market_data_cache=json.dumps(security._market_data_cache),
            price_history=json.dumps([
                {
                    'timestamp': data.timestamp.isoformat(),
                    'price': float(data.price),
                    'volume': data.volume
                }
                for data in security.get_price_history(50)  # Last 50 data points
            ]),
            contract_multiplier=security.get_contract_multiplier(),
            tick_size=0.01,  # Default
            margin_requirement=0.5,  # Default 50%
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_market_update=security.last_update
        )
    
    def _create_portfolio_snapshot(
        self, 
        portfolio_model: MockPortfolioModel, 
        portfolio: MockPortfolio
    ) -> MockPortfolioSnapshot:
        """Create portfolio snapshot from current state."""
        return MockPortfolioSnapshot(
            portfolio_id=portfolio_model.id,
            snapshot_date=datetime.now(),
            cash=portfolio.cash,
            total_portfolio_value=portfolio.total_portfolio_value,
            holdings_value=portfolio.holdings_value,
            unrealized_pnl=sum(
                security.holdings.unrealized_pnl 
                for security in portfolio._securities.values()
            ),
            total_return_percent=portfolio_model.total_return_percent,
            drawdown_percent=portfolio_model.max_drawdown,
            holdings_snapshot=json.dumps({
                symbol: {
                    'quantity': float(quantity),
                    'price': float(portfolio.get_security(symbol).price) if portfolio.get_security(symbol) else 0,
                    'value': float(portfolio.get_holding_value(symbol))
                }
                for symbol, quantity in portfolio.get_holdings().items()
                if quantity != 0
            })
        )