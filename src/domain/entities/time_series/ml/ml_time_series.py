from domain.entities.time_series.time_series import TimeSeries


class MlTimeSeries(TimeSeries):
    def __init__(self, data, x_columns, y_column, split_ratio=0.8, shuffle=False, random_seed=None):
        """
        Initialize the MlTimeSeries class and create train/test splits for X and Y.
        
        :param data: The input data (passed to the parent class).
        :param x_columns: List of column names to be used as features (X).
        :param y_column: Column name to be used as the target (Y).
        :param split_ratio: Ratio for train/test split. Default is 0.8 (80% train, 20% test).
        :param shuffle: Whether to shuffle the data before splitting. Default is False.
        :param random_seed: Random seed for reproducibility when shuffling. Default is None.
        """
        super().__init__(data)  # Initialize the parent class

        if not isinstance(x_columns, list) or not isinstance(y_column, str):
            raise ValueError("x_columns should be a list and y_column should be a string.")
        
        if y_column not in self.time_series.columns:
            raise KeyError(f"Target column '{y_column}' not found in the DataFrame.")
        
        if any(col not in self.time_series.columns for col in x_columns):
            missing_cols = [col for col in x_columns if col not in self.time_series.columns]
            raise KeyError(f"Feature columns {missing_cols} not found in the DataFrame.")

        self.x_columns = x_columns
        self.y_column = y_column
        self.split_ratio = split_ratio
        self.shuffle = shuffle
        self.random_seed = random_seed

        # Create the train/test split
        self._create_splits()

    def _create_splits(self):
        """
        Internal method to create train/test splits for X and Y.
        """
        data = self.time_series.copy()

        # Shuffle data if required
        if self.shuffle:
            data = data.sample(frac=1, random_state=self.random_seed).reset_index(drop=True)

        # Separate features and target
        x_data = data[self.x_columns]
        y_data = data[self.y_column]

        # Determine split index
        split_index = int(len(data) * self.split_ratio)

        # Split the data
        self.train_x = x_data.iloc[:split_index]
        self.train_y = y_data.iloc[:split_index]
        self.test_x = x_data.iloc[split_index:]
        self.test_y = y_data.iloc[split_index:]

    def prepare_classification_data(self, num_classes):
        """
        Prepares classification data by dividing the target column (Y) into quantile-based classes.
        
        :param num_classes: Number of classes to divide the target column into.
        :return: None. Modifies train_y and test_y in place to be class labels.
        """
        if num_classes < 2:
            raise ValueError("Number of classes must be at least 2.")

        # Use the parent class's `add_quantile_columns` method to create class labels
        self.time_series = self.add_quantile_columns(
            data=self.time_series,
            column=self.y_column,
            quantiles=num_classes,
            new_column_name="class"
        )

        # Update train_y and test_y to use the new 'class' column
        self.train_y = self.time_series["class"].iloc[:len(self.train_x)]
        self.test_y = self.time_series["class"].iloc[len(self.train_x):]

    def __repr__(self):
        """
        Representation of the MlTimeSeries object.
        """
        return (
            f"MlTimeSeries("
            f"{len(self.train_x)} train rows, "
            f"{len(self.test_x)} test rows, "
            f"{len(self.x_columns)} features, "
            f"target: '{self.y_column}')"
        )
