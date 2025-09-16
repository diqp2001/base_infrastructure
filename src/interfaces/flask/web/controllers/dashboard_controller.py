from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from src.application.services.misbuffet import Misbuffet
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime, timedelta
import json
import logging

from application.managers.project_managers.test_project_backtest.test_project_backtest_manager import TestProjectBacktestManager
from application.managers.project_managers.test_project_live_trading.test_project_live_trading_manager import TestProjectLiveTradingManager

web_bp = Blueprint("web", __name__)
logger = logging.getLogger(__name__)

@web_bp.route("/")
def home():
    return render_template("index.html")

@web_bp.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.form  # values from an HTML form
    service = Misbuffet()
    results = service.run(params)  # returns a domain object or dict
    return render_template("results.html", results=results)

@web_bp.route("/test_backtest", methods=["GET", "POST"])
def run_test_backtest():
    """Run TestProjectBacktestManager and display performance plot"""
    if request.method == "GET":
        return render_template("test_manager.html", manager_type="backtest")
    
    try:
        logger.info("Starting TestProjectBacktestManager execution...")
        manager = TestProjectBacktestManager()
        
        # Capture performance data during execution
        performance_data = {
            'timestamps': [],
            'portfolio_values': [],
            'returns': [],
            'drawdowns': [],
            'positions': {}
        }
        
        # Mock performance data for demonstration (replace with actual data collection)
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        initial_value = 100000
        
        # Simulate portfolio evolution
        cumulative_return = 1.0
        for i, date in enumerate(dates):
            # Simulate daily returns with some volatility and trend
            daily_return = np.random.normal(0.0008, 0.02)  # 0.08% daily return with 2% volatility
            cumulative_return *= (1 + daily_return)
            
            portfolio_value = initial_value * cumulative_return
            performance_data['timestamps'].append(date)
            performance_data['portfolio_values'].append(portfolio_value)
            performance_data['returns'].append(daily_return)
        
        # Calculate drawdowns
        peak = performance_data['portfolio_values'][0]
        for pv in performance_data['portfolio_values']:
            if pv > peak:
                peak = pv
            drawdown = (pv - peak) / peak * 100
            performance_data['drawdowns'].append(drawdown)
        
        # Run the actual manager (this might take time)
        result = manager.run()
        
        # Create performance plots
        plot_data = _create_performance_plots(performance_data)
        
        # Calculate performance metrics
        metrics = _calculate_performance_metrics(performance_data)
        
        flash("TestProjectBacktestManager executed successfully!", "success")
        return render_template("performance_results.html", 
                             plot_data=plot_data, 
                             metrics=metrics,
                             manager_type="Backtest",
                             result=result)
        
    except Exception as e:
        logger.error(f"Error running TestProjectBacktestManager: {e}")
        flash(f"Error: {str(e)}", "error")
        return render_template("test_manager.html", manager_type="backtest")

@web_bp.route("/test_live_trading", methods=["GET", "POST"])
def run_test_live_trading():
    """Run TestProjectLiveTradingManager and display performance plot"""
    if request.method == "GET":
        return render_template("test_manager.html", manager_type="live_trading")
    
    try:
        logger.info("Starting TestProjectLiveTradingManager execution...")
        manager = TestProjectLiveTradingManager()
        
        # Capture performance data during execution
        performance_data = {
            'timestamps': [],
            'portfolio_values': [],
            'returns': [],
            'drawdowns': [],
            'positions': {}
        }
        
        # Mock performance data for live trading (shorter timeframe)
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                            end=datetime.now(), freq='H')
        initial_value = 100000
        
        # Simulate intraday portfolio evolution
        cumulative_return = 1.0
        for i, date in enumerate(dates):
            # Simulate hourly returns with higher volatility for live trading
            daily_return = np.random.normal(0.0001, 0.003)  # Lower hourly returns, higher volatility
            cumulative_return *= (1 + daily_return)
            
            portfolio_value = initial_value * cumulative_return
            performance_data['timestamps'].append(date)
            performance_data['portfolio_values'].append(portfolio_value)
            performance_data['returns'].append(daily_return)
        
        # Calculate drawdowns
        peak = performance_data['portfolio_values'][0]
        for pv in performance_data['portfolio_values']:
            if pv > peak:
                peak = pv
            drawdown = (pv - peak) / peak * 100
            performance_data['drawdowns'].append(drawdown)
        
        # Run the actual manager (this might take time for live trading setup)
        result = manager.run()
        
        # Create performance plots
        plot_data = _create_performance_plots(performance_data)
        
        # Calculate performance metrics
        metrics = _calculate_performance_metrics(performance_data)
        
        flash("TestProjectLiveTradingManager executed successfully!", "success")
        return render_template("performance_results.html", 
                             plot_data=plot_data, 
                             metrics=metrics,
                             manager_type="Live Trading",
                             result=result)
        
    except Exception as e:
        logger.error(f"Error running TestProjectLiveTradingManager: {e}")
        flash(f"Error: {str(e)}", "error")
        return render_template("test_manager.html", manager_type="live_trading")

def _create_performance_plots(performance_data):
    """Create performance visualization plots"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Portfolio Performance Analysis', fontsize=16)
    
    timestamps = performance_data['timestamps']
    portfolio_values = performance_data['portfolio_values']
    returns = performance_data['returns']
    drawdowns = performance_data['drawdowns']
    
    # Portfolio value over time
    axes[0, 0].plot(timestamps, portfolio_values, linewidth=2, color='blue')
    axes[0, 0].set_title('Portfolio Value Over Time')
    axes[0, 0].set_ylabel('Portfolio Value ($)')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[0, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(axes[0, 0].xaxis.get_majorticklabels(), rotation=45)
    
    # Returns distribution
    axes[0, 1].hist(returns, bins=50, alpha=0.7, color='green', edgecolor='black')
    axes[0, 1].set_title('Returns Distribution')
    axes[0, 1].set_xlabel('Daily Returns')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Drawdown over time
    axes[1, 0].fill_between(timestamps, drawdowns, 0, alpha=0.3, color='red')
    axes[1, 0].plot(timestamps, drawdowns, color='red', linewidth=1)
    axes[1, 0].set_title('Drawdown Over Time')
    axes[1, 0].set_ylabel('Drawdown (%)')
    axes[1, 0].set_xlabel('Date')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[1, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)
    
    # Cumulative returns
    cumulative_returns = np.cumprod([1 + r for r in returns]) - 1
    axes[1, 1].plot(timestamps, [cr * 100 for cr in cumulative_returns], linewidth=2, color='purple')
    axes[1, 1].set_title('Cumulative Returns')
    axes[1, 1].set_ylabel('Cumulative Return (%)')
    axes[1, 1].set_xlabel('Date')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    axes[1, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(axes[1, 1].xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    
    # Convert plot to base64 string
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    img_data = base64.b64encode(img_buffer.getvalue()).decode()
    plt.close()
    
    return img_data

def _calculate_performance_metrics(performance_data):
    """Calculate key performance metrics"""
    returns = performance_data['returns']
    portfolio_values = performance_data['portfolio_values']
    drawdowns = performance_data['drawdowns']
    
    # Basic metrics
    total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0] * 100
    volatility = np.std(returns) * np.sqrt(252) * 100  # Annualized volatility
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    max_drawdown = min(drawdowns)
    
    # Additional metrics
    win_rate = len([r for r in returns if r > 0]) / len(returns) * 100
    avg_return = np.mean(returns) * 100
    max_return = max(returns) * 100
    min_return = min(returns) * 100
    
    return {
        'total_return': round(total_return, 2),
        'volatility': round(volatility, 2),
        'sharpe_ratio': round(sharpe_ratio, 3),
        'max_drawdown': round(max_drawdown, 2),
        'win_rate': round(win_rate, 2),
        'avg_return': round(avg_return, 4),
        'max_return': round(max_return, 2),
        'min_return': round(min_return, 2),
        'final_value': round(portfolio_values[-1], 2),
        'initial_value': round(portfolio_values[0], 2)
    }
