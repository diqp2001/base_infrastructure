"""
Result storage for backtest results.
Handles persistence using infrastructure models and DDD principles.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from src.domain.entities.finance.financial_assets.security import Security
from domain.entities.finance.portfolio.portfolio import Portfolio, PortfolioStatistics
from src.infrastructure.models.finance.market_data import MarketDataModel
from src.infrastructure.models.finance.portfolio import Portfolio as PortfolioModel
from src.infrastructure.models.finance.security_holdings import SecurityHoldingsModel
from src.infrastructure.models.finance.portfolio_holdings import PortfolioHoldingsModel
from src.infrastructure.models.finance.portfolio_statistics import PortfolioStatisticsModel

#from domain.entities.finance.portfolio import Portfolio

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
        portfolio: Portfolio
    ) -> PortfolioModel:
        """
        Save complete backtest result to database.
        
        Args:
            result: BacktestResult to save
            portfolio: Final portfolio state
            
        Returns:
            Saved PortfolioModel instance
        """
        # Create portfolio model from domain entity
        portfolio_model = self._create_portfolio_model(result, portfolio)
        
        # Save to database
        self.db_session.add(portfolio_model)
        self.db_session.commit()
        
        # Save portfolio statistics
        if hasattr(result, 'portfolio_statistics'):
            self._save_portfolio_statistics(portfolio_model.id, result.portfolio_statistics)
        
        # Save holdings
        self._save_portfolio_holdings(portfolio_model.id, portfolio)
        
        return portfolio_model
    
    def create_portfolio_snapshot(
        self, 
        portfolio_model: PortfolioModel, 
        portfolio: Portfolio, 
        snapshot_date: datetime
    ) -> PortfolioHoldingsModel:
        """Create portfolio snapshot for a specific point in time."""
        
        snapshot = PortfolioHoldingsModel(
            portfolio_id=portfolio_model.id,
            cash_balance=float(portfolio.cash_balance),
            total_value=float(portfolio.current_value),
            holdings_value=float(portfolio.invested_amount),
            holdings_data=self._serialize_holdings(portfolio.holdings),
            snapshot_date=snapshot_date,
            created_at=datetime.utcnow()
        )
        
        self.db_session.add(snapshot)
        self.db_session.commit()
        return snapshot
    
    def save_security_price_data(
        self, 
        security: Security, 
        timestamp: datetime, 
        price_data: Dict
    ) -> MarketDataModel:
        """Save security price snapshot."""
        
        # Create market data model
        market_data = MarketDataModel(
            symbol_ticker=security.symbol.ticker,
            symbol_exchange=security.symbol.exchange,
            security_type=security.symbol.security_type.value,
            timestamp=timestamp,
            price=float(price_data.get('price', 0)),
            volume=price_data.get('volume', 0),
            bid=float(price_data.get('bid', 0)) if price_data.get('bid') else None,
            ask=float(price_data.get('ask', 0)) if price_data.get('ask') else None,
            open=float(price_data.get('open', 0)) if price_data.get('open') else None,
            high=float(price_data.get('high', 0)) if price_data.get('high') else None,
            low=float(price_data.get('low', 0)) if price_data.get('low') else None,
            close=float(price_data.get('close', 0)) if price_data.get('close') else None,
            created_at=datetime.utcnow()
        )
        
        self.db_session.add(market_data)
        self.db_session.commit()
        return market_data
    
    def load_backtest_result(self, backtest_id: str) -> Optional[PortfolioModel]:
        """Load backtest result by ID."""
        return self.db_session.query(PortfolioModel).filter(
            PortfolioModel.backtest_id == backtest_id
        ).first()
    
    def get_portfolio_snapshots(
        self,
        portfolio_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PortfolioHoldingsModel]:
        """Get portfolio snapshots within date range."""
        
        query = self.db_session.query(PortfolioHoldingsModel).filter(
            PortfolioHoldingsModel.portfolio_id == portfolio_id
        )
        
        if start_date:
            query = query.filter(PortfolioHoldingsModel.snapshot_date >= start_date)
        if end_date:
            query = query.filter(PortfolioHoldingsModel.snapshot_date <= end_date)
        
        return query.order_by(PortfolioHoldingsModel.snapshot_date).all()
    
    def get_security_price_history(
        self,
        symbol_ticker: str,
        symbol_exchange: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MarketDataModel]:
        """Get security price history within date range."""
        
        query = self.db_session.query(MarketDataModel).filter(
            MarketDataModel.symbol_ticker == symbol_ticker,
            MarketDataModel.symbol_exchange == symbol_exchange
        )
        
        if start_date:
            query = query.filter(MarketDataModel.timestamp >= start_date)
        if end_date:
            query = query.filter(MarketDataModel.timestamp <= end_date)
        
        return query.order_by(MarketDataModel.timestamp).all()
    
    def get_recent_backtests(self, limit: int = 10) -> List[PortfolioModel]:
        """Get recent backtest results."""
        portfolios = self.db_session.query(PortfolioModel).filter(
            PortfolioModel.backtest_id.isnot(None)
        ).order_by(
            PortfolioModel.created_at.desc()
        ).limit(limit).all()
        
        return portfolios
    
    def delete_backtest_result(self, portfolio: PortfolioModel):
        """Delete backtest result and all related data."""
        portfolio_id = portfolio.id
        
        # Delete market data (if any direct relationships exist)
        # Note: MarketDataModel doesn't have direct FK to portfolio, so skip
        
        # Delete portfolio holdings snapshots
        self.db_session.query(PortfolioHoldingsModel).filter(
            PortfolioHoldingsModel.portfolio_id == portfolio_id
        ).delete()
        
        # Delete security holdings
        self.db_session.query(SecurityHoldingsModel).filter(
            SecurityHoldingsModel.portfolio_id == portfolio_id
        ).delete()
        
        # Delete portfolio statistics
        self.db_session.query(PortfolioStatisticsModel).filter(
            PortfolioStatisticsModel.portfolio_id == portfolio_id
        ).delete()
        
        # Delete portfolio itself
        self.db_session.delete(portfolio)
        self.db_session.commit()
    
    def _create_portfolio_model(
        self, 
        result: BacktestResult, 
        portfolio: Portfolio
    ) -> PortfolioModel:
        """Create PortfolioModel from domain entities."""
        
        # Extract dates from result or use defaults
        start_date = getattr(result, 'start_date', None)
        end_date = getattr(result, 'end_date', None)
        
        return PortfolioModel(
            name=portfolio.name,
            portfolio_type=portfolio.portfolio_type.value,
            backtest_id=portfolio.backtest_id,
            initial_cash=float(portfolio.initial_cash),
            current_cash=float(portfolio.cash_balance),
            total_value=float(portfolio.current_value),
            cash_balance=float(portfolio.cash_balance),
            invested_amount=float(portfolio.invested_amount),
            holdings_value=float(portfolio.invested_amount),
            total_return=float(portfolio.statistics.total_return),
            total_return_percent=float(portfolio.statistics.total_return_percent),
            unrealized_pnl=float(portfolio.holdings.total_unrealized_pnl),
            realized_pnl=float(portfolio.holdings.total_realized_pnl),
            max_drawdown=float(portfolio.statistics.max_drawdown),
            high_water_mark=float(portfolio.statistics.high_water_mark),
            volatility=float(portfolio.statistics.volatility) if portfolio.statistics.volatility else None,
            sharpe_ratio=float(portfolio.statistics.sharpe_ratio) if portfolio.statistics.sharpe_ratio else None,
            beta=float(portfolio.statistics.beta) if portfolio.statistics.beta else None,
            alpha=float(portfolio.statistics.alpha) if portfolio.statistics.alpha else None,
            var_95=float(portfolio.statistics.var_95) if portfolio.statistics.var_95 else None,
            total_trades=portfolio.statistics.total_trades,
            winning_trades=portfolio.statistics.winning_trades,
            losing_trades=portfolio.statistics.losing_trades,
            win_rate=float(portfolio.statistics.win_rate),
            currency=portfolio.currency,
            is_active=portfolio.is_active,
            is_paper_trading=portfolio.is_paper_trading,
            inception_date=portfolio.inception_date,
            backtest_start_date=start_date,
            backtest_end_date=end_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_valuation_date=portfolio.last_valuation_date
        )
    
    def _save_portfolio_statistics(self, portfolio_id: int, statistics: PortfolioStatistics) -> PortfolioStatisticsModel:
        """Save portfolio statistics to database."""
        
        stats_model = PortfolioStatisticsModel(
            portfolio_id=portfolio_id,
            total_return=float(statistics.total_return),
            total_return_percent=float(statistics.total_return_percent),
            max_drawdown=float(statistics.max_drawdown),
            high_water_mark=float(statistics.high_water_mark),
            volatility=float(statistics.volatility) if statistics.volatility else None,
            sharpe_ratio=float(statistics.sharpe_ratio) if statistics.sharpe_ratio else None,
            beta=float(statistics.beta) if statistics.beta else None,
            alpha=float(statistics.alpha) if statistics.alpha else None,
            var_95=float(statistics.var_95) if statistics.var_95 else None,
            tracking_error=float(statistics.tracking_error) if statistics.tracking_error else None,
            win_rate=float(statistics.win_rate),
            total_trades=statistics.total_trades,
            winning_trades=statistics.winning_trades,
            losing_trades=statistics.losing_trades,
            calculation_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        self.db_session.add(stats_model)
        self.db_session.commit()
        return stats_model
    
    def _save_portfolio_holdings(self, portfolio_id: int, portfolio: Portfolio):
        """Save individual security holdings to database."""
        
        for symbol, holding in portfolio.holdings.holdings.items():
            holding_model = SecurityHoldingsModel(
                portfolio_id=portfolio_id,
                symbol_ticker=symbol.ticker,
                symbol_exchange=symbol.exchange,
                security_type=symbol.security_type.value,
                quantity=float(holding.quantity),
                average_cost=float(holding.average_cost),
                market_value=float(holding.market_value),
                unrealized_pnl=float(holding.unrealized_pnl),
                realized_pnl=float(holding.realized_pnl),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(holding_model)
        
        self.db_session.commit()
    
    def _serialize_holdings(self, holdings) -> str:
        """Serialize portfolio holdings to JSON."""
        holdings_dict = {}
        for symbol, holding in holdings.holdings.items():
            holdings_dict[str(symbol)] = {
                'quantity': float(holding.quantity),
                'average_cost': float(holding.average_cost),
                'market_value': float(holding.market_value),
                'unrealized_pnl': float(holding.unrealized_pnl),
                'realized_pnl': float(holding.realized_pnl)
            }
        
        return json.dumps(holdings_dict)
    
    def _create_portfolio_snapshot_model(
        self, 
        portfolio_model: PortfolioModel, 
        portfolio: Portfolio
    ) -> PortfolioHoldingsModel:
        """Create holdings snapshot model."""
        
        return PortfolioHoldingsModel(
            portfolio_id=portfolio_model.id,
            cash_balance=float(portfolio.cash_balance),
            total_value=float(portfolio.current_value),
            holdings_value=float(portfolio.invested_amount),
            holdings_data=self._serialize_holdings(portfolio.holdings),
            snapshot_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )