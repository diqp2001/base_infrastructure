# ReportingService

## Overview

The `ReportingService` provides comprehensive analytics, reporting, and visualization capabilities for data analysis and machine learning model evaluation. It serves as a centralized hub for generating performance metrics, statistical reports, and interactive visualizations with support for multiple export formats.

## Responsibilities

### Analytics and Metrics
- **Classification Metrics**: Comprehensive classification performance evaluation (F1, precision, recall, accuracy)
- **Regression Metrics**: Regression model evaluation (MSE, RMSE, MAE, R², residual analysis)
- **Descriptive Statistics**: Statistical summaries, correlation analysis, and data profiling
- **Data Quality Assessment**: Missing value analysis, data type validation, and quality scoring

### Visualization and Plotting
- **Statistical Plots**: Histograms, line plots, correlation heatmaps, and distribution analysis
- **Model Evaluation Plots**: Confusion matrices, actual vs predicted scatter plots, residual plots
- **Base64 Encoding**: Convert plots to base64 for web integration and API responses
- **Export Options**: Save plots to files or return as encoded strings for web display

### Report Generation and Export
- **Model Performance Reports**: Comprehensive model evaluation reports with metrics and visualizations
- **Data Quality Reports**: Detailed data profiling with column-level analysis
- **Report Storage**: In-memory report storage with retrieval capabilities
- **Multi-format Export**: Export reports as JSON, CSV, or formatted text files

## Architecture

### Service Design
```python
class ReportingService:
    def __init__(self, data: pd.DataFrame = None):
        self.data = data
        self.reports = {}  # Store generated reports
```

### Flexible Data Handling
- **Optional Data Initialization**: Service can be initialized with or without data
- **Dynamic Data Assignment**: Set or update data at runtime for different analyses
- **Data Validation**: Type checking and validation for all data inputs
- **Memory Management**: Efficient handling of large datasets with streaming operations

## Key Features

### 1. Machine Learning Model Evaluation
```python
# Initialize service
service = ReportingService()

# Generate comprehensive model report
report = service.generate_model_report(
    model_name="RandomForest_v1",
    y_true=test_labels,
    y_pred=predictions,
    task_type="classification",
    labels=["Class_A", "Class_B", "Class_C"]
)

# Access metrics
print(f"Accuracy: {report['accuracy']:.3f}")
print(f"F1 Score: {report['f1_score']:.3f}")
```

### 2. Data Quality Assessment
```python
# Set data for analysis
service.set_data(dataframe)

# Generate data quality report
quality_report = service.generate_data_quality_report(
    columns=['price', 'volume', 'market_cap']
)

# Analyze results
for column, analysis in quality_report['column_analysis'].items():
    print(f"{column}: {analysis['null_percentage']:.1f}% missing")
```

### 3. Statistical Analysis and Visualization
```python
# Generate descriptive statistics
stats = service.generate_descriptive_stats(['price', 'volume'])

# Create visualizations
histogram = service.plot_histogram('price', bins=20, title='Price Distribution')
heatmap = service.plot_correlation_heatmap(['price', 'volume', 'returns'])
evolution = service.plot_line_evolution(['price', 'volume'], title='Price & Volume Evolution')
```

### 4. Classification Model Analysis
```python
# Calculate detailed classification metrics
metrics = service.calculate_classification_metrics(
    y_true=actual_labels,
    y_pred=predicted_labels,
    labels=['Buy', 'Hold', 'Sell']
)

# Generate confusion matrix visualization
confusion_plot = service.plot_confusion_matrix(
    y_true=actual_labels,
    y_pred=predicted_labels,
    labels=['Buy', 'Hold', 'Sell'],
    title='Trading Signal Prediction Results'
)
```

## Usage Patterns

### Model Performance Monitoring
```python
class ModelMonitor:
    def __init__(self):
        self.reporting_service = ReportingService()
    
    def evaluate_model(self, model, X_test, y_test):
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Generate comprehensive report
        report = self.reporting_service.generate_model_report(
            model_name=f"{model.__class__.__name__}_v{datetime.now().strftime('%Y%m%d')}",
            y_true=y_test,
            y_pred=y_pred,
            task_type="classification"
        )
        
        # Export report
        self.reporting_service.export_report(
            report, 
            f"model_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        return report
```

### Data Pipeline Quality Control
```python
class DataQualityMonitor:
    def __init__(self):
        self.reporting_service = ReportingService()
    
    def monitor_data_pipeline(self, data_batches):
        quality_reports = []
        
        for batch_name, batch_data in data_batches.items():
            self.reporting_service.set_data(batch_data)
            
            # Generate quality report
            quality_report = self.reporting_service.generate_data_quality_report()
            quality_report['batch_name'] = batch_name
            quality_reports.append(quality_report)
            
            # Check for quality issues
            self._check_quality_thresholds(quality_report)
        
        return quality_reports
    
    def _check_quality_thresholds(self, report):
        for column, analysis in report['column_analysis'].items():
            if analysis['null_percentage'] > 10:  # More than 10% missing
                print(f"WARNING: High missing values in {column}: {analysis['null_percentage']:.1f}%")
```

### Financial Analytics Dashboard
```python
class FinancialReportGenerator:
    def __init__(self):
        self.reporting_service = ReportingService()
    
    def generate_portfolio_report(self, portfolio_data):
        self.reporting_service.set_data(portfolio_data)
        
        # Generate performance visualizations
        price_evolution = self.reporting_service.plot_line_evolution(
            ['portfolio_value', 'benchmark'], 
            title='Portfolio vs Benchmark Performance'
        )
        
        correlation_heatmap = self.reporting_service.plot_correlation_heatmap(
            ['returns', 'volatility', 'sharpe_ratio'],
            title='Risk-Return Correlation Analysis'
        )
        
        # Generate comprehensive statistics
        stats = self.reporting_service.generate_descriptive_stats()
        
        return {
            'visualizations': {
                'performance': price_evolution,
                'correlations': correlation_heatmap
            },
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        }
```

## Metrics and Analysis

### Classification Metrics
- **Accuracy**: Overall correctness of predictions
- **F1 Score**: Harmonic mean of precision and recall (weighted and macro averages)
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **Per-class Metrics**: Individual metrics for each class label
- **Confusion Matrix**: Detailed breakdown of prediction accuracy by class

### Regression Metrics
- **MSE**: Mean Squared Error for prediction accuracy
- **RMSE**: Root Mean Squared Error (same units as target)
- **MAE**: Mean Absolute Error (robust to outliers)
- **R² Score**: Coefficient of determination (explained variance)
- **Residual Analysis**: Mean and standard deviation of prediction residuals

### Data Quality Metrics
- **Completeness**: Missing value analysis by column
- **Uniqueness**: Cardinality and duplicate detection
- **Data Types**: Type validation and conversion recommendations
- **Statistical Properties**: Distribution analysis, outlier detection
- **Memory Usage**: Storage requirements and optimization opportunities

## Visualization Capabilities

### Statistical Visualizations
```python
# Distribution analysis
histogram = service.plot_histogram('column_name', bins=30)

# Time series analysis  
evolution = service.plot_line_evolution(['col1', 'col2'], title='Trend Analysis')

# Correlation analysis
heatmap = service.plot_correlation_heatmap(['numeric_cols'])
```

### Model Evaluation Visualizations
```python
# Classification results
confusion_matrix = service.plot_confusion_matrix(y_true, y_pred, labels)

# Regression results (automatically generated in model reports)
actual_vs_predicted = service.generate_model_report(..., task_type="regression")
```

### Output Formats
- **Base64 Encoding**: For web applications and API responses
- **File Export**: Save plots as PNG files with high DPI (300)
- **In-memory Streaming**: Efficient memory usage with BytesIO buffers

## Report Storage and Management

### Report Storage
```python
# Reports are automatically stored with timestamp keys
report = service.generate_model_report(...)
# Stored as: "ModelName_YYYYMMDD_HHMMSS"

# Retrieve stored reports
report_keys = service.get_stored_reports()
specific_report = service.get_report(report_keys[0])
```

### Export Capabilities
```python
# Export to different formats
service.export_report(report, 'report.json', format_type='json')
service.export_report(report, 'report.csv', format_type='csv')  
service.export_report(report, 'report.txt', format_type='txt')
```

## Performance Considerations

### Memory Management
- **Lazy Loading**: Plots generated on-demand to minimize memory usage
- **Buffer Management**: Proper cleanup of plot buffers after encoding
- **Data Copying**: Minimal data copying during analysis operations
- **Large Dataset Support**: Efficient processing of large DataFrames

### Processing Efficiency
- **Vectorized Operations**: Leverage pandas/numpy vectorized computations
- **Matplotlib Optimization**: Proper figure closing to prevent memory leaks
- **Selective Analysis**: Option to analyze only specified columns
- **Batch Processing**: Support for processing multiple datasets sequentially

### Plot Quality and Performance
- **High DPI Output**: 300 DPI for publication-quality visualizations
- **Optimized Rendering**: Efficient matplotlib/seaborn configuration
- **Style Consistency**: Standardized styling across all visualizations
- **Resource Cleanup**: Automatic figure and buffer cleanup

## Dependencies

### Core Dependencies
```python
import pandas as pd
import numpy as np
from sklearn.metrics import *  # Classification and regression metrics
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
import io
import base64
from datetime import datetime
```

### External Libraries
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing and array operations
- **scikit-learn**: Machine learning metrics and evaluation
- **matplotlib**: Static plotting and visualization
- **seaborn**: Statistical data visualization
- **base64**: Plot encoding for web integration

## Configuration and Customization

### Plot Styling
- **Figure Sizes**: Customizable plot dimensions for different use cases
- **Color Schemes**: Seaborn color palettes and matplotlib colormaps
- **DPI Settings**: High-resolution output for professional presentations
- **Style Themes**: Consistent styling across all visualizations

### Metric Calculation
- **Averaging Methods**: Support for macro, micro, and weighted averaging
- **Missing Value Handling**: Configurable strategies for incomplete data
- **Threshold Settings**: Customizable thresholds for quality assessment
- **Precision Control**: Floating-point precision settings for numerical stability

## Testing Strategy

### Unit Testing
```python
def test_classification_metrics():
    service = ReportingService()
    y_true = [0, 1, 0, 1, 1]
    y_pred = [0, 1, 1, 1, 0]
    
    metrics = service.calculate_classification_metrics(y_true, y_pred)
    assert 'accuracy' in metrics
    assert 'f1_score' in metrics
    assert 0 <= metrics['accuracy'] <= 1
```

### Integration Testing
```python
def test_report_generation():
    data = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    service = ReportingService(data)
    
    quality_report = service.generate_data_quality_report()
    assert 'total_rows' in quality_report
    assert quality_report['total_rows'] == 3
```

### Performance Testing
- **Large Dataset Processing**: Test with DataFrames of various sizes
- **Memory Usage Monitoring**: Track memory consumption during analysis
- **Plot Generation Speed**: Benchmark visualization creation times
- **Export Performance**: Test report export with different formats

## Best Practices

### Usage Guidelines
1. **Initialize with appropriate data** - Set data early or pass during initialization
2. **Use consistent metric calculation** - Apply same averaging methods across comparisons
3. **Store important reports** - Leverage built-in storage for historical comparison
4. **Export regularly** - Save reports for auditing and compliance purposes
5. **Validate inputs** - Check data quality before generating reports

### Performance Optimization
1. **Minimize data copying** - Use column selection for large DataFrames
2. **Close plot figures** - Prevent memory leaks in long-running applications
3. **Batch similar operations** - Group related analyses together
4. **Cache expensive calculations** - Store intermediate results when possible
5. **Use appropriate plot sizes** - Balance quality and performance

### Quality Assurance
1. **Validate metric calculations** - Cross-check important metrics manually
2. **Test with edge cases** - Verify behavior with empty data, NaN values, etc.
3. **Monitor report consistency** - Ensure reproducible results across runs
4. **Document analysis assumptions** - Record data preprocessing and filtering decisions
5. **Version control reports** - Track report evolution and model improvements