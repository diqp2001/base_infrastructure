"""
Performance Metrics Calculator for Market Making

Calculates market making specific performance metrics including:
- Spread capture
- Fill ratios
- Inventory turnover
- Risk-adjusted returns
- PnL attribution
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import math


class MarketMakingMetrics:
    """
    Comprehensive performance metrics calculator for market making strategies.
    """
    
    def __init__(self):
        """Initialize the performance metrics calculator."""
        self.logger = logging.getLogger(__name__)
        
        # Metrics tracking
        self.trades_history = []
        self.quotes_history = []
        self.inventory_history = []
        self.pnl_history = []
        
        self.logger.info("MarketMakingMetrics initialized")
    
    def record_trade(self, symbol: str, side: str, quantity: Decimal, 
                    price: Decimal, timestamp: datetime = None):
        """
        Record a trade execution.
        
        Args:
            symbol: Instrument symbol
            side: 'BUY' or 'SELL'
            quantity: Trade quantity
            price: Execution price
            timestamp: Trade timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        trade_record = {
            'symbol': symbol,
            'side': side,
            'quantity': float(quantity),
            'price': float(price),
            'timestamp': timestamp,
            'value': float(quantity * price)
        }
        
        self.trades_history.append(trade_record)
        self.logger.debug(f"Recorded trade: {symbol} {side} {quantity} @ {price}")
    
    def record_quote(self, symbol: str, bid_price: Decimal, ask_price: Decimal,
                    bid_size: int, ask_size: int, timestamp: datetime = None):
        """
        Record a quote update.
        
        Args:
            symbol: Instrument symbol
            bid_price: Bid price
            ask_price: Ask price
            bid_size: Bid size
            ask_size: Ask size
            timestamp: Quote timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        quote_record = {
            'symbol': symbol,
            'bid_price': float(bid_price),
            'ask_price': float(ask_price),
            'bid_size': bid_size,
            'ask_size': ask_size,
            'spread': float(ask_price - bid_price),
            'spread_bps': float((ask_price - bid_price) / ((bid_price + ask_price) / 2) * 10000),
            'mid_price': float((bid_price + ask_price) / 2),
            'timestamp': timestamp
        }
        
        self.quotes_history.append(quote_record)
    
    def record_inventory(self, inventory_snapshot: Dict[str, Decimal], 
                        timestamp: datetime = None):
        """
        Record an inventory snapshot.
        
        Args:
            inventory_snapshot: Current inventory positions
            timestamp: Snapshot timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        inventory_record = {
            'positions': {k: float(v) for k, v in inventory_snapshot.items()},
            'total_absolute_inventory': sum(abs(v) for v in inventory_snapshot.values()),
            'timestamp': timestamp
        }
        
        self.inventory_history.append(inventory_record)
    
    def record_pnl(self, symbol: str, realized_pnl: Decimal, unrealized_pnl: Decimal,
                  timestamp: datetime = None):
        """
        Record PnL information.
        
        Args:
            symbol: Instrument symbol
            realized_pnl: Realized PnL
            unrealized_pnl: Unrealized PnL
            timestamp: PnL timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        pnl_record = {
            'symbol': symbol,
            'realized_pnl': float(realized_pnl),
            'unrealized_pnl': float(unrealized_pnl),
            'total_pnl': float(realized_pnl + unrealized_pnl),
            'timestamp': timestamp
        }
        
        self.pnl_history.append(pnl_record)
    
    def calculate_spread_capture_metrics(self, symbol: str = None) -> Dict[str, Any]:
        """
        Calculate spread capture metrics.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Spread capture metrics
        """
        try:
            quotes_df = self._get_quotes_dataframe(symbol)
            trades_df = self._get_trades_dataframe(symbol)
            
            if quotes_df.empty or trades_df.empty:
                return {'error': 'Insufficient data for spread capture calculation'}
            
            # Calculate average spreads
            avg_quoted_spread = quotes_df['spread'].mean()
            avg_quoted_spread_bps = quotes_df['spread_bps'].mean()
            
            # Calculate effective spreads (need to match trades to quotes)
            effective_spreads = self._calculate_effective_spreads(trades_df, quotes_df)
            avg_effective_spread = np.mean(effective_spreads) if effective_spreads else 0
            
            # Spread capture ratio
            spread_capture_ratio = (avg_effective_spread / avg_quoted_spread) if avg_quoted_spread > 0 else 0
            
            return {
                'avg_quoted_spread': avg_quoted_spread,
                'avg_quoted_spread_bps': avg_quoted_spread_bps,
                'avg_effective_spread': avg_effective_spread,
                'spread_capture_ratio': spread_capture_ratio,
                'total_quotes': len(quotes_df),
                'total_trades': len(trades_df),
                'symbol_filter': symbol
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating spread capture metrics: {str(e)}")
            return {'error': str(e)}
    
    def calculate_fill_ratio_metrics(self, symbol: str = None) -> Dict[str, Any]:
        """
        Calculate fill ratio metrics.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Fill ratio metrics
        """
        try:
            quotes_df = self._get_quotes_dataframe(symbol)
            trades_df = self._get_trades_dataframe(symbol)
            
            if quotes_df.empty:
                return {'error': 'No quotes data available'}
            
            # Calculate time-weighted quote exposure
            total_quote_time = self._calculate_total_quote_time(quotes_df)
            
            # Calculate fill metrics
            total_fills = len(trades_df)
            total_fill_quantity = trades_df['quantity'].sum() if not trades_df.empty else 0
            
            # Estimate fill ratio (simplified - real calculation would be more complex)
            avg_quote_size = (quotes_df['bid_size'] + quotes_df['ask_size']).mean() / 2
            theoretical_max_fills = total_quote_time.total_seconds() / 3600 * avg_quote_size  # Hourly turnover
            
            fill_ratio = min(1.0, total_fills / theoretical_max_fills) if theoretical_max_fills > 0 else 0
            
            return {
                'total_fills': total_fills,
                'total_fill_quantity': total_fill_quantity,
                'avg_fill_size': total_fill_quantity / total_fills if total_fills > 0 else 0,
                'fill_ratio_estimate': fill_ratio,
                'total_quote_time_hours': total_quote_time.total_seconds() / 3600,
                'avg_quote_size': avg_quote_size,
                'symbol_filter': symbol
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating fill ratio metrics: {str(e)}")
            return {'error': str(e)}
    
    def calculate_inventory_turnover_metrics(self, symbol: str = None) -> Dict[str, Any]:
        """
        Calculate inventory turnover metrics.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Inventory turnover metrics
        """
        try:
            trades_df = self._get_trades_dataframe(symbol)
            inventory_df = self._get_inventory_dataframe()
            
            if trades_df.empty or inventory_df.empty:
                return {'error': 'Insufficient data for inventory turnover calculation'}
            
            # Calculate trading volume
            total_volume = trades_df['quantity'].abs().sum()
            
            # Calculate average inventory
            if symbol:
                avg_inventory = np.mean([
                    abs(inv['positions'].get(symbol, 0)) 
                    for inv in self.inventory_history
                    if symbol in inv['positions']
                ])
            else:
                avg_inventory = np.mean([
                    inv['total_absolute_inventory'] 
                    for inv in self.inventory_history
                ])
            
            # Calculate turnover
            time_period = (trades_df['timestamp'].max() - trades_df['timestamp'].min()).days
            if time_period > 0 and avg_inventory > 0:
                daily_turnover = total_volume / time_period
                inventory_turnover_ratio = daily_turnover / avg_inventory
            else:
                daily_turnover = 0
                inventory_turnover_ratio = 0
            
            return {
                'total_volume': total_volume,
                'avg_inventory': avg_inventory,
                'daily_turnover': daily_turnover,
                'inventory_turnover_ratio': inventory_turnover_ratio,
                'time_period_days': time_period,
                'symbol_filter': symbol
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating inventory turnover metrics: {str(e)}")
            return {'error': str(e)}
    
    def calculate_pnl_attribution(self, symbol: str = None) -> Dict[str, Any]:
        """
        Calculate PnL attribution metrics.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            PnL attribution metrics
        """
        try:
            pnl_df = self._get_pnl_dataframe(symbol)
            trades_df = self._get_trades_dataframe(symbol)
            
            if pnl_df.empty:
                return {'error': 'No PnL data available'}
            
            # Total PnL components
            total_realized_pnl = pnl_df['realized_pnl'].sum()
            total_unrealized_pnl = pnl_df['unrealized_pnl'].sum()
            total_pnl = total_realized_pnl + total_unrealized_pnl
            
            # Trading-based attribution (simplified)
            buy_volume = trades_df[trades_df['side'] == 'BUY']['value'].sum() if not trades_df.empty else 0
            sell_volume = trades_df[trades_df['side'] == 'SELL']['value'].sum() if not trades_df.empty else 0
            
            # PnL per unit metrics
            total_volume = buy_volume + sell_volume
            pnl_per_dollar_volume = total_pnl / total_volume if total_volume > 0 else 0
            
            return {
                'total_realized_pnl': total_realized_pnl,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_pnl': total_pnl,
                'buy_volume': buy_volume,
                'sell_volume': sell_volume,
                'total_volume': total_volume,
                'pnl_per_dollar_volume': pnl_per_dollar_volume,
                'realized_pnl_ratio': total_realized_pnl / total_pnl if total_pnl != 0 else 0,
                'symbol_filter': symbol
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating PnL attribution: {str(e)}")
            return {'error': str(e)}
    
    def calculate_risk_adjusted_returns(self, symbol: str = None) -> Dict[str, Any]:
        """
        Calculate risk-adjusted return metrics.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Risk-adjusted return metrics
        """
        try:
            pnl_df = self._get_pnl_dataframe(symbol)
            
            if len(pnl_df) < 2:
                return {'error': 'Insufficient PnL data for risk calculations'}
            
            # Calculate daily returns
            pnl_df = pnl_df.sort_values('timestamp')
            pnl_df['daily_pnl'] = pnl_df['total_pnl'].diff()
            daily_returns = pnl_df['daily_pnl'].dropna()
            
            if len(daily_returns) < 2:
                return {'error': 'Insufficient daily returns for risk calculations'}
            
            # Calculate metrics
            avg_daily_return = daily_returns.mean()
            daily_volatility = daily_returns.std()
            
            # Annualized metrics (assuming 252 trading days)
            annualized_return = avg_daily_return * 252
            annualized_volatility = daily_volatility * math.sqrt(252)
            
            # Sharpe ratio (assuming 5% risk-free rate)
            risk_free_rate = 0.05
            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else 0
            
            # Maximum drawdown
            cumulative_pnl = daily_returns.cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdowns = cumulative_pnl - running_max
            max_drawdown = drawdowns.min()
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            return {
                'avg_daily_return': avg_daily_return,
                'daily_volatility': daily_volatility,
                'annualized_return': annualized_return,
                'annualized_volatility': annualized_volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar_ratio,
                'total_trading_days': len(daily_returns),
                'symbol_filter': symbol
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk-adjusted returns: {str(e)}")
            return {'error': str(e)}
    
    def get_comprehensive_performance_report(self, symbol: str = None) -> Dict[str, Any]:
        """
        Generate a comprehensive performance report.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Comprehensive performance metrics
        """
        return {
            'spread_capture': self.calculate_spread_capture_metrics(symbol),
            'fill_ratios': self.calculate_fill_ratio_metrics(symbol),
            'inventory_turnover': self.calculate_inventory_turnover_metrics(symbol),
            'pnl_attribution': self.calculate_pnl_attribution(symbol),
            'risk_adjusted_returns': self.calculate_risk_adjusted_returns(symbol),
            'data_summary': {
                'trades_count': len(self.trades_history),
                'quotes_count': len(self.quotes_history),
                'inventory_snapshots': len(self.inventory_history),
                'pnl_records': len(self.pnl_history)
            },
            'report_timestamp': datetime.now().isoformat(),
            'symbol_filter': symbol
        }
    
    # Helper methods
    
    def _get_quotes_dataframe(self, symbol: str = None) -> pd.DataFrame:
        """Get quotes data as DataFrame."""
        quotes_data = self.quotes_history
        if symbol:
            quotes_data = [q for q in quotes_data if q['symbol'] == symbol]
        
        return pd.DataFrame(quotes_data)
    
    def _get_trades_dataframe(self, symbol: str = None) -> pd.DataFrame:
        """Get trades data as DataFrame."""
        trades_data = self.trades_history
        if symbol:
            trades_data = [t for t in trades_data if t['symbol'] == symbol]
        
        return pd.DataFrame(trades_data)
    
    def _get_inventory_dataframe(self) -> pd.DataFrame:
        """Get inventory data as DataFrame."""
        return pd.DataFrame(self.inventory_history)
    
    def _get_pnl_dataframe(self, symbol: str = None) -> pd.DataFrame:
        """Get PnL data as DataFrame."""
        pnl_data = self.pnl_history
        if symbol:
            pnl_data = [p for p in pnl_data if p['symbol'] == symbol]
        
        return pd.DataFrame(pnl_data)
    
    def _calculate_effective_spreads(self, trades_df: pd.DataFrame, 
                                   quotes_df: pd.DataFrame) -> List[float]:
        """Calculate effective spreads for trades."""
        effective_spreads = []
        
        for _, trade in trades_df.iterrows():
            # Find the closest quote before the trade
            prior_quotes = quotes_df[
                (quotes_df['timestamp'] <= trade['timestamp']) &
                (quotes_df['symbol'] == trade['symbol'])
            ]
            
            if not prior_quotes.empty:
                latest_quote = prior_quotes.iloc[-1]
                mid_price = latest_quote['mid_price']
                
                # Calculate effective spread
                if trade['side'] == 'BUY':
                    effective_spread = 2 * (trade['price'] - mid_price)
                else:  # SELL
                    effective_spread = 2 * (mid_price - trade['price'])
                
                effective_spreads.append(effective_spread)
        
        return effective_spreads
    
    def _calculate_total_quote_time(self, quotes_df: pd.DataFrame) -> timedelta:
        """Calculate total time quotes were active."""
        if quotes_df.empty:
            return timedelta(0)
        
        return quotes_df['timestamp'].max() - quotes_df['timestamp'].min()
    
    def clear_history(self):
        """Clear all historical data."""
        self.trades_history.clear()
        self.quotes_history.clear()
        self.inventory_history.clear()
        self.pnl_history.clear()
        
        self.logger.info("All performance history cleared")
    
    def export_data(self, format_type: str = 'dict') -> Dict[str, Any]:
        """
        Export all recorded data.
        
        Args:
            format_type: Export format ('dict', 'json')
            
        Returns:
            Exported data
        """
        data = {
            'trades': self.trades_history,
            'quotes': self.quotes_history,
            'inventory': self.inventory_history,
            'pnl': self.pnl_history,
            'export_timestamp': datetime.now().isoformat()
        }
        
        if format_type == 'json':
            import json
            return json.dumps(data, default=str, indent=2)
        
        return data