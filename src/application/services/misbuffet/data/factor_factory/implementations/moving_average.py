import pandas as pd
from ..base_factor_creator import BaseFactorCreator

class MovingAverageFactor(BaseFactorCreator):
    def compute(self, input_data: pd.Series, existing_factors=None, window: int = 20, **_):
        if input_data is None:
            raise ValueError("input_data (price series) is required for moving average")
        return input_data.rolling(window=window).mean()
