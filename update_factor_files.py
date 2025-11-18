#!/usr/bin/env python3
"""
Script to update all factor model files to use the unified factor model.
"""

import os
import glob

# Define the factor types mapping
FACTOR_TYPES = [
    ('currency', 'Currency'),
    ('commodity', 'Commodity'),
    ('etf_share', 'ETFShare'),
    ('futures', 'Futures'),
    ('index', 'Index'),
    ('options', 'Options'),
    ('security', 'Security'),
    ('share', 'Share'),
]

# Template for the new file content
FILE_TEMPLATE = '''"""
SQLAlchemy ORM models for {display_name} factor entities.
DEPRECATED: Use unified factor model from factor_model.py instead.
This file exists for backward compatibility and imports from the unified model.
"""

# Import from the unified factor model
from src.infrastructure.models.factor.factor_model import (
    {class_name}Factor,
    FactorValue as {class_name}FactorValue  # Alias for backward compatibility
)
'''

def update_factor_file(factor_type, display_name):
    """Update a single factor file."""
    file_path = f"/home/runner/work/base_infrastructure/base_infrastructure/src/infrastructure/models/factor/finance/financial_assets/{factor_type}_factors.py"
    
    if os.path.exists(file_path):
        content = FILE_TEMPLATE.format(
            display_name=display_name,
            class_name=display_name.replace(' ', '')
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"Updated {file_path}")
    else:
        print(f"File not found: {file_path}")

if __name__ == "__main__":
    print("Updating factor model files...")
    
    for factor_type, display_name in FACTOR_TYPES:
        update_factor_file(factor_type, display_name)
    
    print("Factor file updates complete!")