"""
ML-based signal generation for trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.spatiotemporal_model import HybridSpatiotemporalModel
from ..config import DEFAULT_CONFIG


class MLSignalGenerator:
    """Generates trading signals from ML models and factor data."""
    
    def __init__(self, trained_model: HybridSpatiotemporalModel):
        self.trained_model = trained_model
        self.config = DEFAULT_CONFIG
    
    def generate_trading_signals(self,
                               factor_data: pd.DataFrame,
                               confidence_threshold: float = 0.6) -> pd.DataFrame:
        """Generate trading signals from factor data."""
        return self.trained_model.generate_signals_from_factors(
            factor_data, model_type='ensemble', confidence_threshold=confidence_threshold
        )
    
    def get_signal_confidence(self, signals: pd.DataFrame) -> Dict[str, float]:
        """Extract signal confidence scores."""
        if 'confidence' in signals.columns:
            return signals['confidence'].to_dict()
        return {idx: 0.5 for idx in signals.index}  # Default confidence