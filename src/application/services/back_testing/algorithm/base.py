from abc import ABC, abstractmethod
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime

from src.domain.entities.finance.portfolio import Portfolio
from src.domain.entities.finance.position import Position


class BacktestingAlgorithm(ABC):
    """Base class for backtesting trading algorithms."""
    
    def __init__(self, initial_capital: Decimal, name: str = "BacktestAlgorithm"):
        self.initial_capital = initial_capital
        self.name = name
        self.portfolio = Portfolio(
            id=1,
            name=f"{name}_Portfolio",
            initial_capital=initial_capital,
            created_date=datetime.now()
        )
        self.trade_history: List[Dict[str, Any]] = []
        
    @abstractmethod
    def generate_signals(self, market_data: Dict[str, Any], timestamp: datetime) -> Dict[str, str]:
        """
        Generate trading signals based on market data.
        
        Args:
            market_data: Dictionary containing market data for assets
            timestamp: Current timestamp in the backtest
            
        Returns:
            Dictionary mapping asset_id to signal ('BUY', 'SELL', 'HOLD')
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, asset_id: str, signal: str, 
                              current_price: Decimal, portfolio_value: Decimal) -> Decimal:
        """
        Calculate the position size for a given signal.
        
        Args:
            asset_id: Asset identifier
            signal: Trading signal ('BUY', 'SELL')
            current_price: Current price of the asset
            portfolio_value: Current total portfolio value
            
        Returns:
            Quantity to trade (positive for buy, negative for sell)
        """
        pass
    
    def execute_trade(self, asset_id: int, quantity: Decimal, price: Decimal, 
                     timestamp: datetime, trade_type: str) -> bool:
        """
        Execute a trade and update the portfolio.
        
        Args:
            asset_id: Asset identifier
            quantity: Quantity to trade (positive for buy, negative for sell)
            price: Execution price
            timestamp: Trade timestamp
            trade_type: 'BUY' or 'SELL'
            
        Returns:
            True if trade was executed successfully
        """
        try:
            if trade_type == 'BUY' and quantity > 0:
                # Check if we have enough cash
                total_cost = quantity * price
                if self.portfolio.cash_balance >= total_cost:
                    # Create new position or add to existing
                    existing_position = self.portfolio.get_position(asset_id)
                    if existing_position and existing_position.is_open:
                        # Add to existing position (average cost basis)
                        total_quantity = existing_position.quantity + quantity
                        avg_price = ((existing_position.quantity * existing_position.entry_price) + 
                                   (quantity * price)) / total_quantity
                        existing_position.quantity = total_quantity
                        existing_position.entry_price = avg_price
                    else:
                        # Create new position
                        new_position = Position(
                            id=len(self.portfolio.positions) + 1,
                            asset_id=asset_id,
                            quantity=quantity,
                            entry_price=price,
                            entry_date=timestamp
                        )
                        self.portfolio.add_position(new_position)
                    
                    # Update cash balance
                    self.portfolio.update_cash_balance(-total_cost)
                    
                    # Record trade
                    self._record_trade(asset_id, quantity, price, timestamp, trade_type)
                    return True
                    
            elif trade_type == 'SELL' and quantity > 0:
                # Check if we have the position to sell
                position = self.portfolio.get_position(asset_id)
                if position and position.is_open and position.quantity >= quantity:
                    if position.quantity == quantity:
                        # Close entire position
                        position.close_position(price, timestamp)
                    else:
                        # Partial close - reduce quantity
                        position.quantity -= quantity
                    
                    # Update cash balance
                    total_proceeds = quantity * price
                    self.portfolio.update_cash_balance(total_proceeds)
                    
                    # Record trade
                    self._record_trade(asset_id, -quantity, price, timestamp, trade_type)
                    return True
                    
            return False
            
        except Exception as e:
            print(f"Error executing trade: {e}")
            return False
    
    def _record_trade(self, asset_id: int, quantity: Decimal, price: Decimal, 
                     timestamp: datetime, trade_type: str) -> None:
        """Record a trade in the trade history."""
        trade = {
            'timestamp': timestamp,
            'asset_id': asset_id,
            'quantity': quantity,
            'price': price,
            'trade_type': trade_type,
            'portfolio_value': self.get_portfolio_value({asset_id: price})
        }
        self.trade_history.append(trade)
    
    def get_portfolio_value(self, current_prices: Dict[int, Decimal]) -> Decimal:
        """Get current portfolio value."""
        return self.portfolio.calculate_total_value(current_prices)
    
    def get_performance_metrics(self, final_prices: Dict[int, Decimal]) -> Dict[str, Any]:
        """Calculate performance metrics for the backtest."""
        final_value = self.get_portfolio_value(final_prices)
        total_return = final_value - self.initial_capital
        return_pct = (total_return / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'return_percentage': return_pct,
            'number_of_trades': len(self.trade_history),
            'portfolio_positions': len(self.portfolio.positions)
        }
    
    def run_backtest(self, market_data_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run the complete backtest.
        
        Args:
            market_data_series: List of market data points over time
            
        Returns:
            Dictionary containing backtest results and performance metrics
        """
        print(f"Starting backtest for {self.name}")
        
        for data_point in market_data_series:
            timestamp = data_point.get('timestamp')
            prices = data_point.get('prices', {})
            
            # Generate signals
            signals = self.generate_signals(data_point, timestamp)
            
            # Execute trades based on signals
            current_portfolio_value = self.get_portfolio_value(prices)
            
            for asset_id_str, signal in signals.items():
                asset_id = int(asset_id_str)
                current_price = prices.get(asset_id, Decimal('0'))
                
                if signal in ['BUY', 'SELL'] and current_price > 0:
                    quantity = self.calculate_position_size(
                        asset_id_str, signal, current_price, current_portfolio_value
                    )
                    
                    if quantity != 0:
                        self.execute_trade(asset_id, abs(quantity), current_price, 
                                         timestamp, signal)
        
        # Calculate final performance
        final_prices = market_data_series[-1].get('prices', {}) if market_data_series else {}
        performance = self.get_performance_metrics(final_prices)
        
        print(f"Backtest completed for {self.name}")
        print(f"Final Portfolio Value: {performance['final_value']}")
        print(f"Total Return: {performance['return_percentage']:.2f}%")
        
        return {
            'performance_metrics': performance,
            'trade_history': self.trade_history,
            'final_portfolio': self.portfolio
        }