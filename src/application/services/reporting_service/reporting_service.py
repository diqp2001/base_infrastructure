import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
import io
import base64
from datetime import datetime

class ReportingService:
    """
    Service class for generating reports, metrics, and visualizations.
    Provides comprehensive reporting functionality for data analysis and model evaluation.
    """
    
    def __init__(self, data: pd.DataFrame = None):
        """
        Initialize the ReportingService with optional data.
        :param data: Optional DataFrame containing data to be analyzed or visualized.
        """
        if data is not None and not isinstance(data, pd.DataFrame):
            raise TypeError("Input data must be a pandas DataFrame.")
        self.data = data
        self.reports = {}  # Store generated reports

    def set_data(self, data: pd.DataFrame):
        """
        Set or update the data for analysis.
        :param data: DataFrame containing data to be analyzed.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input data must be a pandas DataFrame.")
        self.data = data

    def calculate_classification_metrics(self, y_true, y_pred, labels: List[str] = None) -> Dict[str, Any]:
        """
        Calculate and return classification metrics.
        :param y_true: Array-like, true labels.
        :param y_pred: Array-like, predicted labels.
        :param labels: Optional list of label names for better reporting.
        :return: Dictionary of metrics (confusion matrix, F1, precision, recall, accuracy).
        """
        metrics = {
            "confusion_matrix": confusion_matrix(y_true, y_pred),
            "f1_score": f1_score(y_true, y_pred, average="weighted"),
            "precision": precision_score(y_true, y_pred, average="weighted"),
            "recall": recall_score(y_true, y_pred, average="weighted"),
            "accuracy": accuracy_score(y_true, y_pred),
            "f1_score_macro": f1_score(y_true, y_pred, average="macro"),
            "precision_macro": precision_score(y_true, y_pred, average="macro"),
            "recall_macro": recall_score(y_true, y_pred, average="macro")
        }
        
        # Add per-class metrics if labels are provided
        if labels:
            per_class_f1 = f1_score(y_true, y_pred, average=None)
            per_class_precision = precision_score(y_true, y_pred, average=None)
            per_class_recall = recall_score(y_true, y_pred, average=None)
            
            for i, label in enumerate(labels):
                metrics[f"f1_score_{label}"] = per_class_f1[i] if i < len(per_class_f1) else 0
                metrics[f"precision_{label}"] = per_class_precision[i] if i < len(per_class_precision) else 0
                metrics[f"recall_{label}"] = per_class_recall[i] if i < len(per_class_recall) else 0
        
        return metrics

    def calculate_regression_metrics(self, y_true, y_pred) -> Dict[str, float]:
        """
        Calculate regression metrics.
        :param y_true: Array-like, true values.
        :param y_pred: Array-like, predicted values.
        :return: Dictionary of regression metrics.
        """
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        metrics = {
            "mse": mean_squared_error(y_true, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
            "mae": mean_absolute_error(y_true, y_pred),
            "r2_score": r2_score(y_true, y_pred),
            "mean_residual": np.mean(y_pred - y_true),
            "std_residual": np.std(y_pred - y_true)
        }
        
        return metrics

    def generate_descriptive_stats(self, columns: List[str] = None) -> Dict[str, Any]:
        """
        Generate descriptive statistics for the data.
        :param columns: Optional list of columns to analyze.
        :return: Dictionary containing descriptive statistics.
        """
        if self.data is None:
            raise ValueError("No data available. Please set data first.")
        
        data_subset = self.data[columns] if columns else self.data
        
        stats = {
            "basic_stats": data_subset.describe().to_dict(),
            "null_counts": data_subset.isnull().sum().to_dict(),
            "data_types": data_subset.dtypes.to_dict(),
            "correlation_matrix": data_subset.select_dtypes(include=[np.number]).corr().to_dict()
        }
        
        return stats

    def plot_histogram(self, column: str, bins: int = 10, title: str = None, save_path: str = None) -> Optional[str]:
        """
        Plot a histogram for a specified column.
        :param column: The column to plot.
        :param bins: Number of bins for the histogram.
        :param title: Title for the plot.
        :param save_path: Optional path to save the plot.
        :return: Base64 encoded plot if save_path is None, else None.
        """
        if self.data is None:
            raise ValueError("No data available. Please set data first.")
        
        if column not in self.data.columns:
            raise KeyError(f"Column '{column}' not found in the DataFrame.")
        
        plt.figure(figsize=(10, 6))
        sns.histplot(self.data[column], bins=bins, kde=True)
        plt.title(title or f"Histogram of {column}")
        plt.xlabel(column)
        plt.ylabel("Frequency")
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return None
        else:
            # Return base64 encoded plot
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            return base64.b64encode(plot_data).decode('utf-8')

    def plot_line_evolution(self, columns: List[str], title: str = None, save_path: str = None) -> Optional[str]:
        """
        Plot line evolution for specified columns over time or index.
        :param columns: List of columns to plot.
        :param title: Title for the plot.
        :param save_path: Optional path to save the plot.
        :return: Base64 encoded plot if save_path is None, else None.
        """
        if self.data is None:
            raise ValueError("No data available. Please set data first.")
        
        missing_columns = [col for col in columns if col not in self.data.columns]
        if missing_columns:
            raise KeyError(f"Columns {missing_columns} not found in the DataFrame.")
        
        plt.figure(figsize=(12, 8))
        for column in columns:
            plt.plot(self.data.index, self.data[column], label=column, marker='o', markersize=3)
        
        plt.title(title or f"Evolution of {', '.join(columns)}")
        plt.xlabel("Index")
        plt.ylabel("Values")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return None
        else:
            # Return base64 encoded plot
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            return base64.b64encode(plot_data).decode('utf-8')

    def plot_correlation_heatmap(self, columns: List[str] = None, title: str = None, save_path: str = None) -> Optional[str]:
        """
        Plot correlation heatmap for numeric columns.
        :param columns: Optional list of columns to include.
        :param title: Title for the plot.
        :param save_path: Optional path to save the plot.
        :return: Base64 encoded plot if save_path is None, else None.
        """
        if self.data is None:
            raise ValueError("No data available. Please set data first.")
        
        numeric_data = self.data.select_dtypes(include=[np.number])
        if columns:
            numeric_data = numeric_data[columns]
        
        if numeric_data.empty:
            raise ValueError("No numeric columns available for correlation analysis.")
        
        correlation_matrix = numeric_data.corr()
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                   square=True, fmt='.2f', cbar_kws={"shrink": .8})
        plt.title(title or "Correlation Heatmap")
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return None
        else:
            # Return base64 encoded plot
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            return base64.b64encode(plot_data).decode('utf-8')

    def plot_confusion_matrix(self, y_true, y_pred, labels: List[str] = None, 
                             title: str = None, save_path: str = None) -> Optional[str]:
        """
        Plot confusion matrix.
        :param y_true: Array-like, true labels.
        :param y_pred: Array-like, predicted labels.
        :param labels: Optional list of label names.
        :param title: Title for the plot.
        :param save_path: Optional path to save the plot.
        :return: Base64 encoded plot if save_path is None, else None.
        """
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=labels, yticklabels=labels)
        plt.title(title or "Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("Actual")
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return None
        else:
            # Return base64 encoded plot
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            return base64.b64encode(plot_data).decode('utf-8')

    def generate_model_report(self, model_name: str, y_true, y_pred, 
                             task_type: str = "classification", labels: List[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive model performance report.
        :param model_name: Name of the model.
        :param y_true: True labels/values.
        :param y_pred: Predicted labels/values.
        :param task_type: Type of task ("classification" or "regression").
        :param labels: Optional list of label names for classification.
        :return: Dictionary containing the complete report.
        """
        report = {
            "model_name": model_name,
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            "sample_count": len(y_true)
        }
        
        if task_type == "classification":
            metrics = self.calculate_classification_metrics(y_true, y_pred, labels)
            report.update(metrics)
            
            # Generate confusion matrix plot
            cm_plot = self.plot_confusion_matrix(y_true, y_pred, labels)
            if cm_plot:
                report["confusion_matrix_plot"] = cm_plot
                
        elif task_type == "regression":
            metrics = self.calculate_regression_metrics(y_true, y_pred)
            report.update(metrics)
            
            # Add prediction vs actual plot for regression
            plt.figure(figsize=(8, 6))
            plt.scatter(y_true, y_pred, alpha=0.6)
            plt.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
            plt.xlabel('Actual')
            plt.ylabel('Predicted')
            plt.title('Actual vs Predicted Values')
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            report["actual_vs_predicted_plot"] = base64.b64encode(plot_data).decode('utf-8')
        
        # Store report
        self.reports[f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"] = report
        
        return report

    def generate_data_quality_report(self, columns: List[str] = None) -> Dict[str, Any]:
        """
        Generate a data quality report.
        :param columns: Optional list of columns to analyze.
        :return: Dictionary containing data quality metrics.
        """
        if self.data is None:
            raise ValueError("No data available. Please set data first.")
        
        data_subset = self.data[columns] if columns else self.data
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_rows": len(data_subset),
            "total_columns": len(data_subset.columns),
            "memory_usage_mb": data_subset.memory_usage(deep=True).sum() / 1024**2,
            "column_analysis": {}
        }
        
        for column in data_subset.columns:
            col_data = data_subset[column]
            analysis = {
                "data_type": str(col_data.dtype),
                "null_count": col_data.isnull().sum(),
                "null_percentage": (col_data.isnull().sum() / len(col_data)) * 100,
                "unique_count": col_data.nunique(),
                "unique_percentage": (col_data.nunique() / len(col_data)) * 100
            }
            
            if col_data.dtype in ['int64', 'float64']:
                analysis.update({
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "mean": float(col_data.mean()),
                    "std": float(col_data.std()),
                    "zeros_count": (col_data == 0).sum(),
                    "negative_count": (col_data < 0).sum() if col_data.dtype in ['int64', 'float64'] else 0
                })
            
            report["column_analysis"][column] = analysis
        
        return report

    def export_report(self, report: Dict[str, Any], file_path: str, format_type: str = 'json'):
        """
        Export a report to file.
        :param report: The report dictionary to export.
        :param file_path: Path to save the report.
        :param format_type: Format to save ('json', 'csv', 'txt').
        """
        if format_type == 'json':
            import json
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
        elif format_type == 'csv':
            # Flatten the report for CSV export
            flattened = self._flatten_dict(report)
            pd.DataFrame([flattened]).to_csv(file_path, index=False)
        elif format_type == 'txt':
            with open(file_path, 'w') as f:
                self._write_dict_to_text(report, f)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten a nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _write_dict_to_text(self, d: Dict[str, Any], file_handle, indent: int = 0):
        """Write dictionary to text file with proper formatting."""
        for key, value in d.items():
            if isinstance(value, dict):
                file_handle.write(f"{'  ' * indent}{key}:\n")
                self._write_dict_to_text(value, file_handle, indent + 1)
            else:
                file_handle.write(f"{'  ' * indent}{key}: {value}\n")

    def get_stored_reports(self) -> List[str]:
        """
        Get list of stored report keys.
        :return: List of report keys.
        """
        return list(self.reports.keys())

    def get_report(self, report_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a stored report.
        :param report_key: Key of the report to retrieve.
        :return: Report dictionary or None if not found.
        """
        return self.reports.get(report_key)