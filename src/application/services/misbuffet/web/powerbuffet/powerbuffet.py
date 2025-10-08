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
        """Get tables from the selected database"""
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
                    
                    tables.append({
                        "name": table_name,
                        "columns": [{"name": col[1], "type": col[2]} for col in columns],
                        "row_count": row_count
                    })
                
                conn.close()
            
            elif "stock_data" in database_path and Path(database_path).is_dir():
                # Handle CSV stock data directory
                data_dir = Path(database_path)
                csv_files = list(data_dir.glob("*.csv"))
                
                for csv_file in csv_files:
                    # Read first few rows to get column info
                    df = pd.read_csv(csv_file, nrows=5)
                    row_count = len(pd.read_csv(csv_file))
                    
                    columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
                    
                    tables.append({
                        "name": csv_file.stem,  # filename without extension
                        "columns": columns,
                        "row_count": row_count,
                        "file_path": str(csv_file)
                    })
            
            elif "fx_data" in database_path and Path(database_path).is_dir():
                # Handle CSV FX data directory
                data_dir = Path(database_path)
                csv_files = list(data_dir.glob("*.csv"))
                
                for csv_file in csv_files:
                    # Read first few rows to get column info
                    df = pd.read_csv(csv_file, nrows=5)
                    row_count = len(pd.read_csv(csv_file))
                    
                    columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
                    
                    tables.append({
                        "name": csv_file.stem,  # filename without extension
                        "columns": columns,
                        "row_count": row_count,
                        "file_path": str(csv_file)
                    })
                
        except Exception as e:
            logger.error(f"Error getting tables from database {database_path}: {e}")
            
        return tables
    
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