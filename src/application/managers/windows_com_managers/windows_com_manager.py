#!/usr/bin/env python3
"""
Windows COM Manager

This module provides a base class for managing Windows COM applications using win32com.
It handles connection, method execution, and disconnection from COM applications.

Usage:
    from application.managers.windows_com_managers.windows_com_manager import WindowsCOMManager
    
    class MyAppManager(WindowsCOMManager):
        def __init__(self):
            super().__init__()
            self.connect_to_app("MyApp.Application")
"""

import logging
from typing import Any, Optional
from abc import ABC

try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False
    logging.warning("win32com.client not available. COM functionality will be limited.")

# Configure logging
logger = logging.getLogger(__name__)


class WindowsCOMManager(ABC):
    """
    Base class for managing Windows COM applications.
    
    This class provides core functionality for connecting to COM applications,
    executing methods, and handling disconnections. It serves as a parent class
    for specific COM application managers.
    """
    
    def __init__(self):
        """
        Initialize the WindowsCOMManager.
        
        Sets up the basic COM manager with error handling and logging.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.app = None
        self.is_connected = False
        self.app_name = None
        
        if not WIN32COM_AVAILABLE:
            self.logger.warning("win32com.client is not available. COM operations will be simulated.")
    
    def connect_to_app(self, app_name: str, visible: bool = True) -> bool:
        """
        Connect to a Windows COM application.
        
        Args:
            app_name: Name of the COM application (e.g., "Excel.Application")
            visible: Whether to make the application visible (default: True)
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not WIN32COM_AVAILABLE:
                self.logger.warning(f"Simulating connection to {app_name} (win32com not available)")
                self.app_name = app_name
                self.is_connected = True
                return True
            
            self.logger.info(f"Connecting to COM application: {app_name}")
            
            # Try to get existing instance first, then create new if needed
            try:
                self.app = win32com.client.GetActiveObject(app_name)
                self.logger.info(f"Connected to existing {app_name} instance")
            except:
                self.app = win32com.client.Dispatch(app_name)
                self.logger.info(f"Created new {app_name} instance")
            
            # Set visibility if supported
            if hasattr(self.app, 'Visible'):
                self.app.Visible = visible
                self.logger.debug(f"Set {app_name} visibility to {visible}")
            
            self.app_name = app_name
            self.is_connected = True
            self.logger.info(f"Successfully connected to {app_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to {app_name}: {e}")
            self.app = None
            self.is_connected = False
            return False
    
    def execute_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a method on the connected COM application.
        
        Args:
            method_name: Name of the method to execute
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method
        
        Returns:
            Any: Result of the method execution, or None if failed
        """
        if not self.is_connected:
            self.logger.error("Not connected to any COM application")
            return None
        
        try:
            if not WIN32COM_AVAILABLE:
                self.logger.warning(f"Simulating method execution: {method_name} with args {args}, kwargs {kwargs}")
                return f"Simulated result for {method_name}"
            
            self.logger.debug(f"Executing method: {method_name} with args {args}")
            
            # Get the method from the COM object
            if hasattr(self.app, method_name):
                method = getattr(self.app, method_name)
                
                # Execute the method
                if callable(method):
                    result = method(*args, **kwargs)
                    self.logger.debug(f"Method {method_name} executed successfully")
                    return result
                else:
                    # If it's a property, return its value
                    self.logger.debug(f"Accessing property: {method_name}")
                    return method
            else:
                self.logger.error(f"Method or property '{method_name}' not found in {self.app_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error executing method '{method_name}': {e}")
            return None
    
    def get_property(self, property_name: str) -> Any:
        """
        Get a property value from the connected COM application.
        
        Args:
            property_name: Name of the property to get
        
        Returns:
            Any: Value of the property, or None if failed
        """
        if not self.is_connected:
            self.logger.error("Not connected to any COM application")
            return None
        
        try:
            if not WIN32COM_AVAILABLE:
                self.logger.warning(f"Simulating property access: {property_name}")
                return f"Simulated value for {property_name}"
            
            if hasattr(self.app, property_name):
                value = getattr(self.app, property_name)
                self.logger.debug(f"Retrieved property '{property_name}': {value}")
                return value
            else:
                self.logger.error(f"Property '{property_name}' not found in {self.app_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting property '{property_name}': {e}")
            return None
    
    def set_property(self, property_name: str, value: Any) -> bool:
        """
        Set a property value in the connected COM application.
        
        Args:
            property_name: Name of the property to set
            value: Value to set
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Not connected to any COM application")
            return False
        
        try:
            if not WIN32COM_AVAILABLE:
                self.logger.warning(f"Simulating property set: {property_name} = {value}")
                return True
            
            if hasattr(self.app, property_name):
                setattr(self.app, property_name, value)
                self.logger.debug(f"Set property '{property_name}' to: {value}")
                return True
            else:
                self.logger.error(f"Property '{property_name}' not found in {self.app_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error setting property '{property_name}': {e}")
            return False
    
    def disconnect_app(self) -> bool:
        """
        Disconnect from the COM application.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        try:
            if not self.is_connected:
                self.logger.warning("No active COM connection to disconnect")
                return True
            
            if not WIN32COM_AVAILABLE:
                self.logger.warning("Simulating disconnection from COM application")
                self.app = None
                self.is_connected = False
                self.app_name = None
                return True
            
            self.logger.info(f"Disconnecting from {self.app_name}")
            
            # Try to quit the application if it has a Quit method
            if self.app and hasattr(self.app, 'Quit'):
                try:
                    self.app.Quit()
                    self.logger.debug(f"Called Quit() on {self.app_name}")
                except:
                    self.logger.debug(f"Quit() not available or failed for {self.app_name}")
            
            # Release COM object
            if self.app:
                try:
                    # Release the COM object
                    self.app = None
                    self.logger.debug("COM object released")
                except:
                    self.logger.debug("Error releasing COM object")
            
            self.is_connected = False
            self.app_name = None
            self.logger.info("Successfully disconnected from COM application")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from COM application: {e}")
            return False
    
    def is_app_connected(self) -> bool:
        """
        Check if the COM application is currently connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.is_connected and self.app is not None
    
    def get_app_name(self) -> Optional[str]:
        """
        Get the name of the currently connected COM application.
        
        Returns:
            Optional[str]: Name of the connected application, or None if not connected
        """
        return self.app_name if self.is_connected else None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure disconnection."""
        self.disconnect_app()
    
    def __del__(self):
        """Destructor - ensure COM object is released."""
        try:
            self.disconnect_app()
        except:
            pass  # Ignore errors during cleanup


# Error classes for COM operations
class COMConnectionError(Exception):
    """Raised when COM connection fails."""
    pass


class COMMethodError(Exception):
    """Raised when COM method execution fails."""
    pass


class COMPropertyError(Exception):
    """Raised when COM property access fails."""
    pass


# Utility functions
def is_win32com_available() -> bool:
    """
    Check if win32com is available.
    
    Returns:
        bool: True if win32com is available, False otherwise
    """
    return WIN32COM_AVAILABLE


def get_available_com_applications() -> list:
    """
    Get a list of commonly used COM application names.
    
    Returns:
        list: List of common COM application names
    """
    return [
        "Excel.Application",
        "Word.Application", 
        "PowerPoint.Application",
        "Outlook.Application",
        "Access.Application",
        "Visio.Application",
        "Publisher.Application"
    ]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test the base COM manager
    with WindowsCOMManager() as com_manager:
        # This would normally connect to a real COM application
        success = com_manager.connect_to_app("TestApp.Application")
        
        if success:
            # Execute some methods
            result = com_manager.execute_method("TestMethod", "arg1", "arg2")
            print(f"Method result: {result}")
            
            # Get a property
            prop_value = com_manager.get_property("TestProperty")
            print(f"Property value: {prop_value}")
            
            # Set a property
            com_manager.set_property("TestProperty", "new_value")
    
    print("COM Manager test completed")