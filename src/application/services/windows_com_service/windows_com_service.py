# src/application/services/windows_com_service.py
import logging
from typing import Any, Optional, Dict, List
from abc import ABC
import platform
import sys

# Check if running on Windows and try to import win32com
WIN32COM_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import win32com.client
        import pywintypes
        WIN32COM_AVAILABLE = True
    except ImportError:
        pass

if not WIN32COM_AVAILABLE:
    logging.warning("win32com.client not available. COM functionality will be limited.")

# Configure logging
logger = logging.getLogger(__name__)


class WindowsComService:
    """
    Service class for managing Windows COM applications using win32com.
    Handles connection, method execution, and disconnection from COM applications.
    
    This service provides a clean interface for COM operations on Windows systems.
    """

    def __init__(self, auto_connect: bool = False):
        """
        Initialize the Windows COM service.
        :param auto_connect: Whether to automatically handle connections.
        """
        self.app = None
        self.app_name = None
        self.is_connected = False
        self.auto_connect = auto_connect
        self.connection_config = {}
        self.last_error = None
        
        if not WIN32COM_AVAILABLE:
            logger.warning("Windows COM functionality not available on this system")

    def connect_to_app(self, app_name: str, visible: bool = True, 
                      create_new: bool = False) -> bool:
        """
        Connect to a COM application.
        :param app_name: Name of the COM application (e.g., 'Excel.Application').
        :param visible: Whether the application should be visible.
        :param create_new: Whether to create a new instance.
        :return: True if connection successful, False otherwise.
        """
        if not WIN32COM_AVAILABLE:
            logger.error("COM functionality not available")
            return False

        try:
            if create_new:
                self.app = win32com.client.Dispatch(app_name)
            else:
                try:
                    # Try to connect to existing instance
                    self.app = win32com.client.GetActiveObject(app_name)
                except pywintypes.com_error:
                    # If no active instance, create new one
                    self.app = win32com.client.Dispatch(app_name)

            self.app_name = app_name
            
            # Set visibility if application supports it
            try:
                if hasattr(self.app, 'Visible'):
                    self.app.Visible = visible
            except Exception as e:
                logger.warning(f"Could not set visibility: {e}")

            self.is_connected = True
            self.connection_config = {
                'app_name': app_name,
                'visible': visible,
                'create_new': create_new
            }
            
            logger.info(f"Successfully connected to {app_name}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to connect to {app_name}: {e}")
            return False

    def disconnect(self) -> bool:
        """
        Disconnect from the COM application.
        :return: True if disconnection successful, False otherwise.
        """
        if not self.is_connected:
            logger.info("No active connection to disconnect")
            return True

        try:
            if self.app:
                # Try to quit the application gracefully
                if hasattr(self.app, 'Quit'):
                    try:
                        self.app.Quit()
                    except Exception as e:
                        logger.warning(f"Could not quit application gracefully: {e}")

                # Release the COM object
                del self.app
                self.app = None

            self.is_connected = False
            self.app_name = None
            logger.info("Successfully disconnected from COM application")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error during disconnection: {e}")
            return False

    def execute_method(self, method_name: str, *args, **kwargs) -> Any:
        """
        Execute a method on the connected COM application.
        :param method_name: Name of the method to execute.
        :param args: Positional arguments for the method.
        :param kwargs: Keyword arguments for the method.
        :return: Method result or None if failed.
        """
        if not self.is_connected or not self.app:
            logger.error("No active connection to execute method")
            return None

        try:
            # Navigate to the method (support dot notation)
            obj = self.app
            method_parts = method_name.split('.')
            
            for part in method_parts[:-1]:
                obj = getattr(obj, part)
            
            method = getattr(obj, method_parts[-1])
            
            # Execute the method
            if callable(method):
                result = method(*args, **kwargs)
            else:
                # If it's a property and we have arguments, try to set it
                if args or kwargs:
                    if args:
                        setattr(obj, method_parts[-1], args[0])
                        result = args[0]
                    else:
                        # Handle keyword arguments for properties
                        result = method
                else:
                    result = method

            logger.debug(f"Successfully executed {method_name}")
            return result

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error executing method {method_name}: {e}")
            return None

    def get_property(self, property_name: str) -> Any:
        """
        Get a property value from the connected COM application.
        :param property_name: Name of the property (supports dot notation).
        :return: Property value or None if failed.
        """
        if not self.is_connected or not self.app:
            logger.error("No active connection to get property")
            return None

        try:
            # Navigate to the property (support dot notation)
            obj = self.app
            property_parts = property_name.split('.')
            
            for part in property_parts:
                obj = getattr(obj, part)
            
            logger.debug(f"Successfully retrieved property {property_name}")
            return obj

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error getting property {property_name}: {e}")
            return None

    def set_property(self, property_name: str, value: Any) -> bool:
        """
        Set a property value on the connected COM application.
        :param property_name: Name of the property (supports dot notation).
        :param value: Value to set.
        :return: True if successful, False otherwise.
        """
        if not self.is_connected or not self.app:
            logger.error("No active connection to set property")
            return False

        try:
            # Navigate to the property (support dot notation)
            obj = self.app
            property_parts = property_name.split('.')
            
            for part in property_parts[:-1]:
                obj = getattr(obj, part)
            
            setattr(obj, property_parts[-1], value)
            
            logger.debug(f"Successfully set property {property_name} = {value}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error setting property {property_name}: {e}")
            return False

    def is_application_available(self, app_name: str) -> bool:
        """
        Check if a COM application is available on the system.
        :param app_name: Name of the COM application.
        :return: True if available, False otherwise.
        """
        if not WIN32COM_AVAILABLE:
            return False

        try:
            win32com.client.Dispatch(app_name)
            return True
        except Exception:
            return False

    def list_com_objects(self) -> List[str]:
        """
        List available COM objects (basic implementation).
        :return: List of COM object names.
        """
        if not WIN32COM_AVAILABLE:
            return []

        # Common COM applications
        common_com_objects = [
            'Excel.Application',
            'Word.Application',
            'PowerPoint.Application',
            'Outlook.Application',
            'Access.Application',
            'Shell.Application',
            'Scripting.FileSystemObject',
            'WScript.Shell'
        ]

        available_objects = []
        for obj_name in common_com_objects:
            if self.is_application_available(obj_name):
                available_objects.append(obj_name)

        return available_objects

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status information.
        :return: Dictionary with connection status.
        """
        return {
            'is_connected': self.is_connected,
            'app_name': self.app_name,
            'com_available': WIN32COM_AVAILABLE,
            'platform': platform.system(),
            'last_error': self.last_error,
            'connection_config': self.connection_config.copy() if self.connection_config else {}
        }

    def create_object(self, class_name: str) -> Any:
        """
        Create a new COM object.
        :param class_name: Name of the COM class.
        :return: COM object instance or None if failed.
        """
        if not WIN32COM_AVAILABLE:
            logger.error("COM functionality not available")
            return None

        try:
            obj = win32com.client.Dispatch(class_name)
            logger.info(f"Successfully created COM object: {class_name}")
            return obj

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error creating COM object {class_name}: {e}")
            return None

    def safe_execute(self, operation: callable, *args, **kwargs) -> tuple[bool, Any]:
        """
        Safely execute a COM operation with error handling.
        :param operation: Operation to execute.
        :param args: Positional arguments.
        :param kwargs: Keyword arguments.
        :return: Tuple of (success, result).
        """
        try:
            result = operation(*args, **kwargs)
            return True, result

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error in safe execution: {e}")
            return False, None

    def reconnect(self) -> bool:
        """
        Reconnect using the last connection configuration.
        :return: True if reconnection successful, False otherwise.
        """
        if not self.connection_config:
            logger.error("No connection configuration available for reconnection")
            return False

        return self.connect_to_app(**self.connection_config)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure disconnection."""
        self.disconnect()

    def __del__(self):
        """Destructor - ensure disconnection."""
        if hasattr(self, 'is_connected') and self.is_connected:
            self.disconnect()


class ExcelComService(WindowsComService):
    """Specialized service for Excel COM operations."""
    
    def __init__(self):
        super().__init__()
        self.workbooks = {}
        self.worksheets = {}

    def connect_to_excel(self, visible: bool = True) -> bool:
        """Connect to Excel application."""
        return self.connect_to_app('Excel.Application', visible=visible)

    def open_workbook(self, file_path: str, workbook_name: str = None) -> bool:
        """
        Open an Excel workbook.
        :param file_path: Path to the Excel file.
        :param workbook_name: Optional name to reference the workbook.
        :return: True if successful, False otherwise.
        """
        try:
            if not self.is_connected:
                if not self.connect_to_excel():
                    return False

            workbook = self.app.Workbooks.Open(file_path)
            wb_name = workbook_name or workbook.Name
            self.workbooks[wb_name] = workbook
            
            logger.info(f"Opened workbook: {file_path}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error opening workbook {file_path}: {e}")
            return False

    def create_workbook(self, workbook_name: str = None) -> bool:
        """
        Create a new Excel workbook.
        :param workbook_name: Optional name to reference the workbook.
        :return: True if successful, False otherwise.
        """
        try:
            if not self.is_connected:
                if not self.connect_to_excel():
                    return False

            workbook = self.app.Workbooks.Add()
            wb_name = workbook_name or workbook.Name
            self.workbooks[wb_name] = workbook
            
            logger.info(f"Created new workbook: {wb_name}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error creating workbook: {e}")
            return False

    def save_workbook(self, workbook_name: str, file_path: str = None) -> bool:
        """
        Save a workbook.
        :param workbook_name: Name of the workbook to save.
        :param file_path: Optional file path for Save As.
        :return: True if successful, False otherwise.
        """
        try:
            if workbook_name not in self.workbooks:
                logger.error(f"Workbook {workbook_name} not found")
                return False

            workbook = self.workbooks[workbook_name]
            
            if file_path:
                workbook.SaveAs(file_path)
            else:
                workbook.Save()
            
            logger.info(f"Saved workbook: {workbook_name}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error saving workbook {workbook_name}: {e}")
            return False

    def close_workbook(self, workbook_name: str, save: bool = True) -> bool:
        """
        Close a workbook.
        :param workbook_name: Name of the workbook to close.
        :param save: Whether to save before closing.
        :return: True if successful, False otherwise.
        """
        try:
            if workbook_name not in self.workbooks:
                logger.error(f"Workbook {workbook_name} not found")
                return False

            workbook = self.workbooks[workbook_name]
            workbook.Close(SaveChanges=save)
            del self.workbooks[workbook_name]
            
            logger.info(f"Closed workbook: {workbook_name}")
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error closing workbook {workbook_name}: {e}")
            return False

    def get_worksheet(self, workbook_name: str, sheet_name: str = None, sheet_index: int = None):
        """
        Get a worksheet from a workbook.
        :param workbook_name: Name of the workbook.
        :param sheet_name: Name of the sheet.
        :param sheet_index: Index of the sheet (1-based).
        :return: Worksheet object or None.
        """
        try:
            if workbook_name not in self.workbooks:
                logger.error(f"Workbook {workbook_name} not found")
                return None

            workbook = self.workbooks[workbook_name]
            
            if sheet_name:
                worksheet = workbook.Worksheets(sheet_name)
            elif sheet_index:
                worksheet = workbook.Worksheets(sheet_index)
            else:
                worksheet = workbook.ActiveSheet
            
            return worksheet

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error getting worksheet: {e}")
            return None

    def read_range(self, workbook_name: str, sheet_name: str, range_address: str) -> Any:
        """
        Read a range of cells from Excel.
        :param workbook_name: Name of the workbook.
        :param sheet_name: Name of the worksheet.
        :param range_address: Excel range address (e.g., 'A1:C10').
        :return: Cell values or None if failed.
        """
        try:
            worksheet = self.get_worksheet(workbook_name, sheet_name)
            if not worksheet:
                return None

            range_obj = worksheet.Range(range_address)
            return range_obj.Value

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error reading range {range_address}: {e}")
            return None

    def write_range(self, workbook_name: str, sheet_name: str, 
                   range_address: str, values: Any) -> bool:
        """
        Write values to a range of cells in Excel.
        :param workbook_name: Name of the workbook.
        :param sheet_name: Name of the worksheet.
        :param range_address: Excel range address (e.g., 'A1:C10').
        :param values: Values to write.
        :return: True if successful, False otherwise.
        """
        try:
            worksheet = self.get_worksheet(workbook_name, sheet_name)
            if not worksheet:
                return False

            range_obj = worksheet.Range(range_address)
            range_obj.Value = values
            
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error writing to range {range_address}: {e}")
            return False