from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List
import inspect
from functools import wraps

from .scheduling import schedule_function, DateRules, TimeRules, DayOfWeek
from .enums import Resolution, SecurityType


class AlgorithmUtilities:
    """
    Collection of utility functions for algorithm development.
    """
    
    @staticmethod
    def percentage_change(old_value: float, new_value: float) -> float:
        """Calculate percentage change between two values"""
        if old_value == 0:
            return 0.0
        return (new_value - old_value) / old_value * 100.0
    
    @staticmethod
    def normalize_to_range(value: float, old_min: float, old_max: float, 
                          new_min: float = 0.0, new_max: float = 1.0) -> float:
        """Normalize a value from one range to another"""
        if old_max == old_min:
            return new_min
        return new_min + (value - old_min) * (new_max - new_min) / (old_max - old_min)
    
    @staticmethod
    def round_to_tick_size(price: float, tick_size: float = 0.01) -> float:
        """Round price to the nearest tick size"""
        if tick_size <= 0:
            return price
        return round(price / tick_size) * tick_size
    
    @staticmethod
    def calculate_position_size(portfolio_value: float, risk_percentage: float, 
                               entry_price: float, stop_loss_price: float) -> int:
        """
        Calculate position size based on risk management parameters.
        
        Args:
            portfolio_value: Total portfolio value
            risk_percentage: Percentage of portfolio to risk (0.0-1.0)
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            
        Returns:
            Position size in shares
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0
        
        risk_amount = portfolio_value * risk_percentage
        price_difference = abs(entry_price - stop_loss_price)
        
        if price_difference == 0:
            return 0
        
        position_size = int(risk_amount / price_difference)
        return max(0, position_size)
    
    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio for a series of returns.
        
        Args:
            returns: List of period returns
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        # Adjust risk-free rate for period
        period_risk_free = risk_free_rate / 252  # Assuming daily returns
        
        return (avg_return - period_risk_free) / std_dev
    
    @staticmethod
    def max_drawdown(values: List[float]) -> float:
        """
        Calculate maximum drawdown from a series of portfolio values.
        
        Args:
            values: List of portfolio values over time
            
        Returns:
            Maximum drawdown as a percentage (negative value)
        """
        if not values or len(values) < 2:
            return 0.0
        
        peak = values[0]
        max_dd = 0.0
        
        for value in values[1:]:
            if value > peak:
                peak = value
            
            drawdown = (value - peak) / peak
            if drawdown < max_dd:
                max_dd = drawdown
        
        return max_dd * 100.0  # Convert to percentage
    
    @staticmethod
    def volatility(returns: List[float], periods_per_year: int = 252) -> float:
        """
        Calculate annualized volatility from returns.
        
        Args:
            returns: List of period returns
            periods_per_year: Number of periods in a year (252 for daily)
            
        Returns:
            Annualized volatility
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        
        return (variance ** 0.5) * (periods_per_year ** 0.5)


class PerformanceMetrics:
    """
    Performance metrics calculation utilities.
    """
    
    def __init__(self):
        self.trades: List[Dict[str, Any]] = []
        self.portfolio_values: List[float] = []
        self.returns: List[float] = []
    
    def add_trade(self, entry_price: float, exit_price: float, quantity: int, 
                  entry_time: datetime, exit_time: datetime, symbol: str = ""):
        """Add a completed trade for analysis"""
        pnl = (exit_price - entry_price) * quantity
        trade = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'pnl': pnl,
            'return_pct': (exit_price - entry_price) / entry_price * 100.0,
            'duration': exit_time - entry_time
        }
        self.trades.append(trade)
    
    def add_portfolio_value(self, value: float):
        """Add portfolio value for tracking"""
        if self.portfolio_values:
            last_value = self.portfolio_values[-1]
            if last_value > 0:
                return_pct = (value - last_value) / last_value
                self.returns.append(return_pct)
        
        self.portfolio_values.append(value)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        if not self.trades:
            return {}
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0.0
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        profit_factor = abs(avg_win * len(winning_trades) / (avg_loss * len(losing_trades))) if avg_loss != 0 else float('inf')
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': AlgorithmUtilities.sharpe_ratio(self.returns) if self.returns else 0.0,
            'max_drawdown': AlgorithmUtilities.max_drawdown(self.portfolio_values) if self.portfolio_values else 0.0,
            'volatility': AlgorithmUtilities.volatility(self.returns) if self.returns else 0.0
        }


def schedule(func, date_rule=None, time_rule=None, name: str = ""):
    """
    Schedule a function to run based on date and time rules.
    
    Args:
        func: The function to schedule
        date_rule: Date-based rule (from DateRules)
        time_rule: Time-based rule (from TimeRules)
        name: Optional name for the scheduled event
    
    Returns:
        Event ID for the scheduled function
    """
    return schedule_function(func, name=name, date_rule=date_rule, time_rule=time_rule)


def set_runtime_parameters(**kwargs):
    """
    Set runtime parameters for the algorithm.
    This is a placeholder that can be extended for specific runtime configurations.
    """
    runtime_config = {
        'start_date': kwargs.get('start_date'),
        'end_date': kwargs.get('end_date'),
        'initial_cash': kwargs.get('initial_cash', 100000),
        'benchmark': kwargs.get('benchmark'),
        'brokerage_model': kwargs.get('brokerage_model'),
        'security_initializer': kwargs.get('security_initializer'),
        'warmup_period': kwargs.get('warmup_period', timedelta(days=0))
    }
    
    print("Runtime configuration set:")
    for key, value in runtime_config.items():
        if value is not None:
            print(f"  {key}: {value}")


def set_warmup(period: Union[int, timedelta], resolution: Resolution = Resolution.DAILY):
    """
    Set the warmup period for the algorithm.
    
    Args:
        period: Warmup period (int for number of bars, timedelta for time period)
        resolution: Resolution for warmup bars
    """
    if isinstance(period, int):
        print(f"Warmup set to {period} bars at {resolution.value} resolution")
    else:
        print(f"Warmup set to {period} time period")


def set_cash(amount: float):
    """Set the starting cash for the algorithm"""
    print(f"Starting cash set to ${amount:,.2f}")


def set_start_date(date: datetime):
    """Set the algorithm start date"""
    print(f"Algorithm start date set to {date.strftime('%Y-%m-%d')}")


def set_end_date(date: datetime):
    """Set the algorithm end date"""
    print(f"Algorithm end date set to {date.strftime('%Y-%m-%d')}")


def set_benchmark(symbol: str):
    """Set the benchmark for performance comparison"""
    print(f"Benchmark set to {symbol}")


# Convenience functions for scheduling
class Schedule:
    """
    Convenience class for algorithm scheduling with fluent interface.
    """
    
    @staticmethod
    def on(date_rule):
        """Schedule based on date rule"""
        return ScheduleBuilder(date_rule=date_rule)
    
    @staticmethod
    def every(date_rule):
        """Schedule every period based on date rule"""
        return ScheduleBuilder(date_rule=date_rule)


class ScheduleBuilder:
    """
    Builder for creating scheduled events with fluent interface.
    """
    
    def __init__(self, date_rule=None, time_rule=None):
        self.date_rule = date_rule
        self.time_rule = time_rule
    
    def at(self, time_rule):
        """Set the time rule"""
        self.time_rule = time_rule
        return self
    
    def do(self, func, name: str = ""):
        """Execute the function with the configured rules"""
        return schedule(func, self.date_rule, self.time_rule, name)


# Legacy compatibility functions
def set_runtime(config):
    """Legacy function for setting runtime configuration"""
    if isinstance(config, dict):
        set_runtime_parameters(**config)
    else:
        print("Runtime configuration set:", config)
