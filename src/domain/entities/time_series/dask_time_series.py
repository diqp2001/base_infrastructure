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

    def add_quantile_column_index(self, column_name, num_quantiles, new_column_name=None, replace=False):
        """
        Add a quantile column to the DataFrame based on a specific column.

        Parameters:
            column_name (str): The name of the column for which quantiles are to be calculated.
            num_quantiles (int): The number of quantiles to compute.
            new_column_name (str, optional): The name of the new column. Defaults to a generated name.
            replace (bool, optional): If True, replace the original column with the quantile column. Defaults to False.


        """
        def compute_group_quantiles(partition, column_name, num_quantiles):
            """
            Compute quantiles within each group (e.g., each date) in a single partition.

            Parameters:
                partition (pd.DataFrame): A partition of the Dask DataFrame.
                column_name (str): The name of the column for which quantiles are to be calculated.
                num_quantiles (int): The number of quantiles to compute.

            Returns:
                pd.Series: Quantile ranks for the specified column within the partition.
            """
            if column_name not in partition.columns:
                raise KeyError(f"Column '{column_name}' not found in the partition.")
            
            return partition.groupby(partition.index)[column_name].transform(
                lambda x: pd.qcut(x, q=num_quantiles, labels=False, duplicates="drop")
            )
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if not new_column_name:
            new_column_name = f"{column_name}_quantile_{num_quantiles}"

        self.time_series[new_column_name] = self.time_series.map_partitions(
            compute_group_quantiles,
            column_name=column_name,
            num_quantiles=num_quantiles,
            meta=(new_column_name, "int"),  # Specify the new column's metadata
        )        

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
    
    def bring_in_memory_partition(self,partition_number):
        partition = self.time_series.get_partition(partition_number)
        pandas_partition = partition.compute()
        return pandas_partition
    
    def remove_column(self, column_name):
        """
        Remove a column from the Dask DataFrame.
        :param column_name: The name of the column to remove.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        self.time_series = self.time_series.drop(columns=[column_name])

    def duplicate_column(self, column_name, new_column_name):
        """
        Duplicate a column in the Dask DataFrame with a new name.
        :param column_name: The name of the column to duplicate.
        :param new_column_name: The name of the new duplicated column.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if new_column_name in self.time_series.columns:
            raise KeyError(f"Column '{new_column_name}' already exists in the DataFrame.")
        self.time_series[new_column_name] = self.time_series[column_name]


    def __repr__(self):
        return f"DaskTimeSeries({len(self.time_series.columns)} columns)"
