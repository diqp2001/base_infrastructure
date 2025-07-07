#!/usr/bin/env python3
"""
Windows COM Managers Package

This package provides Windows COM (Component Object Model) management capabilities
for interacting with Windows applications like Microsoft Office.

Main Components:
    - WindowsCOMManager: Base class for COM application management
    - ExcelManager: Specialized manager for Microsoft Excel operations

Usage:
    from application.managers.windows_com_managers import WindowsCOMManager, ExcelManager
    
    # Basic COM operations
    with WindowsCOMManager() as com:
        com.connect_to_app("Excel.Application")
        result = com.execute_method("Quit")
    
    # Excel-specific operations
    with ExcelManager() as excel:
        workbook = excel.create_workbook("data.xlsx")
        sheet = excel.get_sheet("Sheet1", workbook)
        excel.write_dataframe_to_sheet(sheet, df)
        excel.save_workbook(workbook, "data.xlsx")
"""

from .windows_com_manager import (
    WindowsCOMManager,
    COMConnectionError,
    COMMethodError, 
    COMPropertyError,
    is_win32com_available,
    get_available_com_applications
)

from .excel_manager import ExcelManager

__all__ = [
    'WindowsCOMManager',
    'ExcelManager',
    'COMConnectionError',
    'COMMethodError',
    'COMPropertyError',
    'is_win32com_available',
    'get_available_com_applications'
]

__version__ = '1.0.0'
__author__ = 'Claude Code'
__description__ = 'Windows COM management utilities for Python applications'