"""
QuantConnect Lean Launcher Interfaces

Defines the core interfaces for the launcher module including system handlers,
algorithm handlers, and configuration contracts.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging


class LauncherMode(Enum):
    """Launcher execution modes."""
    BACKTESTING = "backtesting"
    LIVE_TRADING = "live_trading"
    OPTIMIZATION = "optimization"
    RESEARCH = "research"


class LauncherStatus(Enum):
    """Launcher execution status."""
    INITIALIZING = "initializing"
    LOADING_CONFIG = "loading_config"
    CREATING_HANDLERS = "creating_handlers"
    STARTING_ENGINE = "starting_engine"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LauncherConfiguration:
    """Configuration data for launcher execution."""
    
    # Execution parameters
    mode: LauncherMode
    algorithm_type_name: str
    algorithm_location: str
    data_folder: str
    
    # Environment settings
    environment: str = "backtesting"
    live_mode: bool = False
    
    # Handler configurations
    log_handler: str = "ConsoleLogHandler"
    messaging_handler: str = "NullMessagingHandler"
    job_queue_handler: str = "JobQueue"
    api_handler: str = "Api"
    
    # Advanced settings
    debugging: bool = False
    show_missing_data_logs: bool = True
    maximum_data_points_per_chart_series: int = 4000
    maximum_chart_series: int = 30
    
    # Custom configurations
    custom_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_config is None:
            self.custom_config = {}


class ILauncherSystemHandlers(ABC):
    """Interface for system-level handlers in the launcher."""
    
    @property
    @abstractmethod
    def log_handler(self) -> logging.Handler:
        """Gets the log handler."""
        pass
    
    @property
    @abstractmethod
    def messaging_handler(self):
        """Gets the messaging handler."""
        pass
    
    @property
    @abstractmethod
    def job_queue_handler(self):
        """Gets the job queue handler."""
        pass
    
    @property
    @abstractmethod
    def api_handler(self):
        """Gets the API handler."""
        pass
    
    @property
    @abstractmethod
    def data_permission_manager(self):
        """Gets the data permission manager."""
        pass


class ILauncherAlgorithmHandlers(ABC):
    """Interface for algorithm-specific handlers in the launcher."""
    
    @property
    @abstractmethod
    def data_feed(self):
        """Gets the data feed handler."""
        pass
    
    @property
    @abstractmethod
    def setup_handler(self):
        """Gets the setup handler."""
        pass
    
    @property
    @abstractmethod
    def real_time_handler(self):
        """Gets the real-time handler."""
        pass
    
    @property
    @abstractmethod
    def result_handler(self):
        """Gets the result handler."""
        pass
    
    @property
    @abstractmethod
    def transaction_handler(self):
        """Gets the transaction handler."""
        pass
    
    @property
    @abstractmethod
    def history_provider(self):
        """Gets the history provider."""
        pass
    
    @property
    @abstractmethod
    def command_queue_handler(self):
        """Gets the command queue handler."""
        pass
    
    @property
    @abstractmethod
    def map_file_provider(self):
        """Gets the map file provider."""
        pass
    
    @property
    @abstractmethod
    def factor_file_provider(self):
        """Gets the factor file provider."""  
        pass
    
    @property
    @abstractmethod
    def data_provider(self):
        """Gets the data provider."""
        pass
    
    @property
    @abstractmethod
    def alpha_handler(self):
        """Gets the alpha handler."""
        pass
    
    @property
    @abstractmethod
    def object_store(self):
        """Gets the object store."""
        pass


class IConfigurationProvider(ABC):
    """Interface for configuration providers."""
    
    @abstractmethod
    def load_configuration(self, config_path: Optional[str] = None) -> LauncherConfiguration:
        """
        Load configuration from various sources.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            LauncherConfiguration instance
        """
        pass
    
    @abstractmethod
    def validate_configuration(self, config: LauncherConfiguration) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        pass


class ILauncher(ABC):
    """Interface for the main launcher."""
    
    @abstractmethod
    def initialize(self, config: LauncherConfiguration) -> bool:
        """
        Initialize the launcher with given configuration.
        
        Args:
            config: Launcher configuration
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    def run(self) -> bool:
        """
        Run the launcher.
        
        Returns:
            True if execution successful
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the launcher gracefully.
        
        Returns:
            True if stop successful
        """
        pass
    
    @property
    @abstractmethod
    def status(self) -> LauncherStatus:
        """Gets the current launcher status."""
        pass


class IHandlerFactory(ABC):
    """Interface for handler factories."""
    
    @abstractmethod
    def create_system_handlers(self, config: LauncherConfiguration) -> ILauncherSystemHandlers:
        """
        Create system handlers based on configuration.
        
        Args:
            config: Launcher configuration
            
        Returns:
            System handlers instance
        """
        pass
    
    @abstractmethod
    def create_algorithm_handlers(self, config: LauncherConfiguration) -> ILauncherAlgorithmHandlers:
        """
        Create algorithm handlers based on configuration.
        
        Args:
            config: Launcher configuration
            
        Returns:
            Algorithm handlers instance
        """
        pass


class ICommandLineParser(ABC):
    """Interface for command-line argument parsing."""
    
    @abstractmethod
    def parse_arguments(self, args: List[str]) -> Dict[str, Any]:
        """
        Parse command-line arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Parsed arguments dictionary
        """
        pass
    
    @abstractmethod
    def get_help_text(self) -> str:
        """
        Get help text for command-line usage.
        
        Returns:
            Help text string
        """
        pass


class ILauncherLogger(ABC):
    """Interface for launcher-specific logging."""
    
    @abstractmethod
    def log_initialization_start(self, config: LauncherConfiguration) -> None:
        """Log initialization start."""
        pass
    
    @abstractmethod
    def log_initialization_complete(self) -> None:
        """Log initialization completion."""
        pass
    
    @abstractmethod
    def log_execution_start(self) -> None:
        """Log execution start."""
        pass
    
    @abstractmethod
    def log_execution_complete(self, success: bool) -> None:
        """Log execution completion."""
        pass
    
    @abstractmethod
    def log_error(self, error: Exception, context: str = "") -> None:
        """Log error with context."""
        pass
    
    @abstractmethod
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        pass


class LauncherException(Exception):
    """Base exception for launcher operations."""
    
    def __init__(self, message: str, inner_exception: Optional[Exception] = None):
        super().__init__(message)
        self.inner_exception = inner_exception


class ConfigurationException(LauncherException):
    """Exception for configuration-related errors."""
    pass


class HandlerCreationException(LauncherException):
    """Exception for handler creation errors."""
    pass


class EngineInitializationException(LauncherException):
    """Exception for engine initialization errors."""
    pass


class AlgorithmLoadException(LauncherException):
    """Exception for algorithm loading errors."""
    pass