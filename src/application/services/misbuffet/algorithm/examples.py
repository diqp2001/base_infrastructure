"""
Example algorithms demonstrating the QuantConnect-style framework usage.
These examples show how to implement common trading strategies using the QCAlgorithm base class.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from .base import QCAlgorithm
from .data_handlers import Slice
from .symbol import Symbol
from .enums import Resolution, OrderType
from .scheduling import DateRules, TimeRules
from .utils import AlgorithmUtilities


class BuyAndHoldAlgorithm(QCAlgorithm):
    """
    Simple Buy and Hold strategy that purchases SPY and holds it.
    """
    
    def initialize(self):
        """Initialize the algorithm"""
        # Set algorithm parameters
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(100000)
        
        # Add SPY with daily resolution
        self.spy = self.add_equity("SPY", Resolution.DAILY)
        
        # Set benchmark
        self.set_benchmark("SPY")
        
        # Flag to ensure we only buy once
        self.invested = False
        
        self.log("Buy and Hold Algorithm initialized")
    
    def on_data(self, data: Slice):
        """Handle market data"""
        if not self.invested and data.contains_key(self.spy.symbol):
            # Invest all cash in SPY
            self.set_holdings(self.spy.symbol, 1.0)
            self.invested = True
            self.log(f"Purchased SPY at ${data[self.spy.symbol].price:.2f}")
    
    def on_end_of_algorithm(self):
        """Called when algorithm finishes"""
        self.log(f"Final portfolio value: ${self.portfolio.total_portfolio_value:,.2f}")


class MovingAverageCrossoverAlgorithm(QCAlgorithm):
    """
    Moving Average Crossover strategy using two EMAs.
    Buys when short EMA crosses above long EMA, sells when it crosses below.
    """
    
    def initialize(self):
        """Initialize the algorithm"""
        # Set algorithm parameters
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(100000)
        
        # Add equity
        self.symbol = self.add_equity("AAPL", Resolution.DAILY).symbol
        
        # Set benchmark
        self.set_benchmark("SPY")
        
        # Moving average parameters
        self.short_period = 10
        self.long_period = 30
        
        # Price history for calculating moving averages
        self.price_history = []
        self.short_ema = None
        self.long_ema = None
        self.previous_short_ema = None
        self.previous_long_ema = None
        
        self.log("Moving Average Crossover Algorithm initialized")
    
    def on_data(self, data: Slice):
        """Handle market data"""
        if not data.contains_key(self.symbol):
            return
        
        price = data[self.symbol].close
        self.price_history.append(price)
        
        # Need enough data for long moving average
        if len(self.price_history) < self.long_period:
            return
        
        # Calculate EMAs
        self.previous_short_ema = self.short_ema
        self.previous_long_ema = self.long_ema
        
        self.short_ema = self._calculate_ema(self.price_history[-self.short_period:], self.short_period)
        self.long_ema = self._calculate_ema(self.price_history[-self.long_period:], self.long_period)
        
        # Check for crossover signals
        if self.previous_short_ema and self.previous_long_ema:
            # Golden cross: short EMA crosses above long EMA
            if (self.previous_short_ema <= self.previous_long_ema and 
                self.short_ema > self.long_ema and 
                not self.portfolio.is_invested(self.symbol)):
                
                self.set_holdings(self.symbol, 1.0)
                self.log(f"BUY signal: Short EMA ({self.short_ema:.2f}) crossed above Long EMA ({self.long_ema:.2f})")
            
            # Death cross: short EMA crosses below long EMA
            elif (self.previous_short_ema >= self.previous_long_ema and 
                  self.short_ema < self.long_ema and 
                  self.portfolio.is_invested(self.symbol)):
                
                self.liquidate(self.symbol)
                self.log(f"SELL signal: Short EMA ({self.short_ema:.2f}) crossed below Long EMA ({self.long_ema:.2f})")
    
    def _calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        if not prices:
            return 0.0
        
        multiplier = 2.0 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema


class MeanReversionAlgorithm(QCAlgorithm):
    """
    Mean reversion strategy that trades when price deviates significantly from moving average.
    """
    
    def initialize(self):
        """Initialize the algorithm"""
        # Set algorithm parameters
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(100000)
        
        # Add equity
        self.symbol = self.add_equity("QQQ", Resolution.DAILY).symbol
        
        # Strategy parameters
        self.lookback_period = 20
        self.deviation_threshold = 2.0  # Number of standard deviations
        
        # Data storage
        self.price_history = []
        
        # Position sizing
        self.position_size = 0.5  # 50% of portfolio
        
        self.log("Mean Reversion Algorithm initialized")
    
    def on_data(self, data: Slice):
        """Handle market data"""
        if not data.contains_key(self.symbol):
            return
        
        price = data[self.symbol].close
        self.price_history.append(price)
        
        # Need enough data for analysis
        if len(self.price_history) < self.lookback_period:
            return
        
        # Keep only recent prices
        if len(self.price_history) > self.lookback_period:
            self.price_history.pop(0)
        
        # Calculate statistics
        recent_prices = self.price_history[-self.lookback_period:]
        mean_price = sum(recent_prices) / len(recent_prices)
        variance = sum((p - mean_price) ** 2 for p in recent_prices) / len(recent_prices)
        std_dev = variance ** 0.5
        
        # Calculate z-score
        z_score = (price - mean_price) / std_dev if std_dev > 0 else 0
        
        current_holding = self.portfolio.get_holding(self.symbol)
        is_invested = current_holding and current_holding.is_invested
        
        # Mean reversion signals
        if z_score < -self.deviation_threshold and not is_invested:
            # Price is significantly below average - buy
            self.set_holdings(self.symbol, self.position_size)
            self.log(f"BUY signal: Price ${price:.2f} is {abs(z_score):.2f} std devs below mean ${mean_price:.2f}")
        
        elif z_score > self.deviation_threshold and is_invested:
            # Price is significantly above average - sell
            self.liquidate(self.symbol)
            self.log(f"SELL signal: Price ${price:.2f} is {z_score:.2f} std devs above mean ${mean_price:.2f}")
        
        elif abs(z_score) < 0.5 and is_invested:
            # Price has returned close to mean - exit position
            self.liquidate(self.symbol)
            self.log(f"EXIT signal: Price ${price:.2f} returned to mean ${mean_price:.2f}")


class MomentumAlgorithm(QCAlgorithm):
    """
    Momentum strategy that buys stocks showing strong recent performance.
    """
    
    def initialize(self):
        """Initialize the algorithm"""
        # Set algorithm parameters
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(100000)
        
        # Add multiple equities
        self.symbols = []
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        
        for ticker in tickers:
            symbol = self.add_equity(ticker, Resolution.DAILY).symbol
            self.symbols.append(symbol)
        
        # Strategy parameters
        self.lookback_period = 21  # 21 trading days for momentum calculation
        self.rebalance_frequency = 21  # Rebalance every 21 days
        self.num_positions = 2  # Hold top 2 momentum stocks
        
        # Data storage
        self.price_data = {symbol: [] for symbol in self.symbols}
        self.last_rebalance = None
        
        # Schedule rebalancing
        self.schedule_function(
            self.rebalance,
            date_rule=DateRules.every_day(),
            time_rule=TimeRules.market_open()
        )
        
        self.log("Momentum Algorithm initialized")
    
    def on_data(self, data: Slice):
        """Handle market data"""
        # Store price data for all symbols
        for symbol in self.symbols:
            if data.contains_key(symbol):
                price = data[symbol].close
                self.price_data[symbol].append(price)
                
                # Keep only recent data
                if len(self.price_data[symbol]) > self.lookback_period + 5:
                    self.price_data[symbol].pop(0)
    
    def rebalance(self):
        """Rebalance portfolio based on momentum"""
        # Check if it's time to rebalance
        if (self.last_rebalance and 
            (self.time - self.last_rebalance).days < self.rebalance_frequency):
            return
        
        # Calculate momentum for each symbol
        momentum_scores = {}
        
        for symbol in self.symbols:
            if len(self.price_data[symbol]) >= self.lookback_period:
                prices = self.price_data[symbol]
                current_price = prices[-1]
                past_price = prices[-self.lookback_period]
                
                # Calculate momentum as percentage return
                momentum = (current_price - past_price) / past_price
                momentum_scores[symbol] = momentum
        
        if not momentum_scores:
            return
        
        # Sort symbols by momentum (descending)
        sorted_symbols = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top momentum stocks
        selected_symbols = [symbol for symbol, score in sorted_symbols[:self.num_positions]]
        
        # Liquidate positions not in selected list
        current_positions = self.portfolio.get_positions()
        for symbol in current_positions:
            if symbol not in selected_symbols:
                self.liquidate(symbol)
        
        # Allocate equally among selected symbols
        target_weight = 1.0 / len(selected_symbols) if selected_symbols else 0.0
        
        for symbol in selected_symbols:
            self.set_holdings(symbol, target_weight)
            momentum = momentum_scores[symbol]
            self.log(f"Selected {symbol} with momentum {momentum:.2%}")
        
        self.last_rebalance = self.time
        self.log(f"Rebalanced portfolio with {len(selected_symbols)} positions")


class RiskManagementAlgorithm(QCAlgorithm):
    """
    Algorithm demonstrating risk management techniques including stop losses and position sizing.
    """
    
    def initialize(self):
        """Initialize the algorithm"""
        # Set algorithm parameters
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(100000)
        
        # Add equity
        self.symbol = self.add_equity("SPY", Resolution.DAILY).symbol
        
        # Risk management parameters
        self.max_risk_per_trade = 0.02  # Risk 2% of portfolio per trade
        self.stop_loss_percentage = 0.05  # 5% stop loss
        self.max_portfolio_risk = 0.10  # Maximum 10% portfolio risk
        
        # Trade tracking
        self.entry_price = None
        self.stop_loss_price = None
        self.position_size = 0
        
        # Simple momentum indicator
        self.price_history = []
        self.momentum_period = 10
        
        self.log("Risk Management Algorithm initialized")
    
    def on_data(self, data: Slice):
        """Handle market data"""
        if not data.contains_key(self.symbol):
            return
        
        current_price = data[self.symbol].close
        self.price_history.append(current_price)
        
        # Keep only recent prices
        if len(self.price_history) > self.momentum_period + 5:
            self.price_history.pop(0)
        
        current_holding = self.portfolio.get_holding(self.symbol)
        is_invested = current_holding and current_holding.is_invested
        
        if not is_invested:
            # Look for entry signal
            if len(self.price_history) >= self.momentum_period:
                # Simple momentum: current price > average of last N prices
                recent_avg = sum(self.price_history[-self.momentum_period:]) / self.momentum_period
                
                if current_price > recent_avg * 1.02:  # 2% above average
                    self._enter_position(current_price)
        else:
            # Check stop loss
            if self.stop_loss_price and current_price <= self.stop_loss_price:
                self._exit_position("Stop loss triggered")
            
            # Check for profit taking (simple trailing stop)
            elif current_price > self.entry_price * 1.1:  # 10% profit
                # Update stop loss to breakeven
                self.stop_loss_price = self.entry_price
                self.log(f"Updated stop loss to breakeven: ${self.stop_loss_price:.2f}")
    
    def _enter_position(self, price: float):
        """Enter position with risk management"""
        # Calculate position size based on risk
        stop_loss_price = price * (1 - self.stop_loss_percentage)
        risk_per_share = price - stop_loss_price
        
        # Calculate position size to risk max_risk_per_trade of portfolio
        portfolio_value = self.portfolio.total_portfolio_value
        max_risk_amount = portfolio_value * self.max_risk_per_trade
        position_size = int(max_risk_amount / risk_per_share)
        
        # Ensure we don't exceed available cash
        max_affordable = int(self.portfolio.cash / price)
        position_size = min(position_size, max_affordable)
        
        if position_size > 0:
            # Place the order
            self.market_order(self.symbol, position_size)
            
            # Store trade information
            self.entry_price = price
            self.stop_loss_price = stop_loss_price
            self.position_size = position_size
            
            risk_amount = position_size * risk_per_share
            risk_percentage = risk_amount / portfolio_value
            
            self.log(f"ENTERED position: {position_size} shares at ${price:.2f}")
            self.log(f"Stop loss: ${stop_loss_price:.2f}, Risk: ${risk_amount:.2f} ({risk_percentage:.2%})")
    
    def _exit_position(self, reason: str):
        """Exit current position"""
        if self.position_size > 0:
            self.liquidate(self.symbol)
            
            current_price = self.securities[self.symbol].price
            pnl = (current_price - self.entry_price) * self.position_size
            pnl_percentage = (current_price - self.entry_price) / self.entry_price
            
            self.log(f"EXITED position: {reason}")
            self.log(f"P&L: ${pnl:.2f} ({pnl_percentage:.2%})")
            
            # Reset tracking variables
            self.entry_price = None
            self.stop_loss_price = None
            self.position_size = 0