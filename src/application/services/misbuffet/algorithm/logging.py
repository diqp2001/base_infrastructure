import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from .enums import LogLevel


class AlgorithmLogger:
    """
    Enhanced logging system for algorithm frameworks.
    Provides structured logging with multiple levels and formatting options.
    """
    
    def __init__(self, name: str = "QCAlgorithm", level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self._logs: List[Dict[str, Any]] = []
        
        # Setup Python logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, level.value.upper()))
        
        # Create console handler if not exists
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method"""
        timestamp = datetime.now()
        
        # Store in internal log
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'metadata': kwargs
        }
        self._logs.append(log_entry)
        
        # Forward to Python logger
        python_level = getattr(logging, level.value.upper())
        self._logger.log(python_level, message, extra=kwargs)
    
    def trace(self, message: str, **kwargs):
        """Log trace level message"""
        self._log(LogLevel.TRACE, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error level message"""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical level message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Generic log method"""
        self._log(level, message, **kwargs)
    
    def get_logs(self, level: Optional[LogLevel] = None, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve logged messages with optional filtering"""
        logs = self._logs
        
        if level:
            logs = [log for log in logs if log['level'] == level]
        
        if count:
            logs = logs[-count:]
        
        return logs
    
    def clear_logs(self):
        """Clear all stored logs"""
        self._logs.clear()
    
    def set_level(self, level: LogLevel):
        """Set the logging level"""
        self.level = level
        self._logger.setLevel(getattr(logging, level.value.upper()))


# Global logger instance
_global_logger = AlgorithmLogger()


def log(message: str, level: LogLevel = LogLevel.INFO, **kwargs):
    """Global log function for backward compatibility"""
    _global_logger.log(message, level, **kwargs)


def debug(message: str, **kwargs):
    """Global debug function"""
    _global_logger.debug(message, **kwargs)


def info(message: str, **kwargs):
    """Global info function"""
    _global_logger.info(message, **kwargs)


def warning(message: str, **kwargs):
    """Global warning function"""
    _global_logger.warning(message, **kwargs)


def error(message: str, **kwargs):
    """Global error function"""
    _global_logger.error(message, **kwargs)


def critical(message: str, **kwargs):
    """Global critical function"""
    _global_logger.critical(message, **kwargs)


def trace(message: str, **kwargs):
    """Global trace function"""
    _global_logger.trace(message, **kwargs)


def set_log_level(level: LogLevel):
    """Set the global logging level"""
    _global_logger.set_level(level)


def get_logger(name: str = "QCAlgorithm") -> AlgorithmLogger:
    """Get a named logger instance"""
    return AlgorithmLogger(name)
