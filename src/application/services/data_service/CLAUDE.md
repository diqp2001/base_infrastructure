# DataService

## Overview

The `DataService` provides comprehensive data processing, transformation, and management capabilities for machine learning, risk management, and analytics workflows. It serves as a high-level abstraction over data operations, integrating with the `DatabaseService` for persistence and providing advanced ETL (Extract, Transform, Load) functionality.

## Responsibilities

### Data Lifecycle Management
- **Data Ingestion**: Load data from multiple sources (CSV, Excel, databases, APIs)
- **Data Storage**: Upload and persist data to database tables with conflict resolution
- **Data Retrieval**: Query data with filtering, pagination, and dynamic table operations
- **Data Export**: Export processed data to various formats and destinations

### Data Processing and Transformation
- **Data Cleaning**: Handle missing values with multiple strategies (drop, fill, interpolate)
- **Data Scaling**: Standardize and normalize data using configurable scalers
- **Data Transformation**: Apply custom transformations with function mapping
- **Data Aggregation**: Group and aggregate data with flexible aggregation functions

### Analytics and Integration
- **Data Merging**: Join datasets with various merge strategies
- **Data Quality**: Validate data integrity and provide quality metrics
- **Pipeline Support**: Chainable operations for complex data processing workflows
- **Performance Optimization**: Efficient processing for large datasets

## Architecture

### Service Integration
```python
class DataService:
    def __init__(self, db_type: str = 'sqlite', scaler: str = 'standard'):
        self.database_service = DatabaseService(db_type)
        self.scaler_instance = self._initialize_scaler(scaler)
```

### Configurable Processing
- **Scaler Types**: Support for StandardScaler and MinMaxScaler from scikit-learn
- **Database Types**: Integration with multiple database backends via DatabaseService
- **Processing Strategies**: Configurable strategies for data cleaning and transformation
- **Error Handling**: Graceful degradation with comprehensive error reporting

## Key Features

### 1. Data Ingestion and Storage
```python
# Load from file and optionally store in database
service = DataService()
df = service.load_from_csv('/path/to/data.csv', table_name='raw_data')

# Upload DataFrame to database
service.upload_data(processed_df, 'processed_data')

# Append new data to existing table
service.append_data(new_df, 'processed_data')
```

### 2. Data Querying and Retrieval
```python
# Execute raw SQL queries
results = service.query_data("SELECT * FROM users WHERE status = 'active'")

# Use config-based queries
results = service.query_config_data('get_active_users')

# Dynamic querying with filters
filtered_data = service.fetch_dataframe_with_filters(
    query_key='user_template',
    table_name='users',
    columns=['id', 'name', 'email'],
    filters={'status': ('=', 'active'), 'created_date': ('>', '2023-01-01')},
    top_n=1000
)
```

### 3. Data Cleaning and Processing
```python
# Clean data with various strategies
cleaned_df = service.clean_data(df, strategy='fillna_mean')

# Scale numeric columns
scaled_df = service.scale_data(df, columns=['price', 'volume', 'market_cap'])

# Apply custom transformations
transformations = {
    'price': lambda x: np.log(x + 1),
    'date': lambda x: pd.to_datetime(x)
}
transformed_df = service.transform_data(df, transformations)
```

### 4. Data Aggregation and Analysis
```python
# Aggregate data by groups
aggregated_df = service.aggregate_data(
    df, 
    group_by=['sector', 'date'],
    aggregations={'price': 'mean', 'volume': 'sum', 'returns': 'std'}
)

# Merge datasets
merged_df = service.merge_datasets(
    left=stock_data,
    right=fundamentals_data,
    on='ticker',
    how='left'
)
```

## Usage Patterns

### ETL Pipeline
```python
class ETLPipeline:
    def __init__(self):
        self.data_service = DataService(db_type='postgresql')
    
    def process_market_data(self, file_path: str):
        # Extract
        raw_data = self.data_service.load_from_csv(file_path)
        
        # Transform
        cleaned_data = self.data_service.clean_data(raw_data, strategy='fillna_mean')
        scaled_data = self.data_service.scale_data(cleaned_data, ['price', 'volume'])
        
        # Load
        self.data_service.upload_data(scaled_data, 'market_data_processed')
        return scaled_data
```

### Machine Learning Data Preparation
```python
def prepare_ml_data():
    service = DataService(scaler='standard')
    
    # Load and clean data
    features = service.fetch_dataframe_with_filters(
        query_key='feature_template',
        table_name='features',
        filters={'data_quality': ('=', 'good')}
    )
    
    # Scale features
    scaled_features = service.scale_data(features)
    
    # Store processed data
    service.upload_data(scaled_features, 'ml_features')
    return scaled_features
```

### Data Quality Monitoring
```python
def monitor_data_quality(table_name: str):
    service = DataService()
    
    # Get data with filters
    data = service.fetch_dataframe_with_filters(
        query_key='quality_check',
        table_name=table_name,
        filters={'last_updated': ('>=', datetime.now() - timedelta(days=1))}
    )
    
    # Analyze quality
    quality_report = {
        'row_count': len(data),
        'null_percentage': data.isnull().sum() / len(data),
        'duplicate_count': data.duplicated().sum()
    }
    
    return quality_report
```

## Data Processing Strategies

### Cleaning Strategies
- **`drop`**: Remove rows with missing values
- **`fillna_mean`**: Fill missing values with column means
- **`fillna_median`**: Fill missing values with column medians  
- **`fillna_mode`**: Fill missing values with column modes

### Scaling Options
- **`standard`**: StandardScaler (mean=0, std=1)
- **`minmax`**: MinMaxScaler (scale to [0,1] range)

### Merge Strategies
- **`inner`**: Keep only matching records from both datasets
- **`left`**: Keep all records from left dataset
- **`right`**: Keep all records from right dataset
- **`outer`**: Keep all records from both datasets

## Performance Considerations

### Memory Management
- **DataFrame Copying**: Operations create copies to preserve original data
- **Lazy Evaluation**: Use generators where possible for large datasets
- **Column Selection**: Process only required columns to reduce memory usage
- **Batch Processing**: Support for processing data in chunks

### Database Optimization
- **Connection Reuse**: Single DatabaseService instance per DataService
- **Query Optimization**: Use parameterized queries and proper indexing
- **Bulk Operations**: Efficient bulk insert and update operations
- **Transaction Management**: Proper transaction boundaries for data consistency

### Processing Efficiency
- **Vectorized Operations**: Leverage pandas vectorized operations
- **Parallel Processing**: Support for parallel processing where beneficial
- **Pipeline Optimization**: Chain operations to minimize intermediate copies
- **Error Recovery**: Graceful handling of processing errors

## Error Handling

### Comprehensive Exception Management
```python
def safe_operation(self, operation_func, *args, **kwargs):
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        self.logger.error(f"Operation failed: {e}")
        return self._get_safe_fallback()
```

### Error Categories
- **Database Errors**: Connection failures, query errors, transaction issues
- **Data Errors**: Invalid data formats, missing columns, type mismatches
- **Processing Errors**: Transformation failures, scaling issues, aggregation problems
- **I/O Errors**: File reading/writing errors, network issues

## Configuration

### Service Configuration
```python
# Basic configuration
service = DataService(
    db_type='postgresql',
    scaler='standard'
)

# Advanced configuration
service = DataService(
    db_type='postgresql', 
    scaler='minmax'
)
```

### Database Integration
```python
# Uses DatabaseService configuration
# Inherits all DatabaseService capabilities
# - Connection pooling
# - Transaction management
# - Multiple database support
```

## Dependencies

### Required Packages
```python
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from src.application.services.database_service import DatabaseService
```

### External Dependencies
- **pandas**: Core data manipulation and analysis
- **scikit-learn**: Data preprocessing and scaling
- **DatabaseService**: Database operations and persistence

## Testing Strategy

### Unit Testing
```python
def test_data_cleaning():
    service = DataService()
    dirty_df = pd.DataFrame({'A': [1, 2, None], 'B': [4, None, 6]})
    clean_df = service.clean_data(dirty_df, strategy='drop')
    assert len(clean_df) == 1  # Only one complete row
```

### Integration Testing
```python
def test_etl_pipeline():
    service = DataService('sqlite')
    
    # Test full ETL pipeline
    df = service.load_from_csv('test_data.csv', 'raw_table')
    cleaned = service.clean_data(df)
    scaled = service.scale_data(cleaned)
    service.upload_data(scaled, 'processed_table')
    
    # Verify data was processed correctly
    result = service.query_data("SELECT * FROM processed_table")
    assert len(result) > 0
```

### Performance Testing
- **Large Dataset Processing**: Test with datasets of various sizes
- **Memory Usage**: Monitor memory consumption during processing
- **Processing Speed**: Benchmark transformation and aggregation operations
- **Database Performance**: Test database operations under load

## Best Practices

### Data Processing Guidelines
1. **Always validate input data** before processing
2. **Use appropriate cleaning strategies** based on data characteristics
3. **Scale data consistently** across training and prediction datasets
4. **Document transformations** for reproducibility
5. **Monitor data quality** throughout the pipeline

### Performance Optimization
1. **Process only required columns** to reduce memory usage
2. **Use chunked processing** for very large datasets
3. **Cache frequently used transformations** 
4. **Optimize database queries** with proper indexing
5. **Monitor resource usage** during processing

### Error Handling
1. **Implement graceful degradation** for non-critical failures
2. **Log detailed error information** for debugging
3. **Provide meaningful error messages** to users
4. **Use try-catch blocks** around all external operations
5. **Validate data integrity** before and after transformations