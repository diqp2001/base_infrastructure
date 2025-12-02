
"""
SQL Server specific utilities and helper functions
"""
from sqlalchemy import create_engine, text
from .settings import get_database_url


def get_sql_server_engine():
    """
    Create and return a SQL Server engine using the configured connection string.
    
    Returns:
        sqlalchemy.engine.Engine: Configured SQL Server engine
    """
    connection_string = get_database_url('sql_server')
    return create_engine(connection_string)


def test_sql_server_connection():
    """
    Test SQL Server connection and return basic information.
    
    Returns:
        dict: Connection information including version and status
    """
    try:
        engine = get_sql_server_engine()
        with engine.connect() as connection:
            # Get SQL Server version
            version_result = connection.execute(text("SELECT @@VERSION as version"))
            version = version_result.fetchone().version
            
            # Get current database
            db_result = connection.execute(text("SELECT DB_NAME() as current_database"))
            current_db = db_result.fetchone().current_database
            
            # Get current time
            time_result = connection.execute(text("SELECT GETDATE() as current_time"))
            current_time = time_result.fetchone().current_time
            
            return {
                'status': 'success',
                'version': version,
                'current_database': current_db,
                'current_time': current_time,
                'message': 'Connection successful'
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


def optimize_sql_server_query(query):
    """
    Perform SQL Server-specific query optimizations.
    
    Args:
        query (str): SQL query to optimize
        
    Returns:
        str: Optimized SQL query
    """
    # Add SQL Server specific optimizations here
    # For now, return the query as-is
    return query


def create_database_if_not_exists(database_name):
    """
    Create a database if it doesn't exist.
    
    Args:
        database_name (str): Name of the database to create
        
    Returns:
        bool: True if created or already exists, False on error
    """
    try:
        engine = get_sql_server_engine()
        with engine.connect() as connection:
            # Check if database exists
            result = connection.execute(
                text("SELECT name FROM sys.databases WHERE name = :db_name"), 
                {"db_name": database_name}
            )
            
            if result.fetchone() is None:
                # Database doesn't exist, create it
                connection.execute(text(f"CREATE DATABASE [{database_name}]"))
                connection.commit()
                return True
            else:
                # Database already exists
                return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False