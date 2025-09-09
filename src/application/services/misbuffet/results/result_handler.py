"""
Result handler for misbuffet backtesting operations.
Processes and manages backtest results using domain entities and infrastructure models.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from domain.entities.back_testing import MockPortfolio, MockSecurity, MockPortfolioStatistics


@dataclass
class BacktestResult:
    """
    Value object representing the complete result of a backtest.
    Contains performance metrics, statistics, and detailed logs.
    """
    # Basic information
    backtest_id: str
    algorithm_name: str
    start_date: datetime
    end_date: datetime
    duration_days: int
    
    # Performance metrics
    initial_capital: Decimal
    final_capital: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    annual_return_percent: Decimal
    
    # Risk metrics
    max_drawdown: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    
    # Trading statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    average_win: Decimal
    average_loss: Decimal
    profit_factor: Decimal
    
    # Portfolio statistics
    portfolio_statistics: MockPortfolioStatistics
    
    # Holdings summary
    final_holdings: Dict[str, Dict[str, Any]]  # symbol -> {quantity, value, pnl}
    
    # Transaction log
    transaction_log: List[Dict[str, Any]]
    
    # Performance timeline
    equity_curve: List[Dict[str, Any]]  # timestamp -> portfolio_value
    drawdown_curve: List[Dict[str, Any]]  # timestamp -> drawdown_percent
    
    # Execution details
    execution_time_seconds: float
    data_points_processed: int
    errors: List[str]
    warnings: List[str]
    
    def summary(self) -> str:
        """Generate a human-readable summary of the backtest results."""
        return (
            f"Backtest Results Summary\n"
            f"========================\n"
            f"Algorithm: {self.algorithm_name}\n"
            f"Period: {self.start_date.date()} to {self.end_date.date()} ({self.duration_days} days)\n"
            f"Initial Capital: ${self.initial_capital:,.2f}\n"
            f"Final Capital: ${self.final_capital:,.2f}\n"
            f"Total Return: ${self.total_return:,.2f} ({self.total_return_percent:.2f}%)\n"
            f"Annualized Return: {self.annual_return_percent:.2f}%\n"
            f"Max Drawdown: {self.max_drawdown:.2f}%\n"
            f"Sharpe Ratio: {self.sharpe_ratio:.2f}\n"
            f"Total Trades: {self.total_trades}\n"
            f"Win Rate: {self.win_rate:.1f}%\n"
            f"Profit Factor: {self.profit_factor:.2f}\n"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        
        # Convert Decimal values to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        return convert_decimals(result)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class BacktestResultHandler:
    """
    Handler for processing and managing backtest results.
    Integrates with domain entities and infrastructure models.
    """
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self._start_time: Optional[datetime] = None
    
    def start_processing(self) -> None:
        """Mark start of result processing."""
        self._start_time = datetime.now()
        self.errors.clear()
        self.warnings.clear()
    
    def process_backtest_result(
        self,
        backtest_id: str,
        algorithm_name: str,
        portfolio: MockPortfolio,
        start_date: datetime,
        end_date: datetime,
        data_points_processed: int = 0
    ) -> BacktestResult:
        """
        Process a completed backtest and generate comprehensive results.
        
        Args:
            backtest_id: Unique identifier for the backtest
            algorithm_name: Name of the algorithm that was tested
            portfolio: Final portfolio state
            start_date: Backtest start date
            end_date: Backtest end date
            data_points_processed: Number of data points processed
            
        Returns:
            BacktestResult object with all metrics and analysis
        """
        try:
            # Calculate basic metrics
            initial_capital = portfolio._initial_cash
            final_capital = portfolio.total_portfolio_value
            total_return = final_capital - initial_capital
            total_return_percent = (total_return / initial_capital) * Decimal('100')
            
            duration_days = (end_date - start_date).days
            annual_return_percent = self._calculate_annual_return(
                total_return_percent, duration_days
            )
            
            # Get portfolio statistics
            portfolio_stats = portfolio.calculate_statistics()
            
            # Process trading statistics
            transactions = portfolio.get_transaction_history()
            trading_stats = self._calculate_trading_statistics(transactions, portfolio)
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(
                portfolio, total_return_percent, duration_days
            )
            
            # Build final holdings summary
            final_holdings = self._build_holdings_summary(portfolio)
            
            # Generate equity and drawdown curves
            equity_curve = self._generate_equity_curve(portfolio)
            drawdown_curve = self._generate_drawdown_curve(portfolio)
            
            # Calculate execution time
            execution_time = (
                (datetime.now() - self._start_time).total_seconds()
                if self._start_time else 0.0
            )
            
            return BacktestResult(
                backtest_id=backtest_id,
                algorithm_name=algorithm_name,
                start_date=start_date,
                end_date=end_date,
                duration_days=duration_days,
                initial_capital=initial_capital,
                final_capital=final_capital,
                total_return=total_return,
                total_return_percent=total_return_percent,
                annual_return_percent=annual_return_percent,
                max_drawdown=portfolio_stats.max_drawdown,
                volatility=portfolio_stats.volatility,
                sharpe_ratio=risk_metrics['sharpe_ratio'],
                sortino_ratio=risk_metrics['sortino_ratio'],
                calmar_ratio=risk_metrics['calmar_ratio'],
                total_trades=trading_stats['total_trades'],
                winning_trades=trading_stats['winning_trades'],
                losing_trades=trading_stats['losing_trades'],
                win_rate=trading_stats['win_rate'],
                average_win=trading_stats['average_win'],
                average_loss=trading_stats['average_loss'],
                profit_factor=trading_stats['profit_factor'],
                portfolio_statistics=portfolio_stats,
                final_holdings=final_holdings,
                transaction_log=transactions,
                equity_curve=equity_curve,
                drawdown_curve=drawdown_curve,
                execution_time_seconds=execution_time,
                data_points_processed=data_points_processed,
                errors=self.errors.copy(),
                warnings=self.warnings.copy()
            )
            
        except Exception as e:
            self.errors.append(f"Error processing backtest results: {str(e)}")
            raise
    
    def _calculate_annual_return(self, total_return_percent: Decimal, days: int) -> Decimal:
        """Calculate annualized return."""
        if days <= 0:
            return Decimal('0')
        
        years = Decimal(days) / Decimal('365.25')
        if years <= 0:
            return Decimal('0')
        
        # Compound annual growth rate formula
        if total_return_percent > -100:  # Avoid negative base for fractional power
            annual_rate = ((Decimal('1') + total_return_percent / Decimal('100')) ** (Decimal('1') / years) - Decimal('1')) * Decimal('100')
            return annual_rate
        else:
            return Decimal('-100')  # Total loss
    
    def _calculate_trading_statistics(
        self, transactions: List[Dict], portfolio: MockPortfolio
    ) -> Dict[str, Any]:
        """Calculate trading performance statistics."""
        if not transactions:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': Decimal('0'),
                'average_win': Decimal('0'),
                'average_loss': Decimal('0'),
                'profit_factor': Decimal('0')
            }
        
        # Group transactions by symbol to calculate P&L per trade
        trades_pnl = []
        symbol_positions = {}
        
        for transaction in transactions:
            symbol = transaction['symbol']
            quantity = transaction['quantity']
            price = transaction['price']
            
            if symbol not in symbol_positions:
                symbol_positions[symbol] = {'quantity': Decimal('0'), 'avg_cost': Decimal('0')}
            
            position = symbol_positions[symbol]
            
            if transaction['type'] == 'BUY':
                # Update position
                if position['quantity'] == 0:
                    position['avg_cost'] = price
                else:
                    total_cost = position['quantity'] * position['avg_cost'] + quantity * price
                    position['avg_cost'] = total_cost / (position['quantity'] + quantity)
                position['quantity'] += quantity
            
            else:  # SELL
                if position['quantity'] > 0:
                    # Calculate P&L for this sale
                    pnl_per_share = price - position['avg_cost']
                    total_pnl = pnl_per_share * quantity
                    trades_pnl.append(total_pnl)
                    
                    position['quantity'] -= quantity
        
        # Calculate statistics from trade P&Ls
        if not trades_pnl:
            return {
                'total_trades': len(transactions),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': Decimal('0'),
                'average_win': Decimal('0'),
                'average_loss': Decimal('0'),
                'profit_factor': Decimal('0')
            }
        
        winning_trades = [pnl for pnl in trades_pnl if pnl > 0]
        losing_trades = [pnl for pnl in trades_pnl if pnl < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        total_trades = len(trades_pnl)
        
        win_rate = Decimal(win_count) / Decimal(total_trades) * Decimal('100') if total_trades > 0 else Decimal('0')
        average_win = sum(winning_trades) / Decimal(win_count) if win_count > 0 else Decimal('0')
        average_loss = sum(losing_trades) / Decimal(loss_count) if loss_count > 0 else Decimal('0')
        
        # Profit factor = gross profits / gross losses
        gross_profits = sum(winning_trades) if winning_trades else Decimal('0')
        gross_losses = abs(sum(losing_trades)) if losing_trades else Decimal('0')
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else Decimal('0')
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor
        }
    
    def _calculate_risk_metrics(
        self, portfolio: MockPortfolio, total_return_percent: Decimal, duration_days: int
    ) -> Dict[str, Decimal]:
        """Calculate risk-adjusted performance metrics."""
        # Simplified risk metrics for mock implementation
        volatility = Decimal('15')  # Placeholder
        max_drawdown = portfolio.calculate_statistics().max_drawdown
        
        # Sharpe ratio (simplified - assuming 2% risk-free rate)
        risk_free_rate = Decimal('2')
        annual_return = self._calculate_annual_return(total_return_percent, duration_days)
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else Decimal('0')
        
        # Sortino ratio (simplified - using same volatility)
        sortino_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else Decimal('0')
        
        # Calmar ratio
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else Decimal('0')
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio
        }
    
    def _build_holdings_summary(self, portfolio: MockPortfolio) -> Dict[str, Dict[str, Any]]:
        """Build summary of final holdings."""
        holdings_summary = {}
        
        for symbol, quantity in portfolio.get_holdings().items():
            if quantity != 0:
                security = portfolio.get_security(symbol)
                avg_cost = portfolio.get_average_cost(symbol)
                market_value = portfolio.get_holding_value(symbol)
                unrealized_pnl = (security.price - avg_cost) * quantity if security else Decimal('0')
                
                holdings_summary[symbol] = {
                    'quantity': float(quantity),
                    'average_cost': float(avg_cost),
                    'current_price': float(security.price) if security else 0.0,
                    'market_value': float(market_value),
                    'unrealized_pnl': float(unrealized_pnl),
                    'weight': float(market_value / portfolio.total_portfolio_value * 100) if portfolio.total_portfolio_value > 0 else 0.0
                }
        
        return holdings_summary
    
    def _generate_equity_curve(self, portfolio: MockPortfolio) -> List[Dict[str, Any]]:
        """Generate equity curve data points."""
        # Simplified - in real implementation, this would use historical snapshots
        current_time = datetime.now()
        return [
            {
                'timestamp': current_time.isoformat(),
                'portfolio_value': float(portfolio.total_portfolio_value),
                'cash': float(portfolio.cash),
                'holdings_value': float(portfolio.holdings_value)
            }
        ]
    
    def _generate_drawdown_curve(self, portfolio: MockPortfolio) -> List[Dict[str, Any]]:
        """Generate drawdown curve data points."""
        # Simplified - in real implementation, this would calculate drawdown over time
        current_time = datetime.now()
        max_drawdown = portfolio.calculate_statistics().max_drawdown
        
        return [
            {
                'timestamp': current_time.isoformat(),
                'drawdown_percent': float(max_drawdown)
            }
        ]
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(f"{datetime.now().isoformat()}: {message}")
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(f"{datetime.now().isoformat()}: {message}")