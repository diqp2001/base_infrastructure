# DatabaseService

## Overview

The `DatabaseService` is a centralized database abstraction layer that provides unified access to database operations across the entire application. It serves as the single source of truth for database connectivity, session management, and data operations, supporting both local SQLite and external database configurations.

## Responsibilities

### Core Database Operations
- **Session Management**: Centralized SQLAlchemy session creation and lifecycle management
- **Connection Handling**: Support for both local SQLite and external database connections
- **Query Execution**: Safe execution of raw SQL queries with error handling and transaction management
- **Configuration Management**: Integration with config-based query system for reusable SQL operations

### Data Import/Export Operations
- **File to Database**: Import CSV and Excel files directly into database tables
- **Database to DataFrame**: Export query results to Pandas and Dask DataFrames
- **Bulk Operations**: Efficient bulk insert, update, and replace operations
- **Format Support**: Support for CSV, Excel, and various structured data formats

### Advanced Querying
- **Dynamic Queries**: Template-based queries with runtime parameter substitution
- **Filtered Queries**: Support for complex WHERE clauses with multiple conditions
- **Parameterized Queries**: Safe parameter binding to prevent SQL injection
- **Result Formatting**: Flexible result formatting (dict, DataFrame, raw results)

## Architecture

### Database Abstraction
```python
class DatabaseService:
    def __init__(self, db_type='sqlite'):
        self.db_type = db_type
        self.db = Database(self.db_type)
        self.session = self.db.SessionLocal
```

### Session Management Pattern
- **Local Database**: Creates SQLite database using Domain Database abstraction
- **External Database**: Configures engine and session for remote databases
- **Session Lifecycle**: Proper session cleanup and transaction management
- **Error Handling**: Automatic rollback on failures with proper cleanup

### Configuration Integration
- **Query Templates**: Integration with `config_data_source_manager.QUERIES`
- **Dynamic Parameters**: Runtime substitution of table names and parameters
- **Reusable Queries**: Centralized query definitions for consistency across application

## Key Features

### 1. Unified Database Access
```python
# Local SQLite database
service = DatabaseService('sqlite')

# External database
service = DatabaseService('postgresql')
service.set_ext_db()
```

### 2. Safe Query Execution
```python
# Execute raw SQL safely
service.execute_query("UPDATE users SET status = 'active' WHERE id = :user_id", 
                     params={'user_id': 123})

# Execute config-based queries
results = service.execute_config_query('get_active_users')
```

### 3. Data Import/Export
```python
# Import CSV to database
service.csv_to_db('/path/to/data.csv', 'user_data', if_exists='replace')

# Export to DataFrame
df = service.fetch_dataframe_with_dynamic_table(
    query_key='select_template',
    table_name='users',
    filters={'status': ('=', 'active')},
    top_n=1000
)
```

### 4. Big Data Support
```python
# Dask DataFrame for large datasets
dask_df = service.fetch_dask_dataframe_with_sql_query(
    query="SELECT * FROM large_table",
    index_col='id'
)
```

## Usage Patterns

### Entity Service Integration
```python
class FactorService:
    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.session = database_service.session
        self._init_repositories()
    
    def _init_repositories(self):
        self.factor_repository = FactorRepository(self.session)
```

### Transaction Management
```python
def bulk_operations(self):
    try:
        # Multiple operations in single transaction
        self.service.execute_query("INSERT INTO table1 ...")
        self.service.execute_query("UPDATE table2 ...")
        # Auto-commit on success
    except Exception:
        # Auto-rollback on failure
        pass
```

### Configuration-Driven Queries
```python
# Define in config_data_source_manager.py
QUERIES = {
    'get_factors_by_type': """
        SELECT * FROM {table_name} 
        WHERE factor_type = :factor_type
        ORDER BY created_date DESC
    """
}

# Use in service
results = service.execute_config_query('get_factors_by_type')
```

## Error Handling

### Exception Management
- **SQL Errors**: Automatic session rollback on SQL execution errors
- **Connection Errors**: Graceful handling of database connectivity issues
- **Configuration Errors**: Clear error messages for invalid configurations
- **Data Errors**: Validation and error reporting for data import/export operations

### Logging and Monitoring
- **Operation Logging**: Success/failure logging for all database operations
- **Performance Monitoring**: Query execution time tracking
- **Error Reporting**: Detailed error messages with context information
- **Connection Status**: Database connectivity health checks

## Configuration

### Database Types
```python
# Supported database types
db_types = ['sqlite', 'postgresql', 'mysql', 'mssql']
```

### Environment Variables
```bash
# External database configuration
DATABASE_URL=postgresql://user:pass@host:port/db
DB_TYPE=postgresql

# Local database configuration  
LOCAL_DB_PATH=/path/to/local.db
```

### Connection Parameters
```python
service = DatabaseService(
    db_type='postgresql',
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)
```

## Performance Considerations

### Connection Pooling
- **Session Reuse**: Single session per service instance
- **Connection Management**: Proper connection lifecycle management
- **Pool Configuration**: Configurable connection pooling parameters
- **Resource Cleanup**: Automatic cleanup of database resources

### Query Optimization
- **Parameterized Queries**: Prepared statements for better performance
- **Result Limiting**: Built-in support for query result limiting
- **Index Utilization**: Encourages proper use of database indexes
- **Batch Operations**: Support for bulk operations to reduce round trips

### Memory Management
- **Streaming Results**: Support for large result sets via streaming
- **Dask Integration**: Big data processing capabilities
- **DataFrame Chunking**: Efficient processing of large datasets
- **Memory Monitoring**: Resource usage tracking and optimization

## Dependencies

### Required Packages
```python
# Core dependencies
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
import pandas as pd
import dask.dataframe as dd

# Domain dependencies  
from domain.database import Database
from infrastructure.database.settings import get_database_url
```

### Infrastructure Dependencies
- **Domain Database**: Core database abstraction
- **Config Manager**: Query configuration management
- **Settings Module**: Database URL and connection configuration

## Testing Strategy

### Unit Testing
```python
def test_query_execution():
    service = DatabaseService('sqlite')
    result = service.execute_config_query('test_query')
    assert result is not None
```

### Integration Testing
```python
def test_database_integration():
    service = DatabaseService('sqlite')
    # Test actual database operations
    service.csv_to_db('test.csv', 'test_table')
    results = service.execute_query("SELECT * FROM test_table")
    assert len(results) > 0
```

### Performance Testing
- **Load Testing**: Verify performance under high query loads
- **Memory Testing**: Monitor memory usage with large datasets
- **Connection Testing**: Test connection pool behavior
- **Concurrency Testing**: Verify thread safety and concurrent access

## Best Practices

### Usage Guidelines
1. **Single Instance**: Use one DatabaseService instance per application context
2. **Session Management**: Let service manage session lifecycle
3. **Error Handling**: Always handle database exceptions appropriately
4. **Resource Cleanup**: Call `close_session()` when service is no longer needed

### Security Considerations
1. **Parameter Binding**: Always use parameterized queries to prevent SQL injection
2. **Connection Security**: Use secure connection strings for external databases
3. **Credential Management**: Store database credentials securely
4. **Access Control**: Implement appropriate database access controls

### Performance Optimization
1. **Query Efficiency**: Use appropriate indexes and query optimization
2. **Batch Operations**: Prefer bulk operations for multiple data modifications
3. **Connection Reuse**: Reuse database connections where possible
4. **Memory Management**: Use streaming for large result sets