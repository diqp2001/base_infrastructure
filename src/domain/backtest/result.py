"""
Backtest result domain model.

Defines the schema for backtest results including performance metrics,
equity curves, trade logs, and risk analytics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4
import pandas as pd


@dataclass
class TradeRecord:
    """Individual trade record within a backtest."""
    
    trade_id: str
    symbol: str
    # Trade details
    side: str  # 'long' or 'short'
    quantity: int
    entry_price: Decimal
    entry_time: datetime
    # Costs
    entry_commission: Decimal = Decimal("0")
    exit_commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    
    # Metadata
    entry_signal: str = ""  # Reason for entry
    exit_signal: str = ""   # Reason for exit

    

    tags: Dict[str, str] = field(default_factory=dict)
    exit_time: Optional[datetime] = None
    
    #Trade details
    exit_price: Optional[Decimal] = None
    
    # Performance
    pnl: Optional[Decimal] = None  # Profit/Loss
    pnl_pct: Optional[Decimal] = None  # Percentage return
    
    

    
    
    def __post_init__(self):
        if self.trade_id is None:
            self.trade_id = str(uuid4())
    
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.exit_time is not None and self.exit_price is not None
    
    def duration_days(self) -> Optional[int]:
        """Calculate trade duration in days."""
        if not self.is_closed():
            return None
        return (self.exit_time - self.entry_time).days


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a backtest."""
    
    # Returns
    total_return: Decimal
    total_return_pct: Decimal
    annualized_return: Decimal
    
    # Risk metrics
    volatility: Decimal  # Annualized
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    max_drawdown_pct: Decimal
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    
    # Additional metrics
    profit_factor: Decimal  # Gross profit / Gross loss
    average_trade: Decimal
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    
    # Time-based metrics
    calmar_ratio: Decimal  # Annual return / Max drawdown
    var_95: Decimal  # 95% Value at Risk
    cvar_95: Decimal  # 95% Conditional Value at Risk
    
    # Benchmark comparison (optional)
    benchmark_return: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    information_ratio: Optional[Decimal] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_return': str(self.total_return),
            'total_return_pct': str(self.total_return_pct),
            'annualized_return': str(self.annualized_return),
            'volatility': str(self.volatility),
            'sharpe_ratio': str(self.sharpe_ratio),
            'sortino_ratio': str(self.sortino_ratio),
            'max_drawdown': str(self.max_drawdown),
            'max_drawdown_pct': str(self.max_drawdown_pct),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': str(self.win_rate),
            'profit_factor': str(self.profit_factor),
            'average_trade': str(self.average_trade),
            'average_win': str(self.average_win),
            'average_loss': str(self.average_loss),
            'largest_win': str(self.largest_win),
            'largest_loss': str(self.largest_loss),
            'calmar_ratio': str(self.calmar_ratio),
            'var_95': str(self.var_95),
            'cvar_95': str(self.cvar_95),
            'benchmark_return': str(self.benchmark_return) if self.benchmark_return else None,
            'alpha': str(self.alpha) if self.alpha else None,
            'beta': str(self.beta) if self.beta else None,
            'information_ratio': str(self.information_ratio) if self.information_ratio else None
        }


@dataclass
class EquityCurve:
    """Equity curve data for portfolio value over time."""
    
    timestamps: List[datetime]
    portfolio_values: List[Decimal]
    daily_returns: List[Decimal]
    drawdowns: List[Decimal]
    
    # Position data
    gross_exposure: List[Decimal] = field(default_factory=list)
    net_exposure: List[Decimal] = field(default_factory=list)
    num_positions: List[int] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for analysis."""
        df = pd.DataFrame({
            'timestamp': self.timestamps,
            'portfolio_value': self.portfolio_values,
            'daily_return': self.daily_returns,
            'drawdown': self.drawdowns
        })
        
        if self.gross_exposure:
            df['gross_exposure'] = self.gross_exposure
        if self.net_exposure:
            df['net_exposure'] = self.net_exposure
        if self.num_positions:
            df['num_positions'] = self.num_positions
        
        return df.set_index('timestamp')


@dataclass
class BacktestResult:
    """
    Complete backtest result containing all performance data and analytics.
    """
    
    # Identifiers
    result_id: str
    config_id: str  # Reference to BacktestConfig
    experiment_name: str
    run_name: Optional[str] = None
    
    # Execution metadata
    start_time: datetime = None
    end_time: datetime = None
    execution_duration_seconds: float = 0.0
    status: str = "completed"  # running, completed, failed, cancelled
    error_message: Optional[str] = None
    
    # Core results
    performance_metrics: Optional[PerformanceMetrics] = None
    equity_curve: Optional[EquityCurve] = None
    trades: List[TradeRecord] = field(default_factory=list)
    
    # Additional analytics
    factor_exposures: Dict[str, Decimal] = field(default_factory=dict)
    sector_attribution: Dict[str, Decimal] = field(default_factory=dict)
    monthly_returns: Dict[str, Decimal] = field(default_factory=dict)
    
    # Risk analytics
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    stress_test_results: Dict[str, Any] = field(default_factory=dict)
    
    # Model-specific results (if ML)
    model_metrics: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # System info
    system_info: Dict[str, str] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    
    # User metadata
    created_by: str = "system"
    tags: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    
    def __post_init__(self):
        """Initialize default values."""
        if self.result_id is None:
            self.result_id = str(uuid4())
        
        if self.start_time is None:
            self.start_time = datetime.utcnow()
    
    def get_total_pnl(self) -> Decimal:
        """Calculate total P&L from trades."""
        return sum(trade.pnl for trade in self.trades if trade.pnl is not None)
    
    def get_closed_trades(self) -> List[TradeRecord]:
        """Get only closed trades."""
        return [trade for trade in self.trades if trade.is_closed()]
    
    def get_open_trades(self) -> List[TradeRecord]:
        """Get only open trades."""
        return [trade for trade in self.trades if not trade.is_closed()]
    
    def add_trade(self, trade: TradeRecord):
        """Add a trade record."""
        self.trades.append(trade)
    
    def is_successful(self) -> bool:
        """Check if backtest completed successfully."""
        return self.status == "completed" and self.error_message is None
    
    def execution_duration_minutes(self) -> float:
        """Get execution duration in minutes."""
        return self.execution_duration_seconds / 60.0
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary for storage/display."""
        summary = {
            'result_id': self.result_id,
            'config_id': self.config_id,
            'experiment_name': self.experiment_name,
            'run_name': self.run_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'execution_duration_seconds': self.execution_duration_seconds,
            'status': self.status,
            'error_message': self.error_message,
            'total_trades': len(self.trades),
            'closed_trades': len(self.get_closed_trades()),
            'open_trades': len(self.get_open_trades()),
            'created_by': self.created_by,
            'tags': self.tags,
            'notes': self.notes
        }
        
        # Add performance metrics if available
        if self.performance_metrics:
            summary.update({
                'total_return_pct': str(self.performance_metrics.total_return_pct),
                'sharpe_ratio': str(self.performance_metrics.sharpe_ratio),
                'max_drawdown_pct': str(self.performance_metrics.max_drawdown_pct),
                'win_rate': str(self.performance_metrics.win_rate)
            })
        
        return summary


@dataclass
class BacktestComparison:
    """
    Comparison between multiple backtest results.
    """
    
    comparison_id: str
    name: str
    result_ids: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Comparative metrics
    relative_performance: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Statistical analysis
    significance_tests: Dict[str, Any] = field(default_factory=dict)
    risk_adjusted_rankings: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.comparison_id is None:
            self.comparison_id = str(uuid4())


@dataclass
class ResultSummary:
    """
    Lightweight summary of backtest results for listings and searches.
    """
    
    result_id: str
    experiment_name: str
    run_name: Optional[str]
    config_id: str
    
    # Key metrics
    total_return_pct: Decimal
    sharpe_ratio: Decimal
    max_drawdown_pct: Decimal
    
    # Execution info
    start_time: datetime
    duration_minutes: float
    status: str
    
    # Metadata
    tags: Dict[str, str]
    created_by: str