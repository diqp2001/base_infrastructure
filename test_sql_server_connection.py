#!/usr/bin/env python3
"""
Test script for SQL Server connection using SQLAlchemy and pyodbc
"""

import sys
import os

# Add src to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.infrastructure.database.settings import get_database_url
    from sqlalchemy import create_engine, text
    
    print("Testing SQL Server connection...")
    
    # Get the SQL Server connection string
    connection_string = get_database_url('sql_server')
    print(f"Connection string: {connection_string}")
    
    # Create engine
    engine = create_engine(connection_string)
    
    # Test the connection
    with engine.connect() as connection:
        # Execute a simple query to test connection
        result = connection.execute(text("SELECT @@VERSION as version, GETDATE() as current_time"))
        row = result.fetchone()
        
        print("✅ Connection successful!")
        print(f"SQL Server Version: {row.version}")
        print(f"Current Time: {row.current_time}")
        
        # Test database selection
        result = connection.execute(text("SELECT DB_NAME() as current_database"))
        db_row = result.fetchone()
        print(f"Current Database: {db_row.current_database}")
        
    print("\n🎉 SQL Server connectivity test completed successfully!")
    
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
    print("\nTroubleshooting tips:")
    print("1. Ensure SQL Server is running")
    print("2. Check that ODBC Driver 17 for SQL Server is installed")
    print("3. Verify Windows Authentication is enabled")
    print("4. Make sure SQL Server Browser service is running if using named instances")
    sys.exit(1)