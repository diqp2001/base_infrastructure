import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

class ReportingManager:
    def __init__(self, data):
        """
        Initialize the ReportingManager with a DataFrame.
        :param data: A DataFrame containing data to be analyzed or visualized.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input data must be a pandas DataFrame.")
        self.data = data

    def calculate_metrics(self, y_true, y_pred):
        """
        Calculate and return classification metrics.
        :param y_true: Array-like, true labels.
        :param y_pred: Array-like, predicted labels.
        :return: Dictionary of metrics (confusion matrix, F1, precision, recall, accuracy).
        """
        metrics = {
            "Confusion Matrix": confusion_matrix(y_true, y_pred),
            "F1 Score": f1_score(y_true, y_pred, average="weighted"),
            "Precision": precision_score(y_true, y_pred, average="weighted"),
            "Recall": recall_score(y_true, y_pred, average="weighted"),
            "Accuracy": accuracy_score(y_true, y_pred)
        }
        return metrics

    def plot_histogram(self, column, bins=10, title=None):
        """
        Plot a histogram for a specified column in the DataFrame.
        :param column: The column to plot.
        :param bins: Number of bins for the histogram.
        :param title: Title for the plot.
        """
        if column not in self.data.columns:
            raise KeyError(f"Column '{column}' not found in the DataFrame.")
        
        plt.figure(figsize=(8, 5))
        sns.histplot(self.data[column], bins=bins, kde=True)
        plt.title(title or f"Histogram of {column}")
        plt.xlabel(column)
        plt.ylabel("Frequency")
        plt.show()

    def plot_line_evolution(self, columns, title=None):
        """
        Plot line evolution of specified columns over time.
        :param columns: List of column names to plot.
        :param title: Title for the plot.
        """
        if not all(col in self.data.columns for col in columns):
            missing = [col for col in columns if col not in self.data.columns]
            raise KeyError(f"Columns '{missing}' not found in the DataFrame.")

        plt.figure(figsize=(10, 6))
        for col in columns:
            plt.plot(self.data.index, self.data[col], label=col)
        plt.title(title or "Line Evolution Over Time")
        plt.xlabel("Time")
        plt.ylabel("Values")
        plt.legend()
        plt.show()

    def plot_confusion_matrix(self, y_true, y_pred, labels=None, title=None):
        """
        Plot a confusion matrix as a heatmap.
        :param y_true: Array-like, true labels.
        :param y_pred: Array-like, predicted labels.
        :param labels: List of label names for the heatmap.
        :param title: Title for the plot.
        """
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
        plt.title(title or "Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("True")
        plt.show()

    def display_summary_statistics(self, column):
        """
        Display mean, max, and other summary statistics for a specific column.
        :param column: The column to summarize.
        """
        if column not in self.data.columns:
            raise KeyError(f"Column '{column}' not found in the DataFrame.")
        summary = self.data[column].describe()
        mean = summary["mean"]
        maximum = summary["max"]
        print(f"Mean: {mean}, Max: {maximum}")
        print(summary)

    def to_table_array(self):
        """
        Convert the DataFrame to a NumPy table array.
        :return: A NumPy array representing the DataFrame.
        """
        return self.data.to_numpy()

    def __repr__(self):
        return f"ReportingManager(DataFrame with {self.data.shape[0]} rows and {self.data.shape[1]} columns)"
