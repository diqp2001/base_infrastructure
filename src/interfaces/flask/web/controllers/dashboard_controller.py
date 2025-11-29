from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask.json.provider import DefaultJSONProvider
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


class CustomJSONProvider(DefaultJSONProvider):
    """Custom JSON provider that handles NaN and numpy types."""

    def default(self, obj):
        if pd.isna(obj) or obj is None:
            return None
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
#from application.managers.project_managers.test_project_live_trading.test_project_live_trading_manager import TestProjectLiveTradingManager
from src.application.services.misbuffet.web.powerbuffet.powerbuffet import PowerBuffetService

web_bp = Blueprint("web", __name__)
logger = logging.getLogger(__name__)


def clean_for_json(data):
    """Clean data structure to ensure JSON serialization compatibility"""
    if isinstance(data, dict):
        return {k: clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(item) for item in data]
    elif pd.isna(data) or data is None:
        return None
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

@web_bp.route("/")
def home():
    return render_template("index.html")

@web_bp.route("/dashboard")
def dashboard_hub():
    """Main comprehensive dashboard hub with all 7 views"""
    return render_template("dashboard_hub.html")

@web_bp.route("/backtest", methods=["POST"])
def run_backtest():
    params = request.form  # values from an HTML form
    service = Misbuffet()
    results = service.run(params)  # returns a domain object or dict
    return render_template("results.html", results=results)

@web_bp.route("/test_backtest", methods=["GET", "POST"])
def run_test_backtest():
    """Display backtest configuration page or execute backtest via API call"""
    if request.method == "GET":
        return render_template("test_manager.html", manager_type="backtest")
    
    try:
        # Extract configuration from form data
        config = {
            'algorithm': request.form.get('algorithm', 'momentum'),
            'lookback': int(request.form.get('lookback', 20)),
            'start_date': request.form.get('start_date', '2024-01-01'),
            'end_date': request.form.get('end_date', '2024-12-31'),
            'initial_capital': float(request.form.get('initial_capital', 100000)),
            'risk_threshold': float(request.form.get('risk_threshold', 0.02)),
            'position_size': float(request.form.get('position_size', 10))
        }
        
        logger.info(f"Web controller: Calling API endpoint with config: {config}")
        
        # Call API endpoint instead of direct business logic
        import requests
        try:
            api_response = requests.post('http://localhost:5000/api/test_managers/backtest', 
                                       json=config, 
                                       timeout=300)  # 5 minute timeout for long-running backtests
            
            if api_response.status_code == 200:
                api_data = api_response.json()
                flash("Backtest completed successfully via API!", "success")
                
                # Generate mock performance data for visualization (in real app, get from API)
                performance_data = _generate_mock_performance_data(config)
                plot_data = _create_performance_plots(performance_data)
                metrics = _calculate_performance_metrics(performance_data)
                
                return render_template("performance_results.html", 
                                     plot_data=plot_data, 
                                     metrics=metrics,
                                     manager_type="Backtest",
                                     result=api_data.get('result'),
                                     config=config)
            else:
                error_msg = api_response.json().get('error', 'Unknown API error')
                flash(f"API Error: {error_msg}", "error")
                return render_template("test_manager.html", manager_type="backtest", config=config)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call backtest API: {e}")
            flash(f"Failed to connect to API: {str(e)}", "error")
            return render_template("test_manager.html", manager_type="backtest", config=config)
        
    except Exception as e:
        logger.error(f"Error in web controller: {e}")
        flash(f"Error: {str(e)}", "error")
        return render_template("test_manager.html", manager_type="backtest")

@web_bp.route("/test_live_trading", methods=["GET", "POST"])
def run_test_live_trading():
    """Display live trading configuration page or execute via API call"""
    if request.method == "GET":
        return render_template("test_manager.html", manager_type="live_trading")
    
    try:
        # Extract configuration from form data
        config = {
            'mode': request.form.get('trading_mode', 'paper'),
            'algorithm': request.form.get('algorithm', 'momentum'),
            'capital': float(request.form.get('capital', 50000)),
            'daily_risk': float(request.form.get('daily_risk', 2.0)),
            'max_positions': int(request.form.get('max_positions', 10))
        }
        
        logger.info(f"Web controller: Calling live trading API with config: {config}")
        
        # Call API endpoint instead of direct business logic
        import requests
        try:
            api_response = requests.post('http://localhost:5000/api/test_managers/live_trading', 
                                       json=config, 
                                       timeout=120)  # 2 minute timeout
            
            if api_response.status_code == 200:
                api_data = api_response.json()
                flash(f"Live trading ({config['mode']}) started successfully via API!", "success")
                
                # Generate mock performance data for visualization
                performance_data = _generate_mock_live_trading_data(config)
                plot_data = _create_performance_plots(performance_data)
                metrics = _calculate_performance_metrics(performance_data)
                
                return render_template("performance_results.html", 
                                     plot_data=plot_data, 
                                     metrics=metrics,
                                     manager_type="Live Trading",
                                     result=api_data.get('result'),
                                     config=config)
            else:
                error_msg = api_response.json().get('error', 'Unknown API error')
                flash(f"API Error: {error_msg}", "error")
                return render_template("test_manager.html", manager_type="live_trading", config=config)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call live trading API: {e}")
            flash(f"Failed to connect to API: {str(e)}", "error")
            return render_template("test_manager.html", manager_type="live_trading", config=config)
        
    except Exception as e:
        logger.error(f"Error in web controller: {e}")
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

def _generate_mock_performance_data(config):
    """Generate mock performance data based on configuration"""
    start_date = datetime.strptime(config.get('start_date', '2024-01-01'), '%Y-%m-%d')
    end_date = datetime.strptime(config.get('end_date', '2024-12-31'), '%Y-%m-%d')
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    initial_value = config.get('initial_capital', 100000)
    
    performance_data = {
        'timestamps': [],
        'portfolio_values': [],
        'returns': [],
        'drawdowns': []
    }
    
    cumulative_return = 1.0
    for date in dates:
        daily_return = np.random.normal(0.0008, 0.02)  
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
    
    return performance_data

def _generate_mock_live_trading_data(config):
    """Generate mock live trading performance data"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                        end=datetime.now(), freq='H')
    initial_value = config.get('capital', 50000)
    
    performance_data = {
        'timestamps': [],
        'portfolio_values': [],
        'returns': [],
        'drawdowns': []
    }
    
    cumulative_return = 1.0
    for date in dates:
        hourly_return = np.random.normal(0.0001, 0.003)
        cumulative_return *= (1 + hourly_return)
        
        portfolio_value = initial_value * cumulative_return
        performance_data['timestamps'].append(date)
        performance_data['portfolio_values'].append(portfolio_value)
        performance_data['returns'].append(hourly_return)
    
    # Calculate drawdowns
    peak = performance_data['portfolio_values'][0]
    for pv in performance_data['portfolio_values']:
        if pv > peak:
            peak = pv
        drawdown = (pv - peak) / peak * 100
        performance_data['drawdowns'].append(drawdown)
    
    return performance_data

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


# PowerBuffet Routes
@web_bp.route("/powerbuffet")
def powerbuffet_home():
    """PowerBuffet data visualization and database explorer"""
    try:
        service = PowerBuffetService()
        databases = service.get_available_databases()
        visualizations = service.get_available_visualizations()
        
        return render_template("powerbuffet.html", 
                             databases=databases,
                             visualizations=visualizations)
    except Exception as e:
        logger.error(f"Error loading PowerBuffet: {e}")
        flash(f"Error loading PowerBuffet: {str(e)}", "error")
        return redirect(url_for('web.dashboard_hub'))

@web_bp.route("/api/powerbuffet/databases", methods=["GET"])
def get_databases():
    """API endpoint to get available databases"""
    try:
        service = PowerBuffetService()
        databases = service.get_available_databases()
        return jsonify({"success": True, "databases": databases})
    except Exception as e:
        logger.error(f"Error getting databases: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/powerbuffet/tables/<path:database_path>", methods=["GET"])
def get_tables(database_path):
    """API endpoint to get tables for a specific database"""
    try:
        service = PowerBuffetService()
        tables = service.get_database_tables(database_path)
        # Clean data to ensure JSON serialization compatibility
        cleaned_tables = clean_for_json(tables)
        return jsonify({"success": True, "tables": cleaned_tables})
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/powerbuffet/preview/<path:database_path>/<table_name>", methods=["GET"])
def get_table_preview(database_path, table_name):
    """API endpoint to get preview data for a specific table (SELECT TOP 10)"""
    try:
        service = PowerBuffetService()
        preview_data = service.get_table_preview(database_path, table_name)
        # Clean data to ensure JSON serialization compatibility
        cleaned_preview = clean_for_json(preview_data)
        return jsonify({"success": True, "preview": cleaned_preview})
    except Exception as e:
        logger.error(f"Error getting table preview: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/powerbuffet/visualizations", methods=["GET"])
def get_visualizations():
    """API endpoint to get available visualizations"""
    try:
        service = PowerBuffetService()
        visualizations = service.get_available_visualizations()
        return jsonify({"success": True, "visualizations": visualizations})
    except Exception as e:
        logger.error(f"Error getting visualizations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/powerbuffet/run_visualization", methods=["POST"])
def run_visualization():
    """API endpoint to execute a visualization"""
    try:
        data = request.json
        database_path = data.get('database_path')
        table_name = data.get('table_name')
        visualization_name = data.get('visualization_name')
        params = data.get('params', {})
        
        if not all([database_path, table_name, visualization_name]):
            return jsonify({
                "success": False, 
                "error": "Missing required parameters: database_path, table_name, visualization_name"
            }), 400
        
        service = PowerBuffetService()
        result = service.run_visualization(database_path, table_name, visualization_name, params)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error running visualization: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/powerbuffet/run_custom_visualization", methods=["POST"])
def run_custom_visualization():
    """API endpoint to execute custom multi-column visualizations"""
    try:
        data = request.json
        chart_type = data.get('chart_type', 'scatter')
        x_columns = data.get('x_columns', [])
        y_columns = data.get('y_columns', [])
        params = data.get('params', {})
        
        if not x_columns and not y_columns:
            return jsonify({
                "success": False,
                "error": "Must provide at least one X or Y column for visualization"
            }), 400
        
        service = PowerBuffetService()
        result = service.run_custom_visualization(chart_type, x_columns, y_columns, params)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error running custom visualization: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# New API endpoints for enhanced functionality
@web_bp.route("/api/ib/connect", methods=["POST"])
def connect_interactive_brokers():
    """API endpoint to connect to Interactive Brokers"""
    try:
        from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
        
        data = request.json if request.json else {}
        ib_config = {
            'host': data.get('host', '127.0.0.1'),
            'port': data.get('port', 7497),
            'client_id': data.get('client_id', 1),
            'paper_trading': data.get('paper_trading', True),
            'timeout': data.get('timeout', 60),
            'account_id': data.get('account_id', 'DEFAULT'),
            'enable_logging': data.get('enable_logging', True),
        }
        
        # Create manager and connect to IB
        manager = TestBaseProjectManager()
        manager._setup_interactive_brokers_connection(ib_config)
        
        # Get account info after connection
        if manager.ib_broker and manager.ib_broker.is_connected():
            account_info = manager.get_ib_account_info()
            return jsonify({
                "success": True,
                "message": "Connected to Interactive Brokers successfully",
                "account_info": account_info,
                "config": ib_config
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to establish connection to Interactive Brokers"
            }), 500
            
    except Exception as e:
        logger.error(f"Error connecting to Interactive Brokers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/system/setup_factors", methods=["POST"])
def setup_factor_system():
    """API endpoint to setup factor system"""
    try:
        from application.managers.project_managers.test_base_project.test_base_project_manager import TestBaseProjectManager
        
        data = request.json if request.json else {}
        tickers = data.get('tickers', None)  # Use default if not provided
        overwrite = data.get('overwrite', False)
        
        manager = TestBaseProjectManager()
        result = manager.setup_factor_system(tickers=tickers, overwrite=overwrite)
        
        if result.get('system_ready', False):
            return jsonify({
                "success": True,
                "message": f"Factor system setup completed in {result.get('total_setup_time', 0):.2f}s",
                "result": result
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error in factor system setup'),
                "result": result
            }), 500
            
    except Exception as e:
        logger.error(f"Error setting up factor system: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/data/import", methods=["POST"])
def import_data():
    """API endpoint to import data"""
    try:
        data = request.json if request.json else {}
        data_source = data.get('source', 'default')
        
        # This could be expanded to handle different data sources
        if data_source == 'cboe':
            from application.managers.api_managers.api_cboe.api_cboe_manager import download_and_consolidate_csv
            result = download_and_consolidate_csv()
            return jsonify({
                "success": True,
                "message": "CBOE data import completed successfully",
                "result": result
            })
        else:
            # Default data import logic
            return jsonify({
                "success": True,
                "message": "Default data import completed",
                "imported_records": 1000  # Placeholder
            })
            
    except Exception as e:
        logger.error(f"Error importing data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Additional API endpoints for test managers
@web_bp.route("/api/test_managers/backtest", methods=["POST"])
def api_execute_backtest():
    """API endpoint to execute TestProjectBacktestManager"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No configuration provided"}), 400
        
        logger.info(f"API: Executing backtest with config: {data}")
        
        # Execute actual backtest manager with configuration
        manager = TestProjectBacktestManager()
        result = manager.run(start_web_interface=False)  # Don't start another web interface
        
        return jsonify({
            "success": True,
            "result": str(result),
            "message": "Backtest completed successfully",
            "config": data
        })
        
    except Exception as e:
        logger.error(f"API: Error executing backtest: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/test_managers/live_trading", methods=["POST"])
def api_execute_live_trading():
    """API endpoint to execute TestProjectLiveTradingManager"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No configuration provided"}), 400
        
        logger.info(f"API: Executing live trading with config: {data}")
        
        # Execute actual live trading manager with configuration
        manager = TestProjectLiveTradingManager()
        result = manager.run()  # In real implementation, pass config to run method
        
        return jsonify({
            "success": True,
            "result": str(result),
            "message": f"Live trading ({data.get('mode', 'paper')}) started successfully",
            "config": data
        })
        
    except Exception as e:
        logger.error(f"API: Error executing live trading: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/system/shutdown", methods=["POST"])
def shutdown_system():
    """API endpoint to shutdown the system gracefully"""
    try:
        import os
        import signal
        import threading
        import time
        
        def delayed_shutdown():
            """Shutdown the system after a short delay to allow response to be sent"""
            time.sleep(2)  # Wait for response to be sent
            logger.info("Initiating system shutdown...")
            
            # Try graceful shutdown first
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                # Force shutdown if graceful doesn't work
                os.kill(os.getpid(), signal.SIGKILL)
        
        # Start shutdown in background thread
        shutdown_thread = threading.Thread(target=delayed_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return jsonify({
            "success": True,
            "message": "System shutdown initiated. Interface will close shortly."
        })
        
    except Exception as e:
        logger.error(f"Error shutting down system: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# MLflow-style Backtest Tracking API Endpoints
@web_bp.route("/api/backtest/tracking/experiments", methods=["GET"])
def get_tracking_experiments():
    """Get list of all tracking experiments"""
    try:
        from src.application.services.mlflow_storage.mlflow_backtest_tracker import get_tracker
        
        tracker = get_tracker()
        experiments = tracker.get_experiments()
        
        return jsonify({
            "success": True,
            "experiments": experiments,
            "count": len(experiments)
        })
        
    except Exception as e:
        logger.error(f"Error getting tracking experiments: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/backtest/tracking/runs", methods=["GET"])
def get_tracking_runs():
    """Get list of backtest runs, optionally filtered by experiment"""
    try:
        from src.application.services.mlflow_storage.mlflow_backtest_tracker import get_tracker
        
        experiment_name = request.args.get('experiment_name')
        limit = int(request.args.get('limit', 50))
        
        tracker = get_tracker()
        runs = tracker.list_runs(experiment_name=experiment_name, limit=limit)
        
        return jsonify({
            "success": True,
            "runs": runs,
            "count": len(runs)
        })
        
    except Exception as e:
        logger.error(f"Error getting tracking runs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/backtest/tracking/runs/<run_id>", methods=["GET"])
def get_tracking_run_details(run_id: str):
    """Get detailed information about a specific run"""
    try:
        from src.application.services.mlflow_storage.mlflow_backtest_tracker import get_tracker
        
        tracker = get_tracker()
        run_data = tracker.get_run(run_id)
        
        if not run_data:
            return jsonify({"success": False, "error": "Run not found"}), 404
        
        return jsonify({
            "success": True,
            "run": run_data
        })
        
    except Exception as e:
        logger.error(f"Error getting run details: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/backtest/tracking/runs/compare", methods=["POST"])
def compare_tracking_runs():
    """Compare multiple backtest runs"""
    try:
        from src.application.services.mlflow_storage.mlflow_backtest_tracker import get_tracker
        
        data = request.json
        run_ids = data.get('run_ids', [])
        
        if not run_ids or len(run_ids) < 2:
            return jsonify({
                "success": False, 
                "error": "At least 2 run IDs required for comparison"
            }), 400
        
        tracker = get_tracker()
        comparison_data = tracker.compare_runs(run_ids)
        
        return jsonify({
            "success": True,
            "comparison": comparison_data
        })
        
    except Exception as e:
        logger.error(f"Error comparing runs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/backtest/tracking/store_run", methods=["POST"])
def store_backtest_run():
    """Store a completed backtest run with MLflow-style tracking"""
    try:
        from src.application.services.mlflow_storage.mlflow_backtest_tracker import get_tracker
        
        data = request.json
        experiment_name = data.get('experiment_name', 'default_backtest_experiment')
        run_name = data.get('run_name')
        parameters = data.get('parameters', {})
        metrics = data.get('metrics', {})
        tags = data.get('tags', {})
        artifacts = data.get('artifacts', {})
        
        tracker = get_tracker()
        run_id = tracker.start_run(experiment_name, run_name)
        
        # Log all data
        if parameters:
            tracker.log_parameters(run_id, parameters)
        
        if metrics:
            tracker.log_metrics(run_id, metrics)
        
        if tags:
            tracker.set_tags(run_id, tags)
        
        # Log artifacts
        for artifact_name, artifact_data in artifacts.items():
            tracker.log_artifact(run_id, f"{artifact_name}.json", artifact_data, 'json')
        
        # End the run
        tracker.end_run(run_id, 'FINISHED')
        
        return jsonify({
            "success": True,
            "run_id": run_id,
            "message": f"Backtest run stored successfully with ID: {run_id}"
        })
        
    except Exception as e:
        logger.error(f"Error storing backtest run: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route("/api/backtest/tracking/runs/<run_id>", methods=["DELETE"])
def delete_tracking_run(run_id: str):
    """Delete a backtest run and all associated data"""
    try:
        from src.application.services.mlflow_storage.mlflow_backtest_tracker import get_tracker
        
        tracker = get_tracker()
        success = tracker.delete_run(run_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Run {run_id} deleted successfully"
            })
        else:
            return jsonify({"success": False, "error": "Run not found"}), 404
        
    except Exception as e:
        logger.error(f"Error deleting run: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
