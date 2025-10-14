import pandas as pd
from ..base_factor_creator import BaseFactorCreator

class MomentumFactor(BaseFactorCreator):
    def compute(self, input_data: pd.Series, existing_factors=None, lookback: int = 20, **_):
        if input_data is None:
            raise ValueError("input_data (price series) is required for momentum")
        return input_data / input_data.shift(lookback) - 1
