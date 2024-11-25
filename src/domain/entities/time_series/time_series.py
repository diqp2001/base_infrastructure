import pandas as pd
import numpy as np

class TimeSeries:
    def __init__(self, data):
        """
        Initialize a TimeSeries object from a DataFrame, NumPy array, list, or dict.
        :param data: The input data to construct the DataFrame.
        """
        if isinstance(data, pd.DataFrame):
            self.time_series = data
        elif isinstance(data, np.ndarray):
            self.time_series = pd.DataFrame(data)
        elif isinstance(data, list):
            self.time_series = pd.DataFrame(data)
        elif isinstance(data, dict):
            self.time_series = pd.DataFrame(data)
        else:
            raise TypeError("Input data must be a DataFrame, NumPy array, list, or dict.")

    def to_numpy(self):
        """Convert the time series DataFrame to a NumPy array."""
        return self.time_series.to_numpy()

    def to_list(self):
        """Convert the time series DataFrame to a list."""
        return self.time_series.values.tolist()

    def to_dict(self):
        """Convert the time series DataFrame to a dictionary."""
        return self.time_series.to_dict()

    def add_column_with_lag(self, column_name, lag, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add a new column to the DataFrame with values lagged by a specific number of steps.
        Optionally, replace the original column with the lagged values.
        Optionally, group the data by specific columns before applying the lag.

        :param column_name: The name of the column to lag.
        :param lag: The number of steps to lag.
        :param new_column_name: The name of the new column. Defaults to "{column_name}_lag_{lag}".
        :param replace: If True, replace the original column with the lagged column.
        :param groupby_columns: List of columns to group by before applying the lag.
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

    def add_column_with_lag_columns(self, column_names, lag, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add lag columns to the DataFrame for each column in the provided list of columns.
        :param column_names: List of columns to apply the lag operation.
        :param lag: The number of steps to lag.
        :param new_column_name: The base name for new columns. Defaults to "{column_name}_lag_{lag}".
        :param replace: If True, replace the original columns with the lagged columns.
        :param groupby_columns: List of columns to group by before applying the lag.
        """
        for column_name in column_names:
            if column_name not in self.time_series.columns:
                raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
            # Generate default new column name
            if not new_column_name:
                new_column_name = f"{column_name}_lag_{lag}"
            
            # Call the single-column lag function for each column
            self.add_column_with_lag(column_name, lag, new_column_name=new_column_name, replace=replace, groupby_columns=groupby_columns)

    def add_quantile_column(self, column_name, quantiles, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add a new column to the DataFrame with quantile categories based on a specific column.
        Optionally, replace the original column with the quantile values.
        Optionally, group the data by specific columns before calculating quantiles.

        :param column_name: The name of the column to calculate quantiles.
        :param quantiles: The number of quantile bins to calculate (e.g., 4 for quartiles).
        :param new_column_name: The name of the new column. Defaults to "{column_name}_quantile_{quantiles}".
        :param replace: If True, replace the original column with the quantile column.
        :param groupby_columns: List of columns to group by before applying quantiles.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if not new_column_name:
            new_column_name = f"{column_name}_quantile_{quantiles}"
        
        if groupby_columns:
            self.time_series[new_column_name] = self.time_series.groupby(groupby_columns)[column_name].apply(lambda x: pd.qcut(x, quantiles, labels=False))
        else:
            self.time_series[new_column_name] = pd.qcut(self.time_series[column_name], quantiles, labels=False)
        
        if replace:
            self.time_series[column_name] = self.time_series[new_column_name]

    def add_quantile_columns(self, column_names, quantiles, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add quantile columns to the DataFrame for each column in the provided list of columns.
        :param column_names: List of columns to calculate quantiles.
        :param quantiles: The number of quantile bins to calculate (e.g., 4 for quartiles).
        :param new_column_name: The base name for new columns. Defaults to "{column_name}_quantile_{quantiles}".
        :param replace: If True, replace the original columns with the quantile columns.
        :param groupby_columns: List of columns to group by before calculating quantiles.
        """
        for column_name in column_names:
            if column_name not in self.time_series.columns:
                raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
            # Generate default new column name
            if not new_column_name:
                new_column_name = f"{column_name}_quantile_{quantiles}"
            
            # Call the single-column quantile function for each column
            self.add_quantile_column(column_name, quantiles, new_column_name=new_column_name, replace=replace, groupby_columns=groupby_columns)
    
    def add_z_score_column(self, column_name, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add a new column to the DataFrame with z-scores calculated from a specific column.
        Optionally, replace the original column with the z-score values.
        Optionally, group the data by specific columns before calculating z-scores.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        if not new_column_name:
            new_column_name = f"{column_name}_z_score"

        # Compute z-scores with optional grouping
        if groupby_columns:
            self.time_series[new_column_name] = self.time_series.groupby(groupby_columns)[column_name].apply(
                lambda x: (x - x.mean()) / x.std()
            )
        else:
            mean = self.time_series[column_name].mean()
            std = self.time_series[column_name].std()
            self.time_series[new_column_name] = (self.time_series[column_name] - mean) / std

        # Optionally replace original column
        if replace:
            self.time_series[column_name] = self.time_series[new_column_name]

    def add_z_score_columns(self, column_names, new_column_name=None, replace=False, groupby_columns=None):
        """
        Add z-score columns for a list of columns, using the single-column function.
        """
        for column_name in column_names:
            # Generate default new column name if not specified
            column_z_name = new_column_name or f"{column_name}_z_score"
            self.add_z_score_column(
                column_name, new_column_name=column_z_name, replace=replace, groupby_columns=groupby_columns
            )

    def calculate_iterative_z_scores(self, column_names, iterations, cap_range=None, replace=False, groupby_columns=None):
        """
        Iteratively calculate z-scores for specified columns, reusing the `add_z_score_column` function.
        """
        for column_name in column_names:
            if column_name not in self.time_series.columns:
                raise KeyError(f"Column '{column_name}' not found in the DataFrame.")

            current_column = column_name
            for i in range(1, iterations + 1):
                # Construct the iterative column name
                new_column_name = f"{column_name}_z_score_iter_{i}"

                # Reuse the z-score function
                self.add_z_score_column(
                    current_column, new_column_name=new_column_name, groupby_columns=groupby_columns
                )

                # Apply capping if specified
                if cap_range:
                    min_cap, max_cap = cap_range
                    self.time_series[new_column_name] = self.time_series[new_column_name].clip(lower=min_cap, upper=max_cap)

                # Update current column for the next iteration
                current_column = new_column_name

            # Replace the original column if specified
            if replace:
                self.time_series[column_name] = self.time_series[current_column]

    def remove_nulls(self, column_name, fill_value):
        """
        Replace null values in a single column with a specified value.
        """
        if column_name not in self.time_series.columns:
            raise KeyError(f"Column '{column_name}' not found in the DataFrame.")
        self.time_series[column_name].fillna(fill_value, inplace=True)

    def remove_nulls_from_columns(self, column_names, fill_value):
        """
        Replace null values in multiple columns using the single-column null removal function.
        """
        for column_name in column_names:
            self.remove_nulls(column_name, fill_value)
            
    def pivot_time_series(self,index_list,column_list,values_name):
        self.time_series = self.time_series.pivot_table(index=index_list, columns=column_list,values=values_name).reset_index()
    
    def __repr__(self):
        return f"TimeSeries({self.time_series.shape[0]} rows, {self.time_series.shape[1]} columns)"