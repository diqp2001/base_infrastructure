"""
Backtest dataset domain model.

Defines the schema for input datasets used in backtests including OHLCV data,
fundamental data, alternative data sources, and feature engineering pipelines.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4
import pandas as pd


@dataclass
class DataSource:
    """Metadata for a data source used in backtests."""
    
    source_id: str
    name: str
    provider: str
    description: str = ""
    
    # Data characteristics
    asset_class: str = "equity"  # equity, fixed_income, commodity, fx, crypto
    data_type: str = "price"     # price, fundamental, alternative, macro
    frequency: str = "daily"     # tick, minute, hourly, daily, weekly, monthly
    
    # Coverage
    symbols: List[str] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Quality metrics
    completeness_pct: float = 100.0  # Percentage of expected data points available
    accuracy_score: float = 1.0      # Data accuracy score (0-1)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Cost and licensing
    cost_per_symbol: Optional[Decimal] = None
    license_type: str = "free"  # free, subscription, per_use
    
    def __post_init__(self):
        if self.source_id is None:
            self.source_id = str(uuid4())


@dataclass
class DataField:
    """Definition of a data field/column within a dataset."""
    
    field_name: str
    field_type: str  # numeric, categorical, datetime, text
    description: str = ""
    
    # Validation rules
    required: bool = True
    min_value: Optional[Union[float, int]] = None
    max_value: Optional[Union[float, int]] = None
    valid_values: Optional[List[str]] = None  # For categorical fields
    
    # Data quality
    null_count: int = 0
    null_percentage: float = 0.0
    unique_count: Optional[int] = None
    
    # Statistics (for numeric fields)
    mean: Optional[float] = None
    std: Optional[float] = None
    min_observed: Optional[float] = None
    max_observed: Optional[float] = None
    
    # Transformation info
    transformations_applied: List[str] = field(default_factory=list)
    derived_from: Optional[str] = None  # Source field if this is derived


@dataclass
class DataQualityReport:
    """Data quality assessment for a dataset."""
    
    report_id: str
    dataset_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Overall quality metrics
    overall_score: float  # 0-1 quality score
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    
    # Issue detection
    missing_data_issues: List[Dict[str, Any]] = field(default_factory=list)
    outlier_issues: List[Dict[str, Any]] = field(default_factory=list)
    consistency_issues: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.report_id is None:
            self.report_id = str(uuid4())


@dataclass  
class FeatureEngineeringPipeline:
    """Pipeline for feature engineering and data transformations."""
    
    pipeline_id: str
    name: str
    description: str = ""
    
    # Pipeline steps
    steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Input/output specification
    input_fields: List[str] = field(default_factory=list)
    output_fields: List[str] = field(default_factory=list)
    
    # Configuration
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    execution_time_seconds: float = 0.0
    
    def __post_init__(self):
        if self.pipeline_id is None:
            self.pipeline_id = str(uuid4())
    
    def add_step(self, step_type: str, config: Dict[str, Any]):
        """Add a transformation step to the pipeline."""
        step = {
            'step_id': str(uuid4()),
            'type': step_type,
            'config': config,
            'order': len(self.steps)
        }
        self.steps.append(step)


@dataclass
class BacktestDataset:
    """
    Complete dataset definition for a backtest including raw data,
    transformations, and quality metrics.
    """
    
    # Identifiers
    dataset_id: str
    name: str
    version: str = "1.0"
    description: str = ""
    
    # Data sources
    primary_source: DataSource = None
    auxiliary_sources: List[DataSource] = field(default_factory=list)
    
    # Schema definition
    fields: List[DataField] = field(default_factory=list)
    
    # Time range and frequency
    start_date: date = None
    end_date: date = None
    frequency: str = "daily"
    timezone: str = "UTC"
    
    # Universe definition
    symbols: List[str] = field(default_factory=list)
    universe_filter: Dict[str, Any] = field(default_factory=dict)
    
    # Feature engineering
    feature_pipeline: Optional[FeatureEngineeringPipeline] = None
    features_generated: List[str] = field(default_factory=list)
    
    # Data quality
    quality_report: Optional[DataQualityReport] = None
    
    # Benchmark and factors
    benchmark_symbol: Optional[str] = "SPY"
    risk_free_rate_source: Optional[str] = "FRED_3M_TREASURY"
    factor_sources: Dict[str, str] = field(default_factory=dict)  # factor_name -> source
    
    # Storage and caching
    storage_location: str = ""
    cache_enabled: bool = True
    compression: str = "parquet"  # parquet, hdf5, csv
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    last_updated: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Statistics
    total_data_points: int = 0
    memory_usage_mb: float = 0.0
    
    def __post_init__(self):
        """Initialize default values."""
        if self.dataset_id is None:
            self.dataset_id = str(uuid4())
    
    def add_field(self, field: DataField):
        """Add a field definition to the dataset."""
        self.fields.append(field)
    
    def get_field(self, field_name: str) -> Optional[DataField]:
        """Get field definition by name."""
        for field in self.fields:
            if field.field_name == field_name:
                return field
        return None
    
    def get_required_fields(self) -> List[DataField]:
        """Get all required fields."""
        return [field for field in self.fields if field.required]
    
    def get_numeric_fields(self) -> List[DataField]:
        """Get all numeric fields."""
        return [field for field in self.fields if field.field_type == "numeric"]
    
    def calculate_data_points(self) -> int:
        """Calculate total expected data points."""
        if not self.start_date or not self.end_date:
            return 0
        
        # Simple calculation - would be more sophisticated in practice
        days = (self.end_date - self.start_date).days
        symbols_count = len(self.symbols)
        fields_count = len(self.fields)
        
        if self.frequency == "daily":
            trading_days = int(days * 0.7)  # Rough approximation
            return trading_days * symbols_count * fields_count
        
        return days * symbols_count * fields_count
    
    def validate(self) -> List[str]:
        """Validate dataset configuration."""
        errors = []
        
        if not self.name:
            errors.append("Dataset name is required")
        
        if not self.symbols:
            errors.append("At least one symbol must be specified")
        
        if not self.fields:
            errors.append("At least one field must be defined")
        
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors.append("start_date must be before end_date")
        
        # Check for duplicate field names
        field_names = [field.field_name for field in self.fields]
        if len(field_names) != len(set(field_names)):
            errors.append("Duplicate field names detected")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if dataset configuration is valid."""
        return len(self.validate()) == 0
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary."""
        return {
            'dataset_id': self.dataset_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'frequency': self.frequency,
            'symbols_count': len(self.symbols),
            'fields_count': len(self.fields),
            'features_count': len(self.features_generated),
            'total_data_points': self.total_data_points,
            'memory_usage_mb': self.memory_usage_mb,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'tags': self.tags
        }


@dataclass
class DatasetVersion:
    """Version tracking for datasets with change history."""
    
    version_id: str
    dataset_id: str
    version: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    
    # Change tracking
    changes_from_previous: List[str] = field(default_factory=list)
    parent_version: Optional[str] = None
    
    # Validation results
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    # Performance impact
    performance_impact: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.version_id is None:
            self.version_id = str(uuid4())


@dataclass
class DatasetCatalog:
    """Catalog of available datasets for backtesting."""
    
    catalog_id: str
    name: str = "Default Catalog"
    
    # Datasets
    datasets: List[BacktestDataset] = field(default_factory=list)
    
    # Organization
    categories: Dict[str, List[str]] = field(default_factory=dict)  # category -> dataset_ids
    tags: Dict[str, List[str]] = field(default_factory=dict)       # tag -> dataset_ids
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if self.catalog_id is None:
            self.catalog_id = str(uuid4())
    
    def add_dataset(self, dataset: BacktestDataset):
        """Add a dataset to the catalog."""
        self.datasets.append(dataset)
        self.last_updated = datetime.utcnow()
    
    def find_datasets_by_tag(self, tag: str) -> List[BacktestDataset]:
        """Find datasets by tag."""
        if tag not in self.tags:
            return []
        
        dataset_ids = self.tags[tag]
        return [ds for ds in self.datasets if ds.dataset_id in dataset_ids]
    
    def find_datasets_by_symbol(self, symbol: str) -> List[BacktestDataset]:
        """Find datasets containing a specific symbol."""
        return [ds for ds in self.datasets if symbol in ds.symbols]