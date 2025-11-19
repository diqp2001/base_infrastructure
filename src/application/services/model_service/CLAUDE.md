# ModelService

## Overview

The `ModelService` provides comprehensive machine learning model lifecycle management capabilities, including training, evaluation, persistence, and deployment support. It serves as a centralized hub for managing ML models with integrated database tracking, file system persistence, and performance evaluation across different model types and frameworks.

## Responsibilities

### Model Training and Validation
- **Model Training**: Train models with configurable parameters and automatic validation splitting
- **Cross-Validation**: Perform k-fold cross-validation with customizable scoring metrics
- **Hyperparameter Management**: Handle model parameters and configuration tracking
- **Training Monitoring**: Track training progress and performance metrics

### Model Evaluation and Comparison
- **Performance Evaluation**: Comprehensive evaluation for both classification and regression tasks
- **Model Comparison**: Side-by-side performance comparison of multiple models
- **Metric Calculation**: Automatic calculation of relevant metrics based on task type
- **Feature Importance**: Extract and analyze feature importance from trained models

### Model Persistence and Deployment
- **Model Serialization**: Save models using pickle or joblib formats
- **Metadata Management**: Track model metadata in database with full versioning
- **Model Loading**: Load and restore previously trained models with full context
- **Model Registry**: Centralized registry of all trained models with search capabilities

## Architecture

### Service Design
```python
class ModelService:
    def __init__(self, db_type: str = 'sqlite', models_directory: str = "./models"):
        self.database_service = DatabaseService(db_type)
        self.models_directory = models_directory
        self.current_model = None
        self.model_metadata = {}
```

### Persistence Strategy
- **Dual Storage**: Models stored as files (pickle/joblib) with metadata in database
- **Version Control**: Automatic model versioning with unique identifiers
- **Metadata Tracking**: Comprehensive tracking of training parameters and performance
- **File System Organization**: Organized file structure for model storage and retrieval

## Key Features

### 1. Model Training with Validation
```python
# Initialize service
service = ModelService(db_type='postgresql', models_directory='./trained_models')

# Train model with automatic validation
from sklearn.ensemble import RandomForestClassifier

results = service.train_model(
    model_class=RandomForestClassifier,
    X=training_features,
    y=training_labels,
    model_id="rf_stock_predictor_v1",
    validation_split=0.2,
    n_estimators=100,
    max_depth=10,
    random_state=42
)

print(f"Validation Score: {results['validation_score']:.4f}")
```

### 2. Cross-Validation and Model Selection
```python
# Perform cross-validation
cv_results = service.cross_validate_model(
    model_class=RandomForestClassifier,
    X=features,
    y=labels,
    cv_folds=5,
    scoring='accuracy',
    n_estimators=100,
    max_depth=10
)

print(f"CV Score: {cv_results['mean_score']:.4f} ± {cv_results['std_score']:.4f}")
```

### 3. Model Evaluation and Comparison
```python
# Evaluate single model
evaluation = service.evaluate_model(
    X_test=test_features,
    y_test=test_labels,
    model_id="rf_stock_predictor_v1",
    task_type="classification"
)

# Compare multiple models
comparison = service.compare_models(
    model_ids=["rf_model_v1", "svm_model_v1", "xgb_model_v1"],
    X_test=test_features,
    y_test=test_labels
)
print(comparison[['model_id', 'accuracy', 'f1_score']].sort_values('accuracy', ascending=False))
```

### 4. Model Persistence and Loading
```python
# Save trained model
service.save_model(model_id="production_model_v2", save_format="joblib")

# Load model for inference
service.load_model("production_model_v2")
predictions = service.predict(new_data)

# Get probability predictions
probabilities = service.predict_proba(new_data)
```

## Usage Patterns

### ML Pipeline with Model Management
```python
class MLPipeline:
    def __init__(self):
        self.model_service = ModelService(
            db_type='postgresql', 
            models_directory='/models/production'
        )
    
    def train_and_evaluate_models(self, X, y, model_configs):
        """Train multiple models and select the best one."""
        results = []
        
        for config in model_configs:
            # Train model
            result = self.model_service.train_model(
                model_class=config['model_class'],
                X=X, y=y,
                model_id=config['model_id'],
                **config['params']
            )
            
            # Cross-validate
            cv_result = self.model_service.cross_validate_model(
                model_class=config['model_class'],
                X=X, y=y,
                cv_folds=5,
                **config['params']
            )
            
            result['cv_score'] = cv_result['mean_score']
            result['cv_std'] = cv_result['std_score']
            results.append(result)
            
            # Save promising models
            if result['validation_score'] > 0.85:
                self.model_service.save_model(config['model_id'])
        
        return results
    
    def deploy_best_model(self, model_comparison_results):
        """Deploy the best performing model."""
        best_model = max(model_comparison_results, key=lambda x: x['validation_score'])
        
        # Load best model
        self.model_service.load_model(best_model['model_id'])
        
        # Mark as production model
        self.model_service._update_model_metadata(
            best_model['model_id'], 
            {'status': 'production'}
        )
        
        return best_model['model_id']
```

### Automated Model Retraining
```python
class ModelRetrainingService:
    def __init__(self):
        self.model_service = ModelService()
    
    def retrain_models_on_new_data(self, new_X, new_y):
        """Retrain existing models with new data."""
        # Get all production models
        production_models = self.model_service.list_models(status='production')
        
        retraining_results = []
        
        for model_info in production_models:
            try:
                # Load original model metadata
                original_metadata = self.model_service._get_model_metadata(model_info['model_id'])
                
                # Retrain with same parameters
                new_model_id = f"{model_info['model_id']}_retrained_{datetime.now().strftime('%Y%m%d')}"
                
                result = self.model_service.train_model(
                    model_class=eval(original_metadata['model_class']),  # In practice, use a registry
                    X=new_X,
                    y=new_y,
                    model_id=new_model_id,
                    **original_metadata['model_params']
                )
                
                retraining_results.append({
                    'original_model': model_info['model_id'],
                    'new_model': new_model_id,
                    'performance_change': result['validation_score'] - model_info['validation_score']
                })
                
                # Save retrained model
                self.model_service.save_model(new_model_id)
                
            except Exception as e:
                print(f"Failed to retrain {model_info['model_id']}: {e}")
        
        return retraining_results
```

### Feature Engineering and Model Analysis
```python
class ModelAnalysisService:
    def __init__(self):
        self.model_service = ModelService()
    
    def analyze_feature_importance(self, model_id: str, feature_names: List[str]):
        """Analyze feature importance for a trained model."""
        # Load model
        self.model_service.load_model(model_id)
        
        # Get feature importance
        importance = self.model_service.get_feature_importance(feature_names)
        
        if importance:
            # Sort by importance
            sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            
            analysis = {
                'model_id': model_id,
                'top_features': sorted_features[:10],
                'feature_count': len(sorted_features),
                'importance_distribution': {
                    'max': max(importance.values()),
                    'min': min(importance.values()),
                    'mean': np.mean(list(importance.values())),
                    'std': np.std(list(importance.values()))
                }
            }
            
            return analysis
        
        return None
    
    def model_performance_over_time(self, model_pattern: str):
        """Track model performance evolution over time."""
        all_models = self.model_service.list_models()
        
        # Filter models matching pattern
        matching_models = [
            model for model in all_models 
            if model_pattern in model['model_id']
        ]
        
        # Sort by training date
        matching_models.sort(key=lambda x: x['training_date'])
        
        performance_timeline = []
        for model in matching_models:
            performance_timeline.append({
                'model_id': model['model_id'],
                'training_date': model['training_date'],
                'validation_score': model['validation_score'],
                'train_score': model['train_score']
            })
        
        return pd.DataFrame(performance_timeline)
```

## Model Evaluation Metrics

### Classification Metrics
- **Accuracy**: Overall correctness of predictions
- **Precision**: True positives / (True positives + False positives) - weighted average
- **Recall**: True positives / (True positives + False negatives) - weighted average
- **F1 Score**: Harmonic mean of precision and recall - weighted average
- **Classification Report**: Detailed per-class metrics with sklearn integration

### Regression Metrics
- **MSE**: Mean Squared Error for prediction accuracy
- **RMSE**: Root Mean Squared Error (interpretable units)
- **MAE**: Mean Absolute Error (robust to outliers)
- **R² Score**: Coefficient of determination (explained variance)

### Cross-Validation Metrics
- **CV Scores**: Individual fold scores for variance analysis
- **Mean Score**: Average performance across all folds
- **Standard Deviation**: Performance consistency across folds

## File System and Database Schema

### File Organization
```
models_directory/
├── model_id.pkl                    # Pickled model file
├── model_id.joblib                 # Joblib model file
├── model_id_metadata.json          # JSON metadata file
└── ...
```

### Database Schema
```sql
CREATE TABLE model_metadata (
    model_id TEXT PRIMARY KEY,
    model_class TEXT,                -- Model class name
    model_params TEXT,               -- JSON serialized parameters
    training_samples INTEGER,        -- Number of training samples
    validation_samples INTEGER,      -- Number of validation samples
    feature_count INTEGER,           -- Number of input features
    train_score REAL,               -- Training performance score
    validation_score REAL,          -- Validation performance score
    training_date TEXT,             -- ISO format training date
    status TEXT,                    -- 'trained', 'saved', 'production', 'archived'
    file_path TEXT                  -- Path to saved model file
);
```

## Supported Model Formats

### Serialization Formats
- **Pickle**: Python's native serialization (`.pkl` files)
- **Joblib**: Optimized for NumPy arrays (`.joblib` files)
- **Auto-detection**: Automatically detect format when loading models

### Supported Model Types
- **Scikit-learn Models**: All sklearn estimators with fit/predict interface
- **Tree-based Models**: Random Forest, Gradient Boosting, XGBoost (with feature importance)
- **Linear Models**: Logistic Regression, Linear Regression (with coefficient importance)
- **Custom Models**: Any model implementing sklearn-compatible interface

## Performance Considerations

### Memory Management
- **Model Caching**: Keep only current model in memory
- **Large Model Support**: Efficient serialization for large models
- **Metadata Separation**: Store metadata separately from model weights
- **Cleanup**: Automatic cleanup of temporary objects

### Database Optimization
- **Indexed Queries**: Database indexes on model_id and status columns
- **Batch Operations**: Efficient bulk metadata operations
- **JSON Storage**: Flexible parameter storage with JSON serialization
- **Connection Pooling**: Leverage DatabaseService connection management

### File System Efficiency
- **Organized Storage**: Clean directory structure for model files
- **Format Selection**: Choose optimal serialization format per use case
- **Space Management**: Tools for model cleanup and archiving
- **Concurrent Access**: Safe concurrent access to model files

## Dependencies

### Core Dependencies
```python
import os, pickle, joblib, json
from typing import Any, Dict, Type, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import *  # All evaluation metrics
```

### External Dependencies
- **DatabaseService**: Centralized database operations
- **scikit-learn**: ML algorithms and evaluation metrics
- **joblib**: Efficient model serialization
- **numpy/pandas**: Data manipulation and analysis

## Configuration and Customization

### Service Configuration
```python
# Development setup
service = ModelService(
    db_type='sqlite',
    models_directory='./models_dev'
)

# Production setup
service = ModelService(
    db_type='postgresql', 
    models_directory='/opt/ml_models'
)
```

### Model Storage Options
- **Local Storage**: File system storage for single-node deployments
- **Shared Storage**: Network storage for distributed environments
- **Cloud Storage**: Integration possibilities with S3, GCS, Azure Blob
- **Database Storage**: Option to store small models directly in database

## Testing Strategy

### Unit Testing
```python
def test_model_training():
    service = ModelService(db_type='sqlite', models_directory='./test_models')
    
    from sklearn.datasets import make_classification
    X, y = make_classification(n_samples=100, n_features=10)
    
    from sklearn.ensemble import RandomForestClassifier
    result = service.train_model(RandomForestClassifier, X, y, n_estimators=10)
    
    assert 'validation_score' in result
    assert result['model_class'] == 'RandomForestClassifier'
```

### Integration Testing
```python
def test_model_persistence():
    service = ModelService()
    
    # Train, save, and reload model
    X, y = make_classification(n_samples=100, n_features=5)
    service.train_model(RandomForestClassifier, X, y, model_id='test_model')
    
    # Save model
    assert service.save_model('test_model')
    
    # Clear current model and reload
    service.current_model = None
    assert service.load_model('test_model')
    
    # Test predictions
    predictions = service.predict(X[:10])
    assert len(predictions) == 10
```

### Performance Testing
- **Large Model Training**: Test with models requiring significant memory
- **Concurrent Access**: Test multiple simultaneous model operations
- **Database Performance**: Test metadata operations under load
- **File I/O Performance**: Test model serialization/deserialization speed

## Best Practices

### Model Development Workflow
1. **Systematic Experimentation**: Use consistent model_id naming conventions
2. **Cross-Validation**: Always validate models before deployment
3. **Metadata Tracking**: Record all relevant training parameters and metrics
4. **Version Control**: Use versioned model IDs for production deployments
5. **Performance Monitoring**: Track model performance over time

### Production Deployment
1. **Model Validation**: Thoroughly evaluate models before production deployment
2. **A/B Testing**: Deploy new models alongside existing ones for comparison
3. **Rollback Strategy**: Maintain ability to quickly revert to previous models
4. **Performance Monitoring**: Monitor production model performance continuously
5. **Retraining Schedule**: Establish regular retraining schedules for model freshness

### Resource Management
1. **Storage Cleanup**: Regularly archive or delete obsolete models
2. **Memory Management**: Clear unused models from memory
3. **Database Maintenance**: Regular database cleanup and optimization
4. **Monitoring**: Monitor disk usage and database size
5. **Backup Strategy**: Regular backup of critical production models