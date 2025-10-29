"""
WebInterfaceManager for test_base_project.

Extends the existing Misbuffet web interface with project-specific monitoring
capabilities for ML models, factor data, and trading performance.
"""

import queue
import threading
from typing import Dict, Any, Optional

# Import existing web interface framework
try:
    from application.services.misbuffet.web.web_interface import WebInterfaceManager as BaseWebInterfaceManager
except ImportError:
    # Fallback if web interface not available
    BaseWebInterfaceManager = object


class WebInterfaceManager:
    """
    Manages web interface for BaseProject backtesting and monitoring.
    
    Integrates with existing Misbuffet web framework while adding
    project-specific features for factor data and ML model monitoring.
    """
    
    def __init__(self):
        """Initialize the web interface manager."""
        self.progress_queue = queue.Queue()
        self.is_running = False
        self.web_thread = None
        
        # Try to initialize base web interface
        try:
            self.base_interface = BaseWebInterfaceManager()
        except Exception:
            self.base_interface = None
        
        # Project-specific monitoring data
        self.factor_data_stats = {}
        self.ml_model_performance = {}
        self.trading_stats = {}

    def start_interface_and_open_browser(self, port: int = 5000):
        """
        Start the web interface and open browser.
        
        Args:
            port: Port number for the web server
        """
        try:
            if self.base_interface and hasattr(self.base_interface, 'start_interface_and_open_browser'):
                # Use existing web interface if available
                self.base_interface.start_interface_and_open_browser(port)
            else:
                # Start simple monitoring interface
                self._start_simple_interface(port)
                
            self.is_running = True
            
        except Exception as e:
            print(f"Warning: Could not start web interface: {e}")
            print("Continuing with backtest execution...")

    def _start_simple_interface(self, port: int):
        """Start a simple monitoring interface if full web interface unavailable."""
        def simple_monitor():
            print(f"Simple monitoring interface started on port {port}")
            print("Progress updates will be displayed in console...")
            
            while self.is_running:
                try:
                    # Process progress messages
                    message = self.progress_queue.get(timeout=1.0)
                    timestamp = message.get('timestamp', 'Unknown')
                    level = message.get('level', 'INFO')
                    content = message.get('message', '')
                    
                    print(f"[{timestamp}] {level}: {content}")
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Error in simple monitor: {e}")
        
        self.web_thread = threading.Thread(target=simple_monitor, daemon=True)
        self.web_thread.start()

    def update_factor_data_stats(self, stats: Dict[str, Any]):
        """
        Update factor data statistics for web display.
        
        Args:
            stats: Dictionary containing factor data statistics
        """
        self.factor_data_stats.update(stats)
        
        # Send update to progress queue for display
        self.progress_queue.put({
            'timestamp': 'now',
            'level': 'INFO',
            'message': f"Factor data updated: {len(stats)} metrics"
        })

    def update_ml_model_performance(self, model_name: str, metrics: Dict[str, float]):
        """
        Update ML model performance metrics.
        
        Args:
            model_name: Name of the ML model
            metrics: Performance metrics dictionary
        """
        self.ml_model_performance[model_name] = metrics
        
        # Send update to progress queue
        self.progress_queue.put({
            'timestamp': 'now',
            'level': 'INFO', 
            'message': f"Model {model_name} performance updated: {metrics}"
        })

    def update_trading_stats(self, stats: Dict[str, Any]):
        """
        Update trading statistics.
        
        Args:
            stats: Dictionary containing trading statistics
        """
        self.trading_stats.update(stats)
        
        # Send update to progress queue
        self.progress_queue.put({
            'timestamp': 'now',
            'level': 'INFO',
            'message': f"Trading stats updated: {stats}"
        })

    def send_progress_update(self, message: str, level: str = 'INFO'):
        """
        Send a progress update to the web interface.
        
        Args:
            message: Progress message
            level: Message level (INFO, WARNING, ERROR)
        """
        import datetime
        
        self.progress_queue.put({
            'timestamp': datetime.datetime.now().isoformat(),
            'level': level,
            'message': message
        })

    def get_current_stats(self) -> Dict[str, Any]:
        """
        Get current statistics for web display.
        
        Returns:
            Dictionary containing all current statistics
        """
        return {
            'factor_data': self.factor_data_stats,
            'ml_models': self.ml_model_performance,
            'trading': self.trading_stats,
            'interface_status': 'running' if self.is_running else 'stopped'
        }

    def stop_interface(self):
        """Stop the web interface."""
        try:
            self.is_running = False
            
            if self.base_interface and hasattr(self.base_interface, 'stop'):
                self.base_interface.stop()
                
            # Signal simple monitor to stop
            self.progress_queue.put({
                'timestamp': 'now',
                'level': 'INFO',
                'message': 'Web interface stopping...'
            })
            
            if self.web_thread and self.web_thread.is_alive():
                self.web_thread.join(timeout=5.0)
                
        except Exception as e:
            print(f"Error stopping web interface: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_interface()