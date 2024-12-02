import dask.dataframe as dd
import numpy as np
import pandas as pd


class DaskTimeSeries:
    def __init__(self, data):
        """
        Initialize a DaskTimeSeries object from a Dask DataFrame, Pandas DataFrame, NumPy array, list, or dict.
        :param data: The input data to construct the Dask DataFrame.
        """
        if isinstance(data, dd.DataFrame):
            self.time_series = data
        elif isinstance(data, pd.DataFrame):
            self.time_series = dd.from_pandas(data, npartitions=1)
        elif isinstance(data, np.ndarray):
            self.time_series = dd.from_pandas(pd.DataFrame(data), npartitions=1)
        elif isinstance(data, list):
            self.time_series = dd.from_pandas(pd.DataFrame(data), npartitions=1)
        elif isinstance(data, dict):
            self.time_series = dd.from_pandas(pd.DataFrame(data), npartitions=1)
        else:
            raise TypeError("Input data must be a Dask DataFrame, Pandas DataFrame, NumPy array, list, or dict.")

    def to_numpy(self):
        """Convert the Dask DataFrame to a NumPy array (requires computation)."""
        return self.time_series.compute().to_numpy()

    def to_list(self):
        """Convert the Dask DataFrame to a list (requires computation)."""
        return self.time_series.compute().values.tolist()

    def to_dict(self):
        """Convert the Dask DataFrame to a dictionary (requires computation)."""
        return self.time_series.compute().to_dict()

    def add_column_with_lag(self, column_name, lag, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add a lagged column to the DataFrame, optionally grouped by specific columns.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if not new_column_name:
            new_column_name = f"{column_name}_lag_{lag}"

        if groupby_columns:
            self.time_series[new_column_name] = self.time_series.groupby(groupby_columns)[column_name].shift(lag)
        else:
            self.time_series[new_column_name] = self.time_series[column_name].shift(lag)

        if replace:
            self.time_series[column_name] = self.time_series[new_column_name]

    def add_quantile_column(self, column_name, quantiles, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add a quantile column to the DataFrame based on a specific column.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if not new_column_name:
            new_column_name = f"{column_name}_quantile_{quantiles}"

        def compute_quantile(x):
            return pd.qcut(x, quantiles, labels=False)

        if groupby_columns:
            self.time_series[new_column_name] = self.time_series.groupby(groupby_columns)[column_name].transform(compute_quantile)
        else:
            self.time_series[new_column_name] = self.time_series[column_name].map_partitions(compute_quantile)

        if replace:
            self.time_series[column_name] = self.time_series[new_column_name]

    def add_z_score_column(self, column_name, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add a column with z-scores for a specific column.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if not new_column_name:
            new_column_name = f"{column_name}_z_score"

        if groupby_columns:
            def compute_z_scores(x):
                return (x - x.mean()) / x.std()
            self.time_series[new_column_name] = self.time_series.groupby(groupby_columns)[column_name].transform(compute_z_scores)
        else:
            mean = self.time_series[column_name].mean()
            std = self.time_series[column_name].std()
            self.time_series[new_column_name] = (self.time_series[column_name] - mean) / std

        if replace:
            self.time_series[column_name] = self.time_series[new_column_name]

    def compute_ddf(self):
        """Compute the Dask DataFrame and return a Pandas DataFrame."""
        return self.time_series.compute()

    def __repr__(self):
        return f"DaskTimeSeries({len(self.time_series.columns)} columns)"
