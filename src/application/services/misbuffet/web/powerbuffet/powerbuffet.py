"""
PowerBuffet - Data Visualization and Database Explorer Tool

A lightweight Power BI alternative that provides database connectivity,
table browsing, and predefined visualization templates using Python.
All data preparation and formatting are handled in Python for consistency
with backend computation and analytical workflows.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import io
import base64
import numpy as np

logger = logging.getLogger(__name__)


class PowerBuffetService:
    """
    PowerBuffet service for database visualization and exploration
    """
    
    def __init__(self):
        self.visualization_registry = self._initialize_visualization_registry()
        self.project_root = Path(__file__).parents[6]  # Navigate to project root
        
    def _initialize_visualization_registry(self) -> Dict[str, callable]:
        """Initialize the registry of available visualization functions"""
        return {
            "Portfolio Performance": self._plot_portfolio_performance,
            "Asset Correlation Heatmap": self._plot_correlation_heatmap,
            "Sector Distribution": self._plot_sector_distribution,
            "Market Cap Analysis": self._plot_market_cap_analysis,
            "Trading Volume Trends": self._plot_volume_trends,
            "Financial Ratios Comparison": self._plot_financial_ratios,
            "Time Series Analysis": self._plot_time_series,
            "Security Price Comparison": self._plot_security_price_comparison
        }
    
    def get_available_databases(self) -> List[Dict[str, str]]:
        """Get list of available database connections"""
        databases = []
        
        # Check for SQLite databases in the project
        sqlite_files = list(self.project_root.rglob("*.db")) + list(self.project_root.rglob("*.sqlite"))
        
        for db_file in sqlite_files:
            databases.append({
                "name": db_file.name,
                "type": "SQLite",
                "path": str(db_file),
                "connection_string": str(db_file)
            })
        
        # Add CSV data sources from stock_data directory
        stock_data_dir = self.project_root / "data" / "stock_data"
        if stock_data_dir.exists():
            databases.append({
                "name": "Stock Data (CSV)",
                "type": "CSV_Stock_Data",
                "path": str(stock_data_dir),
                "connection_string": str(stock_data_dir)
            })
        
        fx_data_dir = self.project_root / "data" / "fx_data"
        if fx_data_dir.exists():
            databases.append({
                "name": "FX Data (CSV)",
                "type": "CSV_FX_Data",
                "path": str(fx_data_dir),
                "connection_string": str(fx_data_dir)
            })
        
        return databases
    
    def get_database_tables(self, database_path: str) -> List[Dict[str, Any]]:
        """Get tables from the selected database with section organization"""
        tables = []
        
        try:
            if database_path.endswith(('.db', '.sqlite')):
                conn = sqlite3.connect(database_path)
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                table_names = cursor.fetchall()
                
                for (table_name,) in table_names:
                    # Get table info
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = cursor.fetchall()
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    row_count = cursor.fetchone()[0]
                    
                    # Get preview data (SELECT TOP 10)
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
                    preview_data = cursor.fetchall()
                    
                    # Organize by section based on table name patterns
                    section = self._categorize_table(table_name)
                    
                    # Convert preview data and handle potential NaN/None values
                    cleaned_preview_data = []
                    for row in preview_data:
                        cleaned_row = []
                        for value in row:
                            if pd.isna(value) or value is None:
                                cleaned_row.append(None)
                            else:
                                cleaned_row.append(value)
                        cleaned_preview_data.append(cleaned_row)
                    
                    tables.append({
                        "name": table_name,
                        "section": section,
                        "columns": [{"name": col[1], "type": col[2]} for col in columns],
                        "row_count": row_count,
                        "preview_data": cleaned_preview_data,
                        "column_names": [col[1] for col in columns]
                    })
                
                conn.close()
            
            elif "stock_data" in database_path and Path(database_path).is_dir():
                # Handle CSV stock data directory
                data_dir = Path(database_path)
                csv_files = list(data_dir.glob("*.csv"))
                
                for csv_file in csv_files:
                    # Read first few rows to get column info
                    df = pd.read_csv(csv_file, nrows=5)
                    full_df = pd.read_csv(csv_file)
                    # Clean NaN values to prevent fillna() issues
                    full_df = full_df.fillna(value=None)
                    row_count = len(full_df)
                    
                    # Get preview data (first 10 rows)
                    preview_df = full_df.head(10)
                    # Replace NaN values with None for JSON serialization
                    preview_df = preview_df.fillna(None)
                    preview_data = [list(row) for row in preview_df.values]
                    
                    columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
                    section = "Stock Data"
                    
                    tables.append({
                        "name": csv_file.stem,  # filename without extension
                        "section": section,
                        "columns": columns,
                        "row_count": row_count,
                        "file_path": str(csv_file),
                        "preview_data": preview_data,
                        "column_names": list(df.columns)
                    })
            
            elif "fx_data" in database_path and Path(database_path).is_dir():
                # Handle CSV FX data directory
                data_dir = Path(database_path)
                csv_files = list(data_dir.glob("*.csv"))
                
                for csv_file in csv_files:
                    # Read first few rows to get column info
                    df = pd.read_csv(csv_file, nrows=5)
                    full_df = pd.read_csv(csv_file)
                    # Clean NaN values to prevent fillna() issues
                    full_df = full_df.fillna(value=None)
                    row_count = len(full_df)
                    
                    # Get preview data (first 10 rows)
                    preview_df = full_df.head(10)
                    # Replace NaN values with None for JSON serialization
                    preview_df = preview_df.fillna(None)
                    preview_data = [list(row) for row in preview_df.values]
                    
                    columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
                    section = "FX Data"
                    
                    tables.append({
                        "name": csv_file.stem,  # filename without extension
                        "section": section,
                        "columns": columns,
                        "row_count": row_count,
                        "file_path": str(csv_file),
                        "preview_data": preview_data,
                        "column_names": list(df.columns)
                    })
                
        except Exception as e:
            logger.error(f"Error getting tables from database {database_path}: {e}")
            
        return tables
    
    def _categorize_table(self, table_name: str) -> str:
        """Categorize table into logical sections based on name patterns."""
        table_lower = table_name.lower()
        
        # Financial data tables
        if any(keyword in table_lower for keyword in ['price', 'stock', 'equity', 'share', 'ohlc']):
            return "Market Data"
        elif any(keyword in table_lower for keyword in ['fundamental', 'balance', 'income', 'cashflow', 'ratio']):
            return "Fundamental Data"
        elif any(keyword in table_lower for keyword in ['company', 'security', 'symbol', 'listing']):
            return "Reference Data"
        elif any(keyword in table_lower for keyword in ['factor', 'alpha', 'signal', 'model']):
            return "Quantitative Data"
        elif any(keyword in table_lower for keyword in ['portfolio', 'position', 'holding', 'allocation']):
            return "Portfolio Data"
        elif any(keyword in table_lower for keyword in ['trade', 'order', 'execution', 'transaction']):
            return "Trading Data"
        elif any(keyword in table_lower for keyword in ['risk', 'var', 'volatility', 'exposure']):
            return "Risk Data"
        elif any(keyword in table_lower for keyword in ['backtest', 'result', 'performance', 'metric']):
            return "Analytics"
        else:
            return "Other Data"
    
    def get_table_preview(self, database_path: str, table_name: str) -> Dict[str, Any]:
        """Get preview data for a specific table (SELECT TOP 10)"""
        try:
            if database_path.endswith(('.db', '.sqlite')):
                conn = sqlite3.connect(database_path)
                cursor = conn.cursor()
                
                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]
                
                # Get preview data (top 10 rows)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
                preview_rows = cursor.fetchall()
                
                conn.close()
                
                return {
                    "table_name": table_name,
                    "column_names": column_names,
                    "data": [list(row) for row in preview_rows],
                    "row_count": len(preview_rows)
                }
            
            elif ("stock_data" in database_path or "fx_data" in database_path) and Path(database_path).is_dir():
                # Handle CSV files
                data_dir = Path(database_path)
                csv_file = data_dir / f"{table_name}.csv"
                
                if csv_file.exists():
                    df = pd.read_csv(csv_file)
                    # Clean NaN values to prevent fillna() issues
                    df = df.fillna(value=None)
                    preview_df = df.head(10)
                    # Replace NaN values with None for JSON serialization
                    preview_df = preview_df.fillna(None)
                    
                    return {
                        "table_name": table_name,
                        "column_names": list(df.columns),
                        "data": [list(row) for row in preview_df.values],
                        "row_count": len(preview_df),
                        "total_rows": len(df)
                    }
                else:
                    return {"error": f"File {csv_file} not found"}
            
            else:
                return {"error": "Unsupported database type"}
                
        except Exception as e:
            logger.error(f"Error getting table preview: {e}")
            return {"error": str(e)}
    
    def get_available_visualizations(self) -> List[str]:
        """Get list of available visualization templates"""
        return list(self.visualization_registry.keys())
    
    def run_visualization(self, database_path: str, table_name: str, 
                         visualization_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a visualization function and return the result"""
        try:
            if visualization_name not in self.visualization_registry:
                raise ValueError(f"Unknown visualization: {visualization_name}")
            
            # Load data from database
            data = self._load_table_data(database_path, table_name)
            
            # Execute visualization function
            viz_func = self.visualization_registry[visualization_name]
            result = viz_func(data, params or {})
            
            return {
                "success": True,
                "visualization": result,
                "metadata": {
                    "database": database_path,
                    "table": table_name,
                    "visualization": visualization_name,
                    "row_count": len(data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error running visualization: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "database": database_path,
                    "table": table_name,
                    "visualization": visualization_name
                }
            }
    
    def _load_table_data(self, database_path: str, table_name: str, limit: int = 10000) -> pd.DataFrame:
        """Load data from database table"""
        if database_path.endswith(('.db', '.sqlite')):
            conn = sqlite3.connect(database_path)
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            data = pd.read_sql_query(query, conn)
            conn.close()
            return data
        elif "stock_data" in database_path or "fx_data" in database_path:
            # Handle CSV files
            data_dir = Path(database_path)
            csv_file = data_dir / f"{table_name}.csv"
            
            if csv_file.exists():
                data = pd.read_csv(csv_file)
                # Clean NaN values to prevent fillna() issues
                data = data.fillna(value=None)
                # Convert Date column to datetime if it exists
                if 'Date' in data.columns:
                    data['Date'] = pd.to_datetime(data['Date'])
                    data = data.set_index('Date')
                return data.head(limit)
            else:
                raise FileNotFoundError(f"CSV file {csv_file} not found")
        else:
            raise NotImplementedError("Only SQLite databases and CSV files are currently supported")
    
    def _create_plot_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_data = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        return img_data

    # Visualization functions
    def _plot_portfolio_performance(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate portfolio performance visualization"""
        try:
            # Try to identify relevant columns for portfolio analysis
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) == 0:
                return {"error": "No numeric columns found for portfolio analysis"}
            
            # Create a simple line plot with the first numeric column
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(data.index, data[numeric_cols[0]], linewidth=2, color='blue')
            ax.set_title(f"Portfolio Performance - {numeric_cols[0]}", fontsize=16, fontweight='bold')
            ax.set_ylabel(numeric_cols[0])
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            
            return {
                "plot_image": plot_image,
                "summary_stats": {
                    "mean": float(data[numeric_cols[0]].mean()),
                    "std": float(data[numeric_cols[0]].std()),
                    "min": float(data[numeric_cols[0]].min()),
                    "max": float(data[numeric_cols[0]].max())
                }
            }
            
        except Exception as e:
            return {"error": f"Error generating portfolio performance plot: {str(e)}"}
    
    def _plot_correlation_heatmap(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate correlation heatmap"""
        try:
            numeric_data = data.select_dtypes(include=['number'])
            
            if len(numeric_data.columns) < 2:
                return {"error": "Need at least 2 numeric columns for correlation analysis"}
            
            corr_matrix = numeric_data.corr()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
            ax.set_title("Asset Correlation Heatmap", fontsize=16, fontweight='bold')
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating correlation heatmap: {str(e)}"}
    
    def _plot_sector_distribution(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate sector distribution pie chart"""
        try:
            # Look for sector-like columns
            text_cols = data.select_dtypes(include=['object']).columns
            sector_col = None
            
            for col in text_cols:
                if 'sector' in col.lower() or 'category' in col.lower() or 'type' in col.lower():
                    sector_col = col
                    break
            
            if sector_col is None and len(text_cols) > 0:
                sector_col = text_cols[0]
            
            if sector_col is None:
                return {"error": "No categorical columns found for sector analysis"}
            
            sector_counts = data[sector_col].value_counts()
            
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.pie(sector_counts.values, labels=sector_counts.index, autopct='%1.1f%%', startangle=90)
            ax.set_title(f"Distribution by {sector_col}", fontsize=16, fontweight='bold')
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating sector distribution: {str(e)}"}
    
    def _plot_market_cap_analysis(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate market cap analysis"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            # Look for market cap or value-related columns
            value_col = None
            for col in numeric_cols:
                if any(term in col.lower() for term in ['cap', 'value', 'market', 'price']):
                    value_col = col
                    break
            
            if value_col is None and len(numeric_cols) > 0:
                value_col = numeric_cols[0]
                
            if value_col is None:
                return {"error": "No numeric columns found for market cap analysis"}
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.hist(data[value_col].dropna(), bins=20, alpha=0.7, edgecolor='black')
            ax.set_title(f"Market Cap Distribution - {value_col}", fontsize=16, fontweight='bold')
            ax.set_xlabel(value_col)
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating market cap analysis: {str(e)}"}
    
    def _plot_volume_trends(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate trading volume trends"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            volume_col = None
            for col in numeric_cols:
                if 'volume' in col.lower() or 'quantity' in col.lower():
                    volume_col = col
                    break
                    
            if volume_col is None and len(numeric_cols) > 0:
                volume_col = numeric_cols[0]
                
            if volume_col is None:
                return {"error": "No numeric columns found for volume analysis"}
            
            # Limit to first 20 rows for readability
            plot_data = data.head(20)
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(range(len(plot_data)), plot_data[volume_col], alpha=0.7)
            ax.set_title(f"Volume Trends - {volume_col}", fontsize=16, fontweight='bold')
            ax.set_xlabel('Data Points')
            ax.set_ylabel(volume_col)
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating volume trends: {str(e)}"}
    
    def _plot_financial_ratios(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate financial ratios comparison"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) < 2:
                return {"error": "Need at least 2 numeric columns for ratio comparison"}
            
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.scatter(data[numeric_cols[0]], data[numeric_cols[1]], alpha=0.6)
            ax.set_title(f"Financial Ratios: {numeric_cols[0]} vs {numeric_cols[1]}", fontsize=16, fontweight='bold')
            ax.set_xlabel(numeric_cols[0])
            ax.set_ylabel(numeric_cols[1])
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating financial ratios plot: {str(e)}"}
    
    def _plot_time_series(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate time series analysis"""
        try:
            numeric_cols = data.select_dtypes(include=['number']).columns
            
            if len(numeric_cols) == 0:
                return {"error": "No numeric columns found for time series"}
            
            # Use index as x-axis
            y_col = numeric_cols[0]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(data.index, data[y_col], linewidth=2, color='green')
            ax.set_title(f"Time Series Analysis - {y_col}", fontsize=16, fontweight='bold')
            ax.set_xlabel('Data Points')
            ax.set_ylabel(y_col)
            ax.grid(True, alpha=0.3)
            
            plot_image = self._create_plot_base64(fig)
            return {"plot_image": plot_image}
            
        except Exception as e:
            return {"error": f"Error generating time series plot: {str(e)}"}
    
    def _plot_security_price_comparison(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """Generate security price comparison chart with date filtering"""
        try:
            # Look for price columns
            price_cols = []
            for col in data.columns:
                if any(term in col.lower() for term in ['close', 'price', 'adj close', 'open', 'high', 'low']):
                    price_cols.append(col)
            
            if len(price_cols) == 0:
                return {"error": "No price columns found for security comparison"}
            
            # Filter data by date range (2019-2020 as requested)
            if isinstance(data.index, pd.DatetimeIndex):
                # Filter for 2019-2020 period
                start_date = '2019-01-01'
                end_date = '2020-12-31'
                filtered_data = data.loc[start_date:end_date]
                
                if len(filtered_data) == 0:
                    filtered_data = data  # Use all data if no data in specified range
                    date_info = "(Using all available data - no data in 2019-2020 range)"
                else:
                    date_info = "(2019-2020)"
            else:
                filtered_data = data
                date_info = "(All available data)"
            
            # Use Close price or first available price column
            price_col = 'Close' if 'Close' in price_cols else price_cols[0]
            
            fig, ax = plt.subplots(figsize=(14, 8))
            ax.plot(filtered_data.index, filtered_data[price_col], linewidth=2, color='blue', label='Price')
            ax.set_title(f"Security Price Analysis {date_info}", fontsize=16, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel(f'{price_col} ($)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis for dates
            if isinstance(filtered_data.index, pd.DatetimeIndex):
                ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plot_image = self._create_plot_base64(fig)
            
            # Calculate summary statistics
            stats = {
                "start_price": float(filtered_data[price_col].iloc[0]),
                "end_price": float(filtered_data[price_col].iloc[-1]),
                "max_price": float(filtered_data[price_col].max()),
                "min_price": float(filtered_data[price_col].min()),
                "avg_price": float(filtered_data[price_col].mean()),
                "total_return_pct": float((filtered_data[price_col].iloc[-1] / filtered_data[price_col].iloc[0] - 1) * 100),
                "volatility_pct": float(filtered_data[price_col].pct_change().std() * np.sqrt(252) * 100),
                "data_points": len(filtered_data)
            }
            
            return {
                "plot_image": plot_image,
                "summary_stats": stats
            }
            
        except Exception as e:
            return {"error": f"Error generating security price comparison: {str(e)}"}
    
    def run_custom_visualization(self, chart_type: str, x_columns: List[Dict], 
                                y_columns: List[Dict], params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute custom multi-column visualization and return the result"""
        try:
            # Collect data from multiple sources
            combined_data = self._load_multi_column_data(x_columns, y_columns)
            
            # Generate custom visualization
            result = self._create_custom_chart(chart_type, combined_data, x_columns, y_columns, params or {})
            
            return {
                "success": True,
                "visualization": result,
                "metadata": {
                    "chart_type": chart_type,
                    "x_columns_count": len(x_columns),
                    "y_columns_count": len(y_columns),
                    "total_data_points": len(combined_data) if combined_data is not None else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error running custom visualization: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "chart_type": chart_type,
                    "x_columns_count": len(x_columns),
                    "y_columns_count": len(y_columns)
                }
            }
    
    def _load_multi_column_data(self, x_columns: List[Dict], y_columns: List[Dict]) -> pd.DataFrame:
        """Load and combine data from multiple database sources and columns"""
        try:
            combined_data = pd.DataFrame()
            column_data = {}
            
            # Process X columns
            for col_info in x_columns:
                data = self._load_table_data(col_info['dbPath'], col_info['table'])
                if col_info['column'] in data.columns:
                    column_key = f"X_{col_info['table']}_{col_info['column']}"
                    column_data[column_key] = {
                        'data': data[col_info['column']],
                        'index': data.index,
                        'source': f"{col_info['dbName']} > {col_info['table']}.{col_info['column']}"
                    }
            
            # Process Y columns
            for col_info in y_columns:
                data = self._load_table_data(col_info['dbPath'], col_info['table'])
                if col_info['column'] in data.columns:
                    column_key = f"Y_{col_info['table']}_{col_info['column']}"
                    column_data[column_key] = {
                        'data': data[col_info['column']],
                        'index': data.index,
                        'source': f"{col_info['dbName']} > {col_info['table']}.{col_info['column']}"
                    }
            
            # Combine data intelligently
            if column_data:
                # Find common index or create unified index
                all_indices = [info['index'] for info in column_data.values()]
                
                # For now, use the first available index and align data
                base_index = all_indices[0]
                combined_data = pd.DataFrame(index=base_index)
                
                for col_key, col_info in column_data.items():
                    try:
                        # Align data to base index
                        aligned_data = col_info['data'].reindex(base_index, method='nearest')
                        combined_data[col_key] = aligned_data
                        combined_data[f"{col_key}_source"] = col_info['source']
                    except Exception as e:
                        logger.warning(f"Error aligning column {col_key}: {e}")
                        # Fallback: reset index and use position-based alignment
                        combined_data[col_key] = col_info['data'].reset_index(drop=True)
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error loading multi-column data: {e}")
            return pd.DataFrame()
    
    def _create_custom_chart(self, chart_type: str, data: pd.DataFrame, 
                           x_columns: List[Dict], y_columns: List[Dict], params: Dict) -> Dict[str, Any]:
        """Create custom visualization based on selected chart type and columns"""
        try:
            if data.empty:
                return {"error": "No data available for visualization"}
            
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Get column names for plotting
            x_cols = [col for col in data.columns if col.startswith('X_') and not col.endswith('_source')]
            y_cols = [col for col in data.columns if col.startswith('Y_') and not col.endswith('_source')]
            
            if chart_type == 'scatter':
                result = self._create_scatter_plot(ax, data, x_cols, y_cols)
            elif chart_type == 'line':
                result = self._create_line_plot(ax, data, x_cols, y_cols)
            elif chart_type == 'bar':
                result = self._create_bar_plot(ax, data, x_cols, y_cols)
            elif chart_type == 'histogram':
                result = self._create_histogram_plot(ax, data, x_cols, y_cols)
            elif chart_type == 'correlation':
                result = self._create_correlation_plot(ax, data, x_cols, y_cols)
            else:
                return {"error": f"Unsupported chart type: {chart_type}"}
            
            if 'error' in result:
                return result
            
            # Finalize plot
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            
            plot_image = self._create_plot_base64(fig)
            
            # Calculate summary statistics
            stats = self._calculate_multi_column_stats(data, x_cols, y_cols)
            
            return {
                "plot_image": plot_image,
                "summary_stats": stats,
                "chart_info": {
                    "type": chart_type,
                    "x_columns": len(x_cols),
                    "y_columns": len(y_cols),
                    "data_points": len(data)
                }
            }
            
        except Exception as e:
            return {"error": f"Error creating custom chart: {str(e)}"}
    
    def _create_scatter_plot(self, ax, data: pd.DataFrame, x_cols: List[str], y_cols: List[str]) -> Dict[str, Any]:
        """Create scatter plot"""
        try:
            if len(x_cols) == 0 or len(y_cols) == 0:
                return {"error": "Need at least one X and one Y column for scatter plot"}
            
            # Use first columns or create combinations
            x_col = x_cols[0]
            y_col = y_cols[0]
            
            ax.scatter(data[x_col], data[y_col], alpha=0.6, s=50)
            ax.set_xlabel(x_col.replace('X_', '').replace('_', '.'))
            ax.set_ylabel(y_col.replace('Y_', '').replace('_', '.'))
            ax.set_title(f"Scatter Plot: {x_col.replace('X_', '')} vs {y_col.replace('Y_', '')}")
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Error creating scatter plot: {str(e)}"}
    
    def _create_line_plot(self, ax, data: pd.DataFrame, x_cols: List[str], y_cols: List[str]) -> Dict[str, Any]:
        """Create line plot"""
        try:
            if len(y_cols) == 0:
                return {"error": "Need at least one Y column for line plot"}
            
            # Use index as X if no X columns, otherwise use first X column
            if len(x_cols) > 0:
                x_data = data[x_cols[0]]
                x_label = x_cols[0].replace('X_', '').replace('_', '.')
            else:
                x_data = data.index
                x_label = 'Index'
            
            colors = plt.cm.tab10(np.linspace(0, 1, len(y_cols)))
            
            for i, y_col in enumerate(y_cols):
                ax.plot(x_data, data[y_col], linewidth=2, color=colors[i], 
                       label=y_col.replace('Y_', '').replace('_', '.'), alpha=0.8)
            
            ax.set_xlabel(x_label)
            ax.set_ylabel('Values')
            ax.set_title('Multi-Column Line Chart')
            
            if len(y_cols) > 1:
                ax.legend()
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Error creating line plot: {str(e)}"}
    
    def _create_bar_plot(self, ax, data: pd.DataFrame, x_cols: List[str], y_cols: List[str]) -> Dict[str, Any]:
        """Create bar plot"""
        try:
            if len(y_cols) == 0:
                return {"error": "Need at least one Y column for bar plot"}
            
            # Use first 20 data points for readability
            plot_data = data.head(20)
            
            if len(y_cols) == 1:
                # Single series bar chart
                y_col = y_cols[0]
                bars = ax.bar(range(len(plot_data)), plot_data[y_col], alpha=0.7)
                ax.set_ylabel(y_col.replace('Y_', '').replace('_', '.'))
                ax.set_title(f"Bar Chart: {y_col.replace('Y_', '').replace('_', '.')}")
            else:
                # Multi-series bar chart
                x = np.arange(len(plot_data))
                width = 0.8 / len(y_cols)
                
                for i, y_col in enumerate(y_cols):
                    offset = (i - len(y_cols)/2) * width + width/2
                    ax.bar(x + offset, plot_data[y_col], width, alpha=0.7, 
                          label=y_col.replace('Y_', '').replace('_', '.'))
                
                ax.set_ylabel('Values')
                ax.set_title('Multi-Column Bar Chart')
                ax.legend()
            
            ax.set_xlabel('Data Points')
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Error creating bar plot: {str(e)}"}
    
    def _create_histogram_plot(self, ax, data: pd.DataFrame, x_cols: List[str], y_cols: List[str]) -> Dict[str, Any]:
        """Create histogram plot"""
        try:
            all_cols = x_cols + y_cols
            if len(all_cols) == 0:
                return {"error": "Need at least one column for histogram"}
            
            if len(all_cols) == 1:
                # Single histogram
                col = all_cols[0]
                ax.hist(data[col].dropna(), bins=30, alpha=0.7, edgecolor='black')
                ax.set_xlabel(col.replace('X_', '').replace('Y_', '').replace('_', '.'))
                ax.set_ylabel('Frequency')
                ax.set_title(f"Histogram: {col.replace('X_', '').replace('Y_', '').replace('_', '.')}")
            else:
                # Multiple histograms
                colors = plt.cm.tab10(np.linspace(0, 1, len(all_cols)))
                for i, col in enumerate(all_cols):
                    ax.hist(data[col].dropna(), bins=20, alpha=0.5, 
                           color=colors[i], label=col.replace('X_', '').replace('Y_', '').replace('_', '.'), 
                           edgecolor='black')
                
                ax.set_xlabel('Values')
                ax.set_ylabel('Frequency')
                ax.set_title('Multi-Column Histogram')
                ax.legend()
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Error creating histogram: {str(e)}"}
    
    def _create_correlation_plot(self, ax, data: pd.DataFrame, x_cols: List[str], y_cols: List[str]) -> Dict[str, Any]:
        """Create correlation heatmap"""
        try:
            all_cols = x_cols + y_cols
            if len(all_cols) < 2:
                return {"error": "Need at least 2 columns for correlation analysis"}
            
            # Select numeric columns only
            numeric_data = data[all_cols].select_dtypes(include=['number'])
            
            if len(numeric_data.columns) < 2:
                return {"error": "Need at least 2 numeric columns for correlation"}
            
            corr_matrix = numeric_data.corr()
            
            # Clean column names for display
            clean_names = [col.replace('X_', '').replace('Y_', '').replace('_', '.') for col in corr_matrix.columns]
            corr_matrix.columns = clean_names
            corr_matrix.index = clean_names
            
            import seaborn as sns
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax, 
                       square=True, fmt='.2f', cbar_kws={'shrink': 0.8})
            ax.set_title('Column Correlation Heatmap')
            
            return {"success": True}
            
        except Exception as e:
            return {"error": f"Error creating correlation plot: {str(e)}"}
    
    def _calculate_multi_column_stats(self, data: pd.DataFrame, x_cols: List[str], y_cols: List[str]) -> Dict[str, Any]:
        """Calculate summary statistics for multiple columns"""
        try:
            stats = {}
            all_cols = x_cols + y_cols
            
            # Basic data info
            stats['total_columns'] = len(all_cols)
            stats['data_points'] = len(data)
            stats['x_columns'] = len(x_cols)
            stats['y_columns'] = len(y_cols)
            
            # Column-specific stats
            numeric_cols = data[all_cols].select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                stats['numeric_columns'] = len(numeric_cols)
                stats['avg_mean'] = float(data[numeric_cols].mean().mean())
                stats['avg_std'] = float(data[numeric_cols].std().mean())
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating multi-column stats: {e}")
            return {'error': str(e)}
    
    def execute_sql_query(self, query: str, database_path: str = None) -> Dict[str, Any]:
        """
        Execute SQL query with safety measures and return results
        
        Args:
            query: SQL query string (SELECT statements only)
            database_path: Optional specific database path
        
        Returns:
            Dict containing query results, column info, and metadata
        """
        try:
            # Basic SQL injection protection - only allow SELECT statements
            query_stripped = query.strip().upper()
            if not query_stripped.startswith('SELECT'):
                return {
                    "success": False,
                    "error": "Only SELECT queries are allowed for security reasons"
                }
            
            # Block potentially dangerous SQL keywords (but allow UNION for legitimate queries)
            dangerous_keywords = [
                'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER',
                'EXEC', 'EXECUTE', 'INTO', 'OUTFILE', 'DUMPFILE'
            ]
            
            for keyword in dangerous_keywords:
                if keyword in query_stripped:
                    return {
                        "success": False,
                        "error": f"Query contains potentially dangerous keyword: {keyword}"
                    }
            
            # If specific database provided, use it; otherwise, try to determine from query
            if database_path and database_path.endswith(('.db', '.sqlite')):
                result = self._execute_sqlite_query(query, database_path)
            elif database_path and ("stock_data" in database_path or "fx_data" in database_path):
                result = self._execute_csv_query(query, database_path)
            else:
                # Try to auto-detect data source from table names in query
                result = self._execute_auto_detected_query(query)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            return {
                "success": False,
                "error": f"Query execution error: {str(e)}"
            }
    
    def _execute_sqlite_query(self, query: str, database_path: str) -> Dict[str, Any]:
        """Execute query against SQLite database"""
        try:
            conn = sqlite3.connect(database_path)
            
            # Execute query with pandas for better handling
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Clean data for JSON serialization
            df_cleaned = df.fillna(None)
            
            return {
                "success": True,
                "data": df_cleaned.to_dict('records'),
                "columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns],
                "column_names": list(df.columns),
                "row_count": len(df),
                "query": query,
                "source_type": "SQLite",
                "source_path": database_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"SQLite query error: {str(e)}"
            }
    
    def _execute_csv_query(self, query: str, database_path: str) -> Dict[str, Any]:
        """Execute query against CSV files using SQLite in-memory database"""
        try:
            # Create in-memory SQLite database
            conn = sqlite3.connect(':memory:')
            
            # Load CSV files into the in-memory database
            data_dir = Path(database_path)
            csv_files = list(data_dir.glob("*.csv"))
            
            table_info = {}
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    # Clean NaN values before loading to SQLite to prevent fillna() issues
                    df = df.fillna(value=None)
                    table_name = csv_file.stem.lower()  # Use lowercase table name
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                    table_info[table_name] = {
                        'original_file': str(csv_file),
                        'row_count': len(df),
                        'columns': list(df.columns)
                    }
                except Exception as file_error:
                    logger.warning(f"Could not load CSV file {csv_file}: {file_error}")
            
            # Execute the query
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Clean data for JSON serialization
            df_cleaned = df.fillna(None)
            
            return {
                "success": True,
                "data": df_cleaned.to_dict('records'),
                "columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns],
                "column_names": list(df.columns),
                "row_count": len(df),
                "query": query,
                "source_type": "CSV",
                "source_path": database_path,
                "loaded_tables": table_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"CSV query error: {str(e)}"
            }
    
    def _execute_auto_detected_query(self, query: str) -> Dict[str, Any]:
        """Auto-detect data source based on table names in query"""
        try:
            # Get available databases
            databases = self.get_available_databases()
            
            # Extract table names from query (simple regex approach)
            import re
            table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)|JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(table_pattern, query.upper())
            table_names = [match[0] or match[1] for match in matches if match[0] or match[1]]
            
            if not table_names:
                return {
                    "success": False,
                    "error": "Could not extract table names from query"
                }
            
            # Try to find a database containing these tables
            for db in databases:
                if db['type'] == 'SQLite':
                    try:
                        conn = sqlite3.connect(db['path'])
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        available_tables = [row[0].lower() for row in cursor.fetchall()]
                        conn.close()
                        
                        # Check if all required tables exist
                        if all(table.lower() in available_tables for table in table_names):
                            return self._execute_sqlite_query(query, db['path'])
                    except:
                        continue
                
                elif db['type'] in ['CSV_Stock_Data', 'CSV_FX_Data']:
                    try:
                        data_dir = Path(db['path'])
                        csv_files = [f.stem.lower() for f in data_dir.glob("*.csv")]
                        
                        # Check if all required tables exist as CSV files
                        if all(table.lower() in csv_files for table in table_names):
                            return self._execute_csv_query(query, db['path'])
                    except:
                        continue
            
            return {
                "success": False,
                "error": f"Could not find database containing tables: {', '.join(table_names)}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Auto-detection error: {str(e)}"
            }
    
    def get_sample_queries(self) -> List[Dict[str, Any]]:
        """Get a list of sample SQL queries for common use cases"""
        return [
            # Original existing queries
            {
                "id": "stock_price_comparison",
                "title": "📈 Stock Price Comparison",
                "description": "Compare closing prices of different stocks over time",
                "query": """SELECT Date, Close as AAPL_Price 
FROM aapl 
WHERE Date >= '2022-01-01' 
ORDER BY Date DESC 
LIMIT 100""",
                "category": "Stock Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "AAPL_Price"],
                "chart_suggestions": ["line", "scatter"]
            },
            {
                "id": "volume_analysis",
                "title": "📊 Trading Volume Analysis",
                "description": "Analyze trading volumes across multiple stocks",
                "query": """SELECT 'AAPL' as Stock, AVG(Volume) as Avg_Volume, MAX(Volume) as Max_Volume 
FROM aapl 
WHERE Date >= '2023-01-01'
UNION ALL
SELECT 'MSFT' as Stock, AVG(Volume) as Avg_Volume, MAX(Volume) as Max_Volume 
FROM msft 
WHERE Date >= '2023-01-01'""",
                "category": "Volume Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Stock", "Avg_Volume", "Max_Volume"],
                "chart_suggestions": ["bar", "scatter"]
            },
            {
                "id": "price_volatility",
                "title": "📉 Price Volatility Analysis",
                "description": "Calculate daily price changes and volatility",
                "query": """SELECT Date, 
       Close, 
       (High - Low) as Daily_Range,
       ((Close - Open) / Open) * 100 as Daily_Return_Pct
FROM aapl 
WHERE Date >= '2023-01-01' 
ORDER BY Date DESC 
LIMIT 252""",
                "category": "Risk Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Close", "Daily_Range", "Daily_Return_Pct"],
                "chart_suggestions": ["line", "scatter", "histogram"]
            },
            {
                "id": "monthly_performance",
                "title": "📅 Monthly Performance Summary",
                "description": "Aggregate monthly stock performance data",
                "query": """SELECT 
    strftime('%Y-%m', Date) as Month,
    MIN(Low) as Monthly_Low,
    MAX(High) as Monthly_High,
    AVG(Close) as Avg_Close,
    SUM(Volume) as Total_Volume
FROM googl
WHERE Date >= '2022-01-01'
GROUP BY strftime('%Y-%m', Date)
ORDER BY Month DESC""",
                "category": "Time Series",
                "data_source": "CSV Stock Data", 
                "expected_columns": ["Month", "Monthly_Low", "Monthly_High", "Avg_Close", "Total_Volume"],
                "chart_suggestions": ["line", "bar"]
            },
            
            # NEW: SELECT TOP 1000 queries for each table
            {
                "id": "aapl_top_1000",
                "title": "🍎 AAPL - Top 1000 Records",
                "description": "Select top 1000 records from AAPL stock data",
                "query": """SELECT Date, Open, High, Low, Close, `Adj Close`, Volume
FROM aapl 
ORDER BY Date DESC 
LIMIT 1000""",
                "category": "Data Exploration",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"],
                "chart_suggestions": ["line", "scatter", "histogram"]
            },
            {
                "id": "msft_top_1000",
                "title": "🪟 MSFT - Top 1000 Records",
                "description": "Select top 1000 records from Microsoft stock data",
                "query": """SELECT Date, Open, High, Low, Close, `Adj Close`, Volume
FROM msft 
ORDER BY Date DESC 
LIMIT 1000""",
                "category": "Data Exploration",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"],
                "chart_suggestions": ["line", "scatter", "histogram"]
            },
            {
                "id": "googl_top_1000",
                "title": "🔍 GOOGL - Top 1000 Records",
                "description": "Select top 1000 records from Google stock data",
                "query": """SELECT Date, Open, High, Low, Close, `Adj Close`, Volume
FROM googl 
ORDER BY Date DESC 
LIMIT 1000""",
                "category": "Data Exploration",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"],
                "chart_suggestions": ["line", "scatter", "histogram"]
            },
            {
                "id": "amzn_top_1000",
                "title": "📦 AMZN - Top 1000 Records",
                "description": "Select top 1000 records from Amazon stock data",
                "query": """SELECT Date, Open, High, Low, Close, `Adj Close`, Volume
FROM amzn 
ORDER BY Date DESC 
LIMIT 1000""",
                "category": "Data Exploration",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"],
                "chart_suggestions": ["line", "scatter", "histogram"]
            },
            {
                "id": "spy_top_1000",
                "title": "📊 SPY - Top 1000 Records",
                "description": "Select top 1000 records from S&P 500 ETF data",
                "query": """SELECT Date, Open, High, Low, Close, `Adj Close`, Volume
FROM spy 
ORDER BY Date DESC 
LIMIT 1000""",
                "category": "Data Exploration",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"],
                "chart_suggestions": ["line", "scatter", "histogram"]
            },
            
            # NEW: JOIN queries between tables using date
            {
                "id": "stock_correlation_join",
                "title": "🔗 Stock Price Correlation (AAPL vs MSFT)",
                "description": "Join AAPL and MSFT data by date to analyze correlation",
                "query": """SELECT 
    a.Date,
    a.Close as AAPL_Close,
    m.Close as MSFT_Close,
    a.Volume as AAPL_Volume,
    m.Volume as MSFT_Volume,
    ((a.Close - a.Open) / a.Open * 100) as AAPL_Daily_Return,
    ((m.Close - m.Open) / m.Open * 100) as MSFT_Daily_Return
FROM aapl a
INNER JOIN msft m ON a.Date = m.Date
WHERE a.Date >= '2023-01-01'
ORDER BY a.Date DESC
LIMIT 1000""",
                "category": "JOIN Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "AAPL_Close", "MSFT_Close", "AAPL_Volume", "MSFT_Volume", "AAPL_Daily_Return", "MSFT_Daily_Return"],
                "chart_suggestions": ["scatter", "line", "correlation"]
            },
            {
                "id": "tech_stocks_comparison_join",
                "title": "🔗 Tech Giants Comparison (3-Way JOIN)",
                "description": "Compare AAPL, MSFT, and GOOGL using date-based JOINs",
                "query": """SELECT 
    a.Date,
    a.Close as AAPL_Price,
    m.Close as MSFT_Price,
    g.Close as GOOGL_Price,
    a.Volume as AAPL_Vol,
    m.Volume as MSFT_Vol,
    g.Volume as GOOGL_Vol,
    (a.High - a.Low) as AAPL_DayRange,
    (m.High - m.Low) as MSFT_DayRange,
    (g.High - g.Low) as GOOGL_DayRange
FROM aapl a
INNER JOIN msft m ON a.Date = m.Date
INNER JOIN googl g ON a.Date = g.Date
WHERE a.Date >= '2022-01-01'
ORDER BY a.Date DESC
LIMIT 1000""",
                "category": "JOIN Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "AAPL_Price", "MSFT_Price", "GOOGL_Price", "AAPL_Vol", "MSFT_Vol", "GOOGL_Vol", "AAPL_DayRange", "MSFT_DayRange", "GOOGL_DayRange"],
                "chart_suggestions": ["line", "scatter", "correlation"]
            },
            {
                "id": "market_vs_tech_join",
                "title": "🔗 Market ETF vs Tech Stock (SPY vs AAPL)",
                "description": "Join SPY market data with AAPL to compare individual vs market performance",
                "query": """SELECT 
    s.Date,
    s.Close as SPY_Close,
    a.Close as AAPL_Close,
    s.Volume as SPY_Volume,
    a.Volume as AAPL_Volume,
    ((s.Close - s.Open) / s.Open * 100) as SPY_Return,
    ((a.Close - a.Open) / a.Open * 100) as AAPL_Return,
    CASE 
        WHEN ((a.Close - a.Open) / a.Open) > ((s.Close - s.Open) / s.Open) THEN 'AAPL Outperformed'
        ELSE 'SPY Outperformed'
    END as Performance_Winner
FROM spy s
INNER JOIN aapl a ON s.Date = a.Date
WHERE s.Date >= '2023-01-01'
ORDER BY s.Date DESC
LIMIT 1000""",
                "category": "JOIN Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "SPY_Close", "AAPL_Close", "SPY_Volume", "AAPL_Volume", "SPY_Return", "AAPL_Return", "Performance_Winner"],
                "chart_suggestions": ["line", "scatter", "bar"]
            },
            {
                "id": "all_stocks_join_summary",
                "title": "🔗 All Stocks Daily Summary (5-Way JOIN)",
                "description": "Join all available stock tables by date for comprehensive daily comparison",
                "query": """SELECT 
    a.Date,
    a.Close as AAPL,
    m.Close as MSFT,
    g.Close as GOOGL,
    amz.Close as AMZN,
    s.Close as SPY,
    (a.Volume + m.Volume + g.Volume + amz.Volume) as Total_Stock_Volume,
    s.Volume as Market_Volume,
    ROUND(AVG(a.Close + m.Close + g.Close + amz.Close) / 4, 2) as Avg_Stock_Price
FROM aapl a
INNER JOIN msft m ON a.Date = m.Date
INNER JOIN googl g ON a.Date = g.Date  
INNER JOIN amzn amz ON a.Date = amz.Date
INNER JOIN spy s ON a.Date = s.Date
WHERE a.Date >= '2022-01-01'
ORDER BY a.Date DESC
LIMIT 1000""",
                "category": "JOIN Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "AAPL", "MSFT", "GOOGL", "AMZN", "SPY", "Total_Stock_Volume", "Market_Volume", "Avg_Stock_Price"],
                "chart_suggestions": ["line", "bar", "correlation"]
            },
            
            # Original remaining queries
            {
                "id": "multi_stock_comparison",
                "title": "🔄 Multi-Stock Price Comparison",
                "description": "Compare normalized prices of multiple stocks",
                "query": """WITH stock_data AS (
    SELECT 'AAPL' as Symbol, Date, Close as Price FROM aapl WHERE Date >= '2023-06-01'
    UNION ALL 
    SELECT 'MSFT' as Symbol, Date, Close as Price FROM msft WHERE Date >= '2023-06-01'
    UNION ALL
    SELECT 'GOOGL' as Symbol, Date, Close as Price FROM googl WHERE Date >= '2023-06-01'
)
SELECT Symbol, Date, Price,
       LAG(Price, 1) OVER (PARTITION BY Symbol ORDER BY Date) as Prev_Price
FROM stock_data
ORDER BY Date DESC, Symbol
LIMIT 300""",
                "category": "Comparative Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Symbol", "Date", "Price", "Prev_Price"],
                "chart_suggestions": ["line", "scatter"]
            },
            {
                "id": "high_volume_days",
                "title": "⚡ High Volume Trading Days",
                "description": "Find days with unusually high trading volume",
                "query": """SELECT Date, Close, Volume,
       (Volume - AVG(Volume) OVER (ORDER BY Date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING)) / 
       AVG(Volume) OVER (ORDER BY Date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) * 100 as Volume_Change_Pct
FROM amzn 
WHERE Date >= '2023-01-01'
ORDER BY Volume DESC
LIMIT 50""",
                "category": "Anomaly Detection",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Date", "Close", "Volume", "Volume_Change_Pct"],
                "chart_suggestions": ["scatter", "bar"]
            },
            {
                "id": "weekly_performance",
                "title": "📊 Weekly Performance Trends", 
                "description": "Analyze weekly trading patterns and performance",
                "query": """SELECT 
    CASE strftime('%w', Date)
        WHEN '0' THEN 'Sunday'
        WHEN '1' THEN 'Monday' 
        WHEN '2' THEN 'Tuesday'
        WHEN '3' THEN 'Wednesday'
        WHEN '4' THEN 'Thursday'
        WHEN '5' THEN 'Friday'
        WHEN '6' THEN 'Saturday'
    END as Day_of_Week,
    AVG((Close - Open) / Open * 100) as Avg_Daily_Return,
    AVG(Volume) as Avg_Volume,
    COUNT(*) as Trading_Days
FROM spy
WHERE Date >= '2022-01-01'
GROUP BY strftime('%w', Date)
ORDER BY strftime('%w', Date)""",
                "category": "Pattern Analysis",
                "data_source": "CSV Stock Data",
                "expected_columns": ["Day_of_Week", "Avg_Daily_Return", "Avg_Volume", "Trading_Days"],
                "chart_suggestions": ["bar", "line"]
            }
        ]