#!/usr/bin/env python3
"""
Excel Manager

This module provides a specialized COM manager for Microsoft Excel operations.
It extends the base WindowsCOMManager to provide Excel-specific functionality
such as workbook management, worksheet operations, and data manipulation.

Usage:
    from application.managers.windows_com_managers.excel_manager import ExcelManager
    import pandas as pd
    
    with ExcelManager() as excel:
        workbook = excel.create_workbook("data.xlsx")
        sheet = excel.get_sheet("Sheet1", workbook)
        
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        excel.write_dataframe_to_sheet(sheet, df)
        excel.save_workbook(workbook, "data.xlsx")
"""

import logging
import os
from typing import Any, Optional, Union, Dict
from pathlib import Path

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("pandas not available. DataFrame operations will be limited.")

from .windows_com_manager import WindowsCOMManager, COMConnectionError, COMMethodError

# Configure logging
logger = logging.getLogger(__name__)


class ExcelManager(WindowsCOMManager):
    """
    Excel-specific COM manager for Microsoft Excel operations.
    
    This class extends WindowsCOMManager to provide specialized functionality
    for Excel workbook and worksheet operations, data manipulation, and file management.
    """
    
    def __init__(self, visible: bool = True, auto_connect: bool = True):
        """
        Initialize the ExcelManager.
        
        Args:
            visible: Whether to make Excel visible (default: True)
            auto_connect: Whether to automatically connect to Excel (default: True)
        """
        super().__init__()
        self.visible = visible
        self.workbooks = {}  # Track opened workbooks
        
        if auto_connect:
            self.connect_to_excel()
    
    def connect_to_excel(self) -> bool:
        """
        Connect to Microsoft Excel application.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        success = self.connect_to_app("Excel.Application", visible=self.visible)
        
        if success:
            self.logger.info("Successfully connected to Excel")
            # Set some Excel-specific properties
            try:
                if self.app:
                    # Disable alerts and screen updating for better performance
                    self.set_property("DisplayAlerts", False)
                    self.set_property("ScreenUpdating", False)
                    self.logger.debug("Excel properties configured for automation")
            except:
                self.logger.debug("Could not set Excel automation properties")
        
        return success
    
    def create_workbook(self, file_path: Optional[str] = None) -> Any:
        """
        Create a new Excel workbook.
        
        Args:
            file_path: Optional path where the workbook will be saved
        
        Returns:
            Workbook object or None if failed
        """
        if not self.is_connected:
            self.logger.error("Not connected to Excel")
            return None
        
        try:
            self.logger.info(f"Creating new workbook{f' at {file_path}' if file_path else ''}")
            
            if not self.app:
                self.logger.error("Excel application not available")
                return None
            
            # Create new workbook
            if hasattr(self.app, 'Workbooks'):
                workbook = self.app.Workbooks.Add()
                
                # Track the workbook
                workbook_id = id(workbook) if workbook else "simulated"
                self.workbooks[workbook_id] = {
                    'workbook': workbook,
                    'file_path': file_path,
                    'saved': False
                }
                
                self.logger.info(f"Created workbook with ID: {workbook_id}")
                return workbook
            else:
                self.logger.error("Workbooks collection not available")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating workbook: {e}")
            return None
    
    def open_workbook(self, file_path: str) -> Any:
        """
        Open an existing Excel workbook.
        
        Args:
            file_path: Path to the Excel file to open
        
        Returns:
            Workbook object or None if failed
        """
        if not self.is_connected:
            self.logger.error("Not connected to Excel")
            return None
        
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(file_path)
            
            if not os.path.exists(abs_path):
                self.logger.error(f"File does not exist: {abs_path}")
                return None
            
            self.logger.info(f"Opening workbook: {abs_path}")
            
            if not self.app or not hasattr(self.app, 'Workbooks'):
                self.logger.error("Excel Workbooks collection not available")
                return None
            
            # Open the workbook
            workbook = self.app.Workbooks.Open(abs_path)
            
            # Track the workbook
            workbook_id = id(workbook) if workbook else "simulated"
            self.workbooks[workbook_id] = {
                'workbook': workbook,
                'file_path': abs_path,
                'saved': True
            }
            
            self.logger.info(f"Opened workbook: {abs_path}")
            return workbook
            
        except Exception as e:
            self.logger.error(f"Error opening workbook '{file_path}': {e}")
            return None
    
    def save_workbook(self, workbook: Any, file_path: Optional[str] = None) -> bool:
        """
        Save an Excel workbook.
        
        Args:
            workbook: Workbook object to save
            file_path: Optional path to save the workbook to
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected or not workbook:
            self.logger.error("Not connected to Excel or invalid workbook")
            return False
        
        try:
            # Find workbook in our tracking
            workbook_id = id(workbook)
            workbook_info = self.workbooks.get(workbook_id)
            
            if file_path:
                # Save with specific file path
                abs_path = os.path.abspath(file_path)
                self.logger.info(f"Saving workbook to: {abs_path}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                
                if hasattr(workbook, 'SaveAs'):
                    workbook.SaveAs(abs_path)
                else:
                    self.logger.warning("SaveAs method not available, simulating save")
                
                # Update tracking info
                if workbook_info:
                    workbook_info['file_path'] = abs_path
                    workbook_info['saved'] = True
                    
            else:
                # Save to existing location
                if workbook_info and workbook_info.get('file_path'):
                    self.logger.info(f"Saving workbook to existing location: {workbook_info['file_path']}")
                    
                    if hasattr(workbook, 'Save'):
                        workbook.Save()
                    else:
                        self.logger.warning("Save method not available, simulating save")
                    
                    workbook_info['saved'] = True
                else:
                    self.logger.error("No file path specified and workbook has no existing path")
                    return False
            
            self.logger.info("Workbook saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving workbook: {e}")
            return False
    
    def close_workbook(self, workbook: Any, save: bool = True) -> bool:
        """
        Close an Excel workbook.
        
        Args:
            workbook: Workbook object to close
            save: Whether to save before closing (default: True)
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not workbook:
            self.logger.error("Invalid workbook object")
            return False
        
        try:
            workbook_id = id(workbook)
            workbook_info = self.workbooks.get(workbook_id)
            
            self.logger.info(f"Closing workbook (save={save})")
            
            if hasattr(workbook, 'Close'):
                workbook.Close(SaveChanges=save)
            else:
                self.logger.warning("Close method not available, simulating close")
            
            # Remove from tracking
            if workbook_id in self.workbooks:
                del self.workbooks[workbook_id]
            
            self.logger.info("Workbook closed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing workbook: {e}")
            return False
    
    def add_sheet(self, workbook: Any, sheet_name: str) -> Any:
        """
        Add a new worksheet to a workbook.
        
        Args:
            workbook: Workbook object to add sheet to
            sheet_name: Name for the new worksheet
        
        Returns:
            Worksheet object or None if failed
        """
        if not workbook:
            self.logger.error("Invalid workbook object")
            return None
        
        try:
            self.logger.info(f"Adding worksheet: {sheet_name}")
            
            if hasattr(workbook, 'Worksheets'):
                worksheets = workbook.Worksheets
                sheet = worksheets.Add()
                
                # Set the sheet name
                if hasattr(sheet, 'Name'):
                    sheet.Name = sheet_name
                
                self.logger.info(f"Added worksheet: {sheet_name}")
                return sheet
            else:
                self.logger.error("Worksheets collection not available")
                return None
                
        except Exception as e:
            self.logger.error(f"Error adding worksheet '{sheet_name}': {e}")
            return None
    
    def get_sheet(self, sheet_name: str, workbook: Any) -> Any:
        """
        Get a worksheet from a workbook by name.
        
        Args:
            sheet_name: Name of the worksheet to get
            workbook: Workbook object containing the worksheet
        
        Returns:
            Worksheet object or None if not found
        """
        if not workbook:
            self.logger.error("Invalid workbook object")
            return None
        
        try:
            self.logger.debug(f"Getting worksheet: {sheet_name}")
            
            if hasattr(workbook, 'Worksheets'):
                worksheets = workbook.Worksheets
                
                # Try to get sheet by name
                try:
                    sheet = worksheets[sheet_name]
                    self.logger.debug(f"Found worksheet: {sheet_name}")
                    return sheet
                except:
                    # Sheet not found by name, try by index if it's a number
                    try:
                        if sheet_name.isdigit():
                            sheet = worksheets[int(sheet_name)]
                            self.logger.debug(f"Found worksheet by index: {sheet_name}")
                            return sheet
                    except:
                        pass
                    
                    self.logger.error(f"Worksheet '{sheet_name}' not found")
                    return None
            else:
                self.logger.error("Worksheets collection not available")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting worksheet '{sheet_name}': {e}")
            return None
    
    def write_dataframe_to_sheet(self, sheet: Any, dataframe: Any, start_cell: str = "A1", include_header: bool = True) -> bool:
        """
        Write a pandas DataFrame to an Excel worksheet.
        
        Args:
            sheet: Worksheet object to write to
            dataframe: pandas DataFrame to write
            start_cell: Starting cell (e.g., "A1")
            include_header: Whether to include column headers
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not sheet:
            self.logger.error("Invalid worksheet object")
            return False
        
        if not PANDAS_AVAILABLE:
            self.logger.error("pandas not available for DataFrame operations")
            return False
        
        try:
            self.logger.info(f"Writing DataFrame to sheet starting at {start_cell}")
            
            # Convert DataFrame to list of lists for COM interface
            if include_header:
                # Include column names as first row
                data = [list(dataframe.columns)] + dataframe.values.tolist()
            else:
                data = dataframe.values.tolist()
            
            # Parse start cell (e.g., "A1" -> column A, row 1)
            start_col, start_row = self._parse_cell_reference(start_cell)
            
            # Write data to Excel
            if hasattr(sheet, 'Cells'):
                for row_idx, row_data in enumerate(data):
                    for col_idx, cell_value in enumerate(row_data):
                        row_num = start_row + row_idx
                        col_num = start_col + col_idx
                        
                        # Handle different data types
                        if pd.isna(cell_value):
                            cell_value = ""
                        elif isinstance(cell_value, (pd.Timestamp, pd.Timedelta)):
                            cell_value = str(cell_value)
                        
                        sheet.Cells[row_num, col_num].Value = cell_value
                
                self.logger.info(f"Successfully wrote DataFrame ({dataframe.shape[0]} rows, {dataframe.shape[1]} cols)")
                return True
            else:
                self.logger.error("Cells collection not available")
                return False
                
        except Exception as e:
            self.logger.error(f"Error writing DataFrame to sheet: {e}")
            return False
    
    def write_replace_dataframe_to_sheet(self, sheet: Any, dataframe: Any, start_cell: str = "A1", include_header: bool = True) -> bool:
        """
        Write a pandas DataFrame to an Excel worksheet, replacing existing content.
        
        Args:
            sheet: Worksheet object to write to
            dataframe: pandas DataFrame to write
            start_cell: Starting cell (e.g., "A1")
            include_header: Whether to include column headers
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not sheet:
            self.logger.error("Invalid worksheet object")
            return False
        
        try:
            self.logger.info(f"Clearing sheet and writing DataFrame starting at {start_cell}")
            
            # Clear the worksheet first
            if hasattr(sheet, 'Cells'):
                try:
                    sheet.Cells.Clear()
                    self.logger.debug("Cleared worksheet content")
                except:
                    self.logger.debug("Could not clear worksheet content")
            
            # Write the DataFrame
            return self.write_dataframe_to_sheet(sheet, dataframe, start_cell, include_header)
            
        except Exception as e:
            self.logger.error(f"Error replacing DataFrame in sheet: {e}")
            return False
    
    def get_cell_value(self, sheet: Any, cell_reference: str) -> Any:
        """
        Get the value of a specific cell.
        
        Args:
            sheet: Worksheet object
            cell_reference: Cell reference (e.g., "A1", "B5")
        
        Returns:
            Cell value or None if failed
        """
        if not sheet:
            self.logger.error("Invalid worksheet object")
            return None
        
        try:
            col, row = self._parse_cell_reference(cell_reference)
            
            if hasattr(sheet, 'Cells'):
                value = sheet.Cells[row, col].Value
                self.logger.debug(f"Retrieved cell {cell_reference}: {value}")
                return value
            else:
                self.logger.error("Cells collection not available")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting cell value '{cell_reference}': {e}")
            return None
    
    def get_range_values(self, sheet: Any, start_cell: str, end_cell: str) -> Optional[list]:
        """
        Get values from a range of cells.
        
        Args:
            sheet: Worksheet object
            start_cell: Starting cell (e.g., "A1")
            end_cell: Ending cell (e.g., "C10")
        
        Returns:
            List of lists containing cell values, or None if failed
        """
        if not sheet:
            self.logger.error("Invalid worksheet object")
            return None
        
        try:
            self.logger.debug(f"Getting range values from {start_cell} to {end_cell}")
            
            start_col, start_row = self._parse_cell_reference(start_cell)
            end_col, end_row = self._parse_cell_reference(end_cell)
            
            if hasattr(sheet, 'Range'):
                range_obj = sheet.Range(f"{start_cell}:{end_cell}")
                values = range_obj.Value
                
                # Convert to list of lists if needed
                if not isinstance(values, (list, tuple)):
                    values = [[values]]
                elif len(values) > 0 and not isinstance(values[0], (list, tuple)):
                    values = [list(values)]
                
                self.logger.debug(f"Retrieved range values: {len(values)} rows")
                return values
            else:
                # Fallback: get values cell by cell
                values = []
                for row in range(start_row, end_row + 1):
                    row_values = []
                    for col in range(start_col, end_col + 1):
                        value = sheet.Cells[row, col].Value
                        row_values.append(value)
                    values.append(row_values)
                
                self.logger.debug(f"Retrieved range values (cell by cell): {len(values)} rows")
                return values
                
        except Exception as e:
            self.logger.error(f"Error getting range values '{start_cell}:{end_cell}': {e}")
            return None
    
    def _parse_cell_reference(self, cell_ref: str) -> tuple:
        """
        Parse a cell reference like "A1" into column and row numbers.
        
        Args:
            cell_ref: Cell reference (e.g., "A1", "BC123")
        
        Returns:
            tuple: (column_number, row_number) where A=1, B=2, etc.
        """
        cell_ref = cell_ref.upper().strip()
        
        # Separate letters and numbers
        col_str = ""
        row_str = ""
        
        for char in cell_ref:
            if char.isalpha():
                col_str += char
            elif char.isdigit():
                row_str += char
        
        # Convert column letters to number (A=1, B=2, ..., Z=26, AA=27, etc.)
        col_num = 0
        for char in col_str:
            col_num = col_num * 26 + (ord(char) - ord('A') + 1)
        
        row_num = int(row_str) if row_str else 1
        
        return col_num, row_num
    
    def disconnect_app(self) -> bool:
        """
        Disconnect from Excel, closing all tracked workbooks.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Close all tracked workbooks
            for workbook_id, workbook_info in list(self.workbooks.items()):
                try:
                    workbook = workbook_info['workbook']
                    if workbook:
                        self.close_workbook(workbook, save=False)
                except:
                    pass
            
            self.workbooks.clear()
            
            # Re-enable Excel properties before disconnecting
            if self.app:
                try:
                    self.set_property("DisplayAlerts", True)
                    self.set_property("ScreenUpdating", True)
                except:
                    pass
            
            # Call parent disconnect
            return super().disconnect_app()
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from Excel: {e}")
            return False
    
    def get_workbook_count(self) -> int:
        """
        Get the number of currently tracked workbooks.
        
        Returns:
            int: Number of tracked workbooks
        """
        return len(self.workbooks)
    
    def list_workbooks(self) -> Dict[str, str]:
        """
        Get a list of currently tracked workbooks.
        
        Returns:
            Dict: Dictionary mapping workbook IDs to file paths
        """
        return {
            str(wb_id): info.get('file_path', 'Unsaved')
            for wb_id, info in self.workbooks.items()
        }


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    if PANDAS_AVAILABLE:
        # Test with pandas DataFrame
        df = pd.DataFrame({
            'Symbol': ['AAPL', 'GOOGL', 'MSFT'],
            'Price': [150.0, 2500.0, 300.0],
            'Volume': [1000000, 500000, 750000]
        })
        
        with ExcelManager(visible=True) as excel:
            if excel.is_connected:
                # Create workbook and write data
                workbook = excel.create_workbook()
                if workbook:
                    sheet = excel.get_sheet("Sheet1", workbook)
                    if sheet:
                        success = excel.write_dataframe_to_sheet(sheet, df)
                        if success:
                            print("DataFrame written successfully")
                            
                            # Read back some data
                            values = excel.get_range_values(sheet, "A1", "C4")
                            print(f"Range values: {values}")
                            
                            # Save workbook
                            excel.save_workbook(workbook, "test_data.xlsx")
                            print("Workbook saved")
    else:
        print("pandas not available for DataFrame operations")
        
        # Test basic Excel operations without pandas
        with ExcelManager() as excel:
            if excel.is_connected:
                workbook = excel.create_workbook()
                print(f"Created workbook: {workbook}")
                
                sheet = excel.get_sheet("Sheet1", workbook)
                print(f"Got sheet: {sheet}")
    
    print("Excel Manager test completed")