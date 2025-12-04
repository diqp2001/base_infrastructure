"""
Data validation utilities for the test base project.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional


class DataValidators:
    """Validation utilities for data quality and consistency."""
    
    @staticmethod
    def validate_price_data(data: pd.DataFrame) -> Dict[str, Any]:
        """Validate price data quality."""
        validation_report = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        # Check for required columns
        required_cols = ['close_price', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        
        if missing_cols:
            validation_report['errors'].append(f"Missing required columns: {missing_cols}")
            validation_report['is_valid'] = False
        
        # Check for negative prices
        if 'close_price' in data.columns:
            negative_prices = (data['close_price'] <= 0).sum()
            if negative_prices > 0:
                validation_report['errors'].append(f"Found {negative_prices} non-positive prices")
                validation_report['is_valid'] = False
        
        # Check for missing values
        missing_pct = (data.isnull().sum() / len(data)) * 100
        high_missing = missing_pct[missing_pct > 10]
        
        if len(high_missing) > 0:
            validation_report['warnings'].append(f"High missing data: {high_missing.to_dict()}")
        
        # Calculate statistics
        validation_report['statistics'] = {
            'total_records': len(data),
            'missing_percentage': missing_pct.to_dict(),
            'date_range': (data.index.min(), data.index.max()) if len(data) > 0 else None
        }
        
        return validation_report
    
    @staticmethod
    def validate_factor_data(data: pd.DataFrame) -> Dict[str, Any]:
        """Validate factor data quality."""
        validation_report = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'factor_stats': {}
        }
        
        # Check for infinite or NaN values
        inf_values = np.isinf(data.select_dtypes(include=[np.number])).sum().sum()
        if inf_values > 0:
            validation_report['warnings'].append(f"Found {inf_values} infinite values")
        
        # Check factor distributions
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            stats = {
                'mean': data[col].mean(),
                'std': data[col].std(),
                'min': data[col].min(),
                'max': data[col].max(),
                'skewness': data[col].skew(),
                'kurtosis': data[col].kurtosis()
            }
            
            # Check for extreme values
            if abs(stats['skewness']) > 5:
                validation_report['warnings'].append(f"High skewness in {col}: {stats['skewness']:.2f}")
            
            if stats['kurtosis'] > 10:
                validation_report['warnings'].append(f"High kurtosis in {col}: {stats['kurtosis']:.2f}")
            
            validation_report['factor_stats'][col] = stats
        
        return validation_report