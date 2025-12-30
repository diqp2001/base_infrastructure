import os
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import mlflow
import mlflow.sklearn
import mlflow.pytorch

# Base classes
from src.application.services.database_service.database_service import DatabaseService
from src.application.managers.project_managers.project_manager import ProjectManager

# Interactive Brokers integration
from src.application.services.misbuffet.brokers.broker_factory import BrokerFactory, create_interactive_brokers_broker
from application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker

# Backtesting components
from .backtesting.backtest_runner import BacktestRunner
from .backtesting.base_project_algorithm import BaseProjectAlgorithm

# Data components

from .data.factor_manager import FactorEnginedDataManager



# Configuration
from .config import DEFAULT_CONFIG, get_config
from . import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectManager(ProjectManager):
    """
    Enhanced Project Manager for backtesting operations.
    Implements a complete backtesting pipeline using  Misbuffet framework integration.
    
    
    """
    
    def __init__(self):
        """
        Initialize the Test Base Project Manager following TestProjectBacktestManager pattern.
        """
        super().__init__()
        
        # Initialize required managers - use TEST config like test_project_backtest
        self.setup_database_service(DatabaseService(config.CONFIG_TEST['DB_TYPE']))
        self.database_service.set_ext_db()
        # Initialize core components
        self.factor_manager = FactorEnginedDataManager(self.database_service)
        # Backtesting components
        self.backtest_runner = BacktestRunner(self.database_service)
        self.algorithm = None
        self.results = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Web interface manager
        try:
            from src.application.services.misbuffet.web.web_interface import WebInterfaceManager
            self.web_interface = WebInterfaceManager()
        except ImportError:
            self.logger.warning("Web interface not available")
            self.web_interface = None
        
        # Runtime state
        self.trained_model = None
        self.strategy = None
        self.signal_generator = None
        self.pipeline_results = {}
        
        # Interactive Brokers broker
        self.ib_broker: Optional[InteractiveBrokersBroker] = None
        
        # MLflow tracking setup
        self.mlflow_experiment_name = "market_making_call_spread_spx_project_manager"
        self.mlflow_run = None
        self._setup_mlflow_tracking()
        
        self.logger.info("🚀 Market making Call Spread SPX ProjectManager initialized with Misbuffet integration and MLflow tracking")